#!/usr/bin/env python3
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmark" / "benchmark_1000.jsonl"

MODELS = {
    "harmonic_step600": "Harmonic0830 Step600",
    "opsd_step900": "OPSD Step900",
    "opsd_step1192": "OPSD Step1192",
    "qwen35_9b_base": "Qwen3.5-9B 原版",
    "gpt_oss_20b": "GPT-OSS-20B",
    "gpt_4o": "GPT-4o",
}


def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception as exc:
                    raise RuntimeError(f"{path}:{line_no}: {exc}") from exc
    return rows


def write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


benchmark_rows = load_jsonl(BENCHMARK)
assert len(benchmark_rows) == 1000
benchmark = {row["query_id"]: row for row in benchmark_rows}
assert len(benchmark) == 1000
benchmark_order = [row["query_id"] for row in benchmark_rows]

all_by_question = {
    qid: {
        "query_id": qid,
        "category": benchmark[qid].get("category"),
        "session_id": benchmark[qid].get("session_id"),
        "memory_key": benchmark[qid].get("memory_key"),
        "query": benchmark[qid].get("query"),
        "extracted_memories": benchmark[qid].get("extracted_memories", []),
        "prompt": benchmark[qid].get("prompt"),
        "models": {},
    }
    for qid in benchmark_order
}

manifest_models = {}
summary_rows = []

for slug, display_name in MODELS.items():
    model_dir = ROOT / "models" / slug
    response_path = model_dir / "responses.jsonl"
    ten_path = model_dir / "deepseek_scores_10d.jsonl"
    four_path = model_dir / "deepseek_scores_4d.jsonl"
    ten_summary_path = model_dir / "deepseek_summary_10d.json"
    four_summary_path = model_dir / "deepseek_summary_4d.json"

    responses = load_jsonl(response_path)
    ten_rows = load_jsonl(ten_path)
    four_rows = load_jsonl(four_path)
    assert len(responses) == len(ten_rows) == len(four_rows) == 1000, slug

    response_map = {row["query_id"]: row for row in responses}
    ten_map = {row["query_id"]: row for row in ten_rows}
    four_map = {row["query_id"]: row for row in four_rows}
    assert set(response_map) == set(ten_map) == set(four_map) == set(benchmark), slug

    combined_rows = []
    for qid in benchmark_order:
        b = benchmark[qid]
        a = response_map[qid]
        t = ten_map[qid]
        f = four_map[qid]
        assert a.get("query") == b.get("query"), (slug, qid, "query mismatch")
        assert t.get("response") == a.get("response"), (slug, qid, "10D response mismatch")
        assert f.get("response") == a.get("response"), (slug, qid, "4D response mismatch")
        assert t.get("query") == b.get("query"), (slug, qid, "10D query mismatch")
        assert f.get("query") == b.get("query"), (slug, qid, "4D query mismatch")

        model_payload = {
            "display_name": display_name,
            "target_model": a.get("target_model"),
            "served_model": a.get("served_model"),
            "response": a.get("response"),
            "deepseek_10d": {
                "judge_model": t.get("judge_model"),
                "scores": t.get("scores"),
                "reasons": t.get("reasons"),
                "macro_average": t.get("macro_average"),
            },
            "deepseek_4d": {
                "judge_model": f.get("judge_model"),
                "scores": f.get("scores"),
                "reasons": f.get("reasons"),
                "derived_scores": f.get("derived_scores"),
            },
        }
        all_by_question[qid]["models"][slug] = model_payload
        combined_rows.append({
            "query_id": qid,
            "category": b.get("category"),
            "session_id": b.get("session_id"),
            "memory_key": b.get("memory_key"),
            "query": b.get("query"),
            "extracted_memories": b.get("extracted_memories", []),
            "prompt": b.get("prompt"),
            "model": model_payload,
        })

    combined_path = model_dir / "combined_results.jsonl"
    write_jsonl(combined_path, combined_rows)

    ten_summary = json.loads(ten_summary_path.read_text(encoding="utf-8"))
    four_summary = json.loads(four_summary_path.read_text(encoding="utf-8"))
    d = four_summary["direct_dimension_averages"]
    mean = four_summary["mean_per_item"]
    op_dist = four_summary["op_score_distribution"]
    summary_rows.append({
        "model": display_name,
        "responses": len(responses),
        "10d_scored": len(ten_rows),
        "10d_macro": ten_summary["macro_average"],
        "4d_scored": len(four_rows),
        "task": d["task_quality"],
        "memory": d["memory_usage"],
        "op_restraint": d["over_personalization_restraint"],
        "resonation": d["resonation"],
        "expression": d["expression"],
        "reception": d["reception"],
        "ei": mean["emotional_intelligence_harmonic"],
        "4d_final": mean["final_op_penalized_score"],
        "op_below_4": int(op_dist.get("1", 0)) + int(op_dist.get("2", 0)) + int(op_dist.get("3", 0)),
    })
    manifest_models[slug] = {
        "display_name": display_name,
        "responses": len(responses),
        "deepseek_10d_scores": len(ten_rows),
        "deepseek_4d_scores": len(four_rows),
        "query_id_set_matches_benchmark": True,
        "response_text_matches_both_score_files": True,
        "paths": {
            "responses": str(response_path.relative_to(ROOT)),
            "deepseek_10d_scores": str(ten_path.relative_to(ROOT)),
            "deepseek_10d_summary": str(ten_summary_path.relative_to(ROOT)),
            "deepseek_4d_scores": str(four_path.relative_to(ROOT)),
            "deepseek_4d_summary": str(four_summary_path.relative_to(ROOT)),
            "combined": str(combined_path.relative_to(ROOT)),
        },
    }

write_jsonl(ROOT / "all_models_by_question.jsonl", [all_by_question[qid] for qid in benchmark_order])

fieldnames = list(summary_rows[0])
with (ROOT / "summary_table.csv").open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(summary_rows)

md_headers = [
    "模型", "回答", "十维", "十维Macro", "四维", "Task", "Memory", "OP", "EI", "四维最终分", "OP<4题数"
]
md_lines = [
    "| " + " | ".join(md_headers) + " |",
    "| " + " | ".join(["---"] * len(md_headers)) + " |",
]
for row in summary_rows:
    values = [
        row["model"], str(row["responses"]), str(row["10d_scored"]), f'{row["10d_macro"]:.4f}',
        str(row["4d_scored"]), f'{row["task"]:.4f}', f'{row["memory"]:.4f}',
        f'{row["op_restraint"]:.4f}', f'{row["ei"]:.4f}', f'{row["4d_final"]:.4f}', str(row["op_below_4"]),
    ]
    md_lines.append("| " + " | ".join(values) + " |")
(ROOT / "summary_table.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

readme = f"""# 1000题个性化对话评测交付包

本目录是可直接交付的完整结果集合，包含同一批1000道题、六个模型的逐题回答、DeepSeek十维评分、新版四维平衡评分、逐题评分理由与汇总报告。

## 内容结构

- `benchmark/benchmark_1000.jsonl`：1000道题的原始benchmark；每行含query、memory、类别与query_id。
- `models/<model>/responses.jsonl`：该模型的1000条原始回答。
- `models/<model>/deepseek_scores_10d.jsonl`：十维逐题分数与理由。
- `models/<model>/deepseek_scores_4d.jsonl`：新版四维逐题分数、六项直接评分、派生分与理由。
- `models/<model>/combined_results.jsonl`：按模型合并后的逐题题目、memory、回答和两套评分。
- `all_models_by_question.jsonl`：按题目组织；一行对应一道题，内含六个模型的回答与两套评分。
- `summary_table.csv` / `summary_table.md`：六模型汇总表。
- `protocols/`：benchmark生成说明以及两套评分实现和prompt。
- `reports/`：完整汇报文档（Word、PDF、Markdown）。
- `tools/build_delivery.py`：逐题合并与一致性校验脚本，可重复生成交付索引。
- `delivery_manifest.json`：机器可读的数量、文件关系与一致性检查结果。
- `SHA256SUMS.txt`：交付文件校验值。

## 数据完整性

- Benchmark：1000/1000
- 模型数量：{len(MODELS)}
- 每个模型回答：1000/1000
- 每个模型DeepSeek十维评分：1000/1000
- 每个模型DeepSeek新版四维评分：1000/1000
- API错误与解析错误：各summary均为0
- 全部query_id与benchmark一一对应；两套评分中保存的response与对应模型原始response逐字一致。

## 推荐阅读顺序

1. 先看 `reports/benchmark_report.pdf` 或 `.docx`。
2. 用 `summary_table.csv` 做表格分析。
3. 用 `all_models_by_question.jsonl` 横向比较同一道题的六个模型。
4. 需要原始审计时，进入 `models/<model>/` 查看回答、逐题分数及理由。
"""
(ROOT / "README.md").write_text(readme, encoding="utf-8")

manifest = {
    "bundle": "core_eval_delivery_1000_20260911",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "benchmark": {
        "path": str(BENCHMARK.relative_to(ROOT)),
        "num_items": len(benchmark_rows),
        "unique_query_ids": len(benchmark),
        "sha256": sha256(BENCHMARK),
    },
    "judge": "deepseek-v4-flash-0731",
    "protocols": ["10d_experience", "balanced_4d"],
    "models": manifest_models,
    "validation": {
        "all_counts_complete": True,
        "all_query_id_sets_match": True,
        "all_response_texts_match_score_inputs": True,
        "all_summary_api_errors_zero": all(
            json.loads((ROOT / "models" / slug / name).read_text(encoding="utf-8")).get("api_errors") == 0
            for slug in MODELS
            for name in ["deepseek_summary_10d.json", "deepseek_summary_4d.json"]
        ),
        "all_summary_parse_failures_zero": all(
            json.loads((ROOT / "models" / slug / name).read_text(encoding="utf-8")).get("parse_failures") == 0
            for slug in MODELS
            for name in ["deepseek_summary_10d.json", "deepseek_summary_4d.json"]
        ),
    },
}
(ROOT / "delivery_manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

checksum_files = sorted(
    p for p in ROOT.rglob("*")
    if p.is_file() and p.name != "SHA256SUMS.txt" and "work" not in p.relative_to(ROOT).parts
)
with (ROOT / "SHA256SUMS.txt").open("w", encoding="utf-8") as f:
    for path in checksum_files:
        f.write(f"{sha256(path)}  {path.relative_to(ROOT)}\n")

print(json.dumps({
    "root": str(ROOT),
    "benchmark_items": len(benchmark_rows),
    "models": len(MODELS),
    "all_models_by_question": len(all_by_question),
    "validation": manifest["validation"],
}, ensure_ascii=False, indent=2))
