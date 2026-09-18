"""Offline dataset checks and exact prompt exports; no model API calls."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import runpy
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (ROOT / path).read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def literal_assignment(path: Path, name: str) -> Any:
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
        # The v2 wrapper sets base.PROTOCOL and base.SYSTEM_PROMPT.
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Attribute) and t.attr == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(f"missing {name} in {path}")


def pure_functions(path: Path, names: tuple[str, ...]) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in selected} == set(names)
    ns: dict[str, Any] = {"Any": Any, "json": json}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), ns)
    return ns


def export_protocol(version: str) -> dict[str, Any]:
    folder = ROOT / "protocols" / version
    criteria_ns = runpy.run_path(str(folder / "criteria_defs.py"))
    criteria = criteria_ns["EVAL_CRITERIA"]
    names = [item["dimension"] for item in criteria]
    assert len(names) == len(set(names)) == 10
    assert all(set(item["levels"]) == {"1", "2", "3", "4", "5"} for item in criteria)
    entry = folder / "evaluate_10d.py"
    base = folder / "evaluate_10d_base.py" if version == "10d_v2" else entry
    functions = pure_functions(base, ("judge_prompt", "response_schema"))
    blocks = []
    for item in criteria:
        lines = [f"## {item['dimension']}"]
        if item.get("description"):
            lines.append(f"指标说明：{item['description']}")
        lines.extend(f"{score}分：{item['levels'][score]}" for score in sorted(item["levels"], key=int, reverse=True))
        blocks.append("\n".join(lines))
    rubric = "\n\n".join(blocks)
    if version == "10d_v2":
        rubric = f"# Project scene guidance\n{criteria_ns['SCENARIO_GUIDANCE']}\n\n# Ten-dimension rubric\n{rubric}"
    row = {"query": "{{QUERY}}", "extracted_memories": ["{{MEMORY_1}}", "{{MEMORY_2}}"], "response": "{{EXISTING_MODEL_RESPONSE}}"}
    user = functions["judge_prompt"](row, rubric, names)
    system = literal_assignment(entry, "SYSTEM_PROMPT")
    protocol = literal_assignment(entry, "PROTOCOL")
    schema = functions["response_schema"](names)
    text = (
        f"# 十维评分 {version}\n\n协议：`{protocol}`。评分为1–5整数，逐维独立。\n\n"
        "以下为来源代码自动导出的完整语句；双花括号表示运行时证据占位符，不是新生成的模型回答。"
        "实际记忆数组长度按题目变化。\n\n## System message\n\n```text\n"
        + system + "\n```\n\n## User message template\n\n```text\n" + user
        + "\n```\n\n## 输出要求\n\n每维包含 `score` 与 `reason`，完整机器约束见同目录 `response_schema.json`。"
        "隐藏标注不进入请求；不执行 `<4→0` 后处理。\n"
    )
    # Normalize document line endings/trailing whitespace, not runtime rubric values.
    (folder / "scoring_prompt.md").write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n", encoding="utf-8")
    save_json(folder / "response_schema.json", schema)
    return {"protocol": protocol, "dimensions": names, "scale": [1, 5], "prompt": f"protocols/{version}/scoring_prompt.md", "entrypoint": f"protocols/{version}/evaluate_10d.py"}


def main() -> None:
    results_audit_path = ROOT.parent / "reports/balanced4_validation.json"
    results_audit = json.loads(results_audit_path.read_text()) if results_audit_path.exists() else None
    score_data_published = (ROOT / "models").exists()
    if score_data_published:
        assert results_audit and results_audit["status"] == "PASS"
        assert len(results_audit["datasets"]["teacher"]["models"]) == 5
    benchmark = load("benchmark/benchmark_1000.jsonl")
    annotations = load("annotations/memory_roles.jsonl")
    ei = load("annotations/ei_memory_dependency.jsonl")
    archive = load("benchmark/archive/archived_task_100.jsonl")
    safety = load("safety_100/benchmark_100.jsonl")
    safety_ann = load("safety_100/hidden_annotations.jsonl")
    ids = {r["query_id"] for r in benchmark}
    assert len(benchmark) == len(ids) == 1000
    assert len(annotations) == 1000 and {r["query_id"] for r in annotations} == ids
    categories = Counter(r["category"].split("::", 1)[0] for r in benchmark)
    assert categories == {"memory": 350, "over_personalization": 250, "emotional_intelligence": 250, "task_quality": 150}
    languages = Counter("zh" if re.search(r"[\u4e00-\u9fff]", r["query"]) else "en" for r in benchmark)
    assert languages == {"zh": 500, "en": 500}
    assert len(ei) == 250 and sum(r["targeted_memory_dependent"] for r in ei) == 175
    assert {r["query_id"] for r in ei} == {r["query_id"] for r in benchmark if r["category"].startswith("emotional_intelligence::")}
    assert len(archive) == len({r["query_id"] for r in archive}) == 100
    assert not ids.intersection(r["query_id"] for r in archive)
    assert len({re.sub(r"\s+", " ", r["query"].strip().casefold()) for r in benchmark}) == 1000
    hidden_keys = {"gold", "memory_roles", "must_do", "must_not_do", "hard_fail_conditions", "hidden"}
    for row in benchmark + safety:
        assert not hidden_keys.intersection(row)
        assert row["query"] and row["prompt"] and row["query"] in row["prompt"]
        assert all(memory in row["prompt"] for memory in row["extracted_memories"])
    by_id = {r["query_id"]: r for r in benchmark}
    roles = Counter()
    for ann in annotations:
        count = len(by_id[ann["query_id"]]["extracted_memories"])
        assert [r["memory_id"] for r in ann["memory_roles"]] == [f"m{i}" for i in range(1, count + 1)]
        assert ann["must_do"] and ann["must_not_do"]
        for role in ann["memory_roles"]:
            assert role["role"] in {"required", "beneficial", "neutral", "prohibited"}
            assert role["rationale"]
            roles[role["role"]] += 1
    slices = Counter(r["category"].split("::", 1)[1] for r in safety)
    assert slices == {"allergy_medication": 25, "sensitive_disclosure": 25, "subject_mismatch": 25, "stale_information": 25}
    assert len(safety) == len({r["query_id"] for r in safety}) == len(safety_ann) == 100
    assert {r["query_id"] for r in safety_ann} == {r["query_id"] for r in safety}
    assert not ids.intersection(r["query_id"] for r in safety)
    assert all(r["hard_fail_conditions"] for r in safety_ann)
    protocols = {version: export_protocol(version) for version in ("10d_v1", "10d_v2")}
    assert protocols["10d_v1"]["dimensions"] == protocols["10d_v2"]["dimensions"]
    construction = ROOT / "protocols/construction/build_benchmark_v2.py"
    construction_text = "# v2构造、审计与隐藏标注语句\n\n以下从构造脚本导出；具体批次参数和 schema 见 `build_benchmark_v2.py`。\n"
    for name in ("GEN_SYSTEM", "AUDIT_SYSTEM", "CAUSAL_AUDIT_SYSTEM", "ROLE_SYSTEM"):
        construction_text += f"\n## {name}\n\n```text\n{literal_assignment(construction, name)}\n```\n"
    (construction.parent / "generation_prompts.md").write_text(construction_text, encoding="utf-8")
    manifest = {
        "bundle": "EI_OP_Evaluation_v2", "schema_version": 2,
        "publication_scope": "datasets_protocols_and_balanced_four_dimension_results" if score_data_published else "datasets_and_protocols_only",
        "score_data_published": score_data_published,
        "balanced_four_dimension_results": results_audit["datasets"]["teacher"] if score_data_published else None,
        "benchmark": {"path": "benchmark/benchmark_1000.jsonl", "num_items": 1000, "unique_query_ids": 1000, "sha256": digest(ROOT / "benchmark/benchmark_1000.jsonl"), "primary_category_counts": dict(categories), "language_counts": dict(languages)},
        "annotations": {"memory_role_cases": 1000, "memory_role_counts": dict(roles), "ei_memory_dependent": 175, "ei_controls": 75, "visible_to_target_model": False, "used_by_regular_10d_judge": False},
        "safety": {"num_items": 100, "slice_counts": dict(slices), "independent_of_main_1000": True},
        "archived_task_rows": 100,
        "ten_dimension_protocols": protocols,
        "default_judge": "deepseek-v4-flash-0731",
        "validation": {"status": "PASS", "id_sets_match": True, "memory_role_coverage_complete": True, "hidden_annotations_separate": True, "prompts_exported_from_source": True},
        "files": {},
    }
    payloads = [p for p in sorted(ROOT.rglob("*")) if p.is_file() and p.name not in {"SHA256SUMS.txt", "delivery_manifest.json"} and "__pycache__" not in p.parts]
    for path in payloads:
        manifest["files"][path.relative_to(ROOT).as_posix()] = {"sha256": digest(path), "bytes": path.stat().st_size}
    save_json(ROOT / "delivery_manifest.json", manifest)
    payloads.append(ROOT / "delivery_manifest.json")
    (ROOT / "SHA256SUMS.txt").write_text("".join(f"{digest(p)}  {p.relative_to(ROOT).as_posix()}\n" for p in sorted(payloads)), encoding="utf-8")
    print(json.dumps({"status": "PASS", "benchmark_rows": len(benchmark), "annotation_rows": len(annotations), "safety_rows": len(safety), "protocols": list(protocols), "score_data_published": score_data_published}, ensure_ascii=False))


if __name__ == "__main__":
    main()
