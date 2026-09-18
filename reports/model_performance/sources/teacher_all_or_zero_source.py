#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


TEN_DIMS = (
    "整体满意度",
    "对话意愿",
    "情绪愉悦度",
    "意图判断准确",
    "记忆信息准确",
    "信息内容表达清晰",
    "交流流畅",
    "情感表达恰当",
    "风格恰当",
    "社会智能",
)
FOUR_DIRECT_DIMS = (
    "task_quality",
    "memory_usage",
    "over_personalization_restraint",
    "resonation",
    "expression",
    "reception",
)
MODELS = (
    ("harmonic0830_step600", "Harmonic0830 Step600"),
    ("qwen35_9b_grpo_opsd_step1192", "OPSD Step1192"),
    ("qwen35_9b_grpo_opsd_step900", "OPSD Step900"),
    ("qwen35_9b_base", "Qwen3.5-9B 原版"),
    ("gpt_oss_20b", "GPT-OSS-20B"),
)
OP_CAPS = {0: 0.0, 1: 1.5, 2: 2.5, 3: 3.5, 4: 4.5, 5: 5.0}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def harmonic(values: list[float]) -> float:
    if any(value <= 0 for value in values):
        return 0.0
    return len(values) / sum(1.0 / value for value in values)


def validate_scores(row: dict[str, Any], dims: tuple[str, ...], path: Path) -> dict[str, float]:
    scores = row.get("scores")
    if not isinstance(scores, dict) or set(scores) != set(dims):
        raise ValueError(f"{path}: {row.get('query_id')} has wrong score fields")
    values = {dim: float(scores[dim]) for dim in dims}
    if any(value < 1 or value > 5 for value in values.values()):
        raise ValueError(f"{path}: {row.get('query_id')} has score outside [1,5]")
    return values


def derive_four(scores: dict[str, float]) -> dict[str, float]:
    ei = harmonic([scores["resonation"], scores["expression"], scores["reception"]])
    top = [
        scores["task_quality"],
        scores["memory_usage"],
        scores["over_personalization_restraint"],
        ei,
    ]
    macro = mean(top)
    four_harmonic = harmonic(top)
    cap = OP_CAPS[int(scores["over_personalization_restraint"])]
    return {
        "emotional_intelligence_harmonic": ei,
        "four_dim_macro": macro,
        "four_dim_harmonic": four_harmonic,
        "over_personalization_cap": cap,
        "final_op_penalized_score": min(four_harmonic, cap),
    }


def gate_scores(scores: dict[str, float]) -> tuple[bool, dict[str, float]]:
    passed = min(scores.values()) >= 4
    return passed, scores if passed else {name: 0.0 for name in scores}


def process_ten(path: Path, out_path: Path) -> dict[str, Any]:
    source = read_jsonl(path)
    if len(source) != 1000 or len({row.get("query_id") for row in source}) != 1000:
        raise ValueError(f"{path}: expected 1000 unique rows")
    transformed = []
    for row in source:
        original = validate_scores(row, TEN_DIMS, path)
        passed, gated = gate_scores(original)
        transformed.append({
            "query_id": row["query_id"],
            "category": row.get("category"),
            "strict_pass": passed,
            "minimum_original_score": min(original.values()),
            "original_scores": original,
            "all_or_zero_scores": gated,
        })
    write_jsonl(out_path, transformed)
    averages = {dim: mean([row["all_or_zero_scores"][dim] for row in transformed]) for dim in TEN_DIMS}
    return {
        "source_path": str(path),
        "source_sha256": sha256(path),
        "derived_path": str(out_path),
        "derived_sha256": sha256(out_path),
        "items": len(transformed),
        "strict_pass_count": sum(row["strict_pass"] for row in transformed),
        "strict_pass_rate": mean([float(row["strict_pass"]) for row in transformed]),
        "dimension_averages": averages,
        "macro_average": mean(list(averages.values())),
    }


def process_four(path: Path, out_path: Path) -> dict[str, Any]:
    source = read_jsonl(path)
    if len(source) != 1000 or len({row.get("query_id") for row in source}) != 1000:
        raise ValueError(f"{path}: expected 1000 unique rows")
    transformed = []
    for row in source:
        original = validate_scores(row, FOUR_DIRECT_DIMS, path)
        passed, gated = gate_scores(original)
        transformed.append({
            "query_id": row["query_id"],
            "category": row.get("category"),
            "strict_pass": passed,
            "minimum_original_score": min(original.values()),
            "original_scores": original,
            "all_or_zero_scores": gated,
            "all_or_zero_derived_scores": derive_four(gated),
        })
    write_jsonl(out_path, transformed)
    averages = {dim: mean([row["all_or_zero_scores"][dim] for row in transformed]) for dim in FOUR_DIRECT_DIMS}
    aggregate_ei = harmonic([averages["resonation"], averages["expression"], averages["reception"]])
    aggregate_top = [averages["task_quality"], averages["memory_usage"], averages["over_personalization_restraint"], aggregate_ei]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in transformed:
        grouped[str(row.get("category", "unknown")).split("::", 1)[0]].append(row)
    return {
        "source_path": str(path),
        "source_sha256": sha256(path),
        "derived_path": str(out_path),
        "derived_sha256": sha256(out_path),
        "items": len(transformed),
        "strict_pass_count": sum(row["strict_pass"] for row in transformed),
        "strict_pass_rate": mean([float(row["strict_pass"]) for row in transformed]),
        "direct_dimension_averages": averages,
        "aggregate_of_dimension_means": {
            "emotional_intelligence_harmonic": aggregate_ei,
            "four_dim_macro": mean(aggregate_top),
            "four_dim_harmonic": harmonic(aggregate_top),
        },
        "mean_per_item": {
            key: mean([row["all_or_zero_derived_scores"][key] for row in transformed])
            for key in (
                "emotional_intelligence_harmonic",
                "four_dim_macro",
                "four_dim_harmonic",
                "final_op_penalized_score",
            )
        },
        "groups": {
            group: {
                "count": len(rows),
                "strict_pass_rate": mean([float(row["strict_pass"]) for row in rows]),
                "mean_final_op_penalized_score": mean([
                    row["all_or_zero_derived_scores"]["final_op_penalized_score"] for row in rows
                ]),
            }
            for group, rows in sorted(grouped.items())
        },
    }


def markdown(summary: dict[str, Any]) -> str:
    rows = sorted(summary["models"], key=lambda row: row["four_dim"]["mean_per_item"]["final_op_penalized_score"], reverse=True)
    lines = [
        "# Teacher-balanced v2：单题任一维低于4则全维置0",
        "",
        "同一题在每套评分协议内独立执行门控。十维任一维低于4则十维全0；四维协议的六个直接字段任一低于4则六项全0。",
        "",
        "| 模型 | 十维严格通过率 | 十维门控Macro | 四维严格通过率 | 四维门控Macro | 四维门控调和分 | 四维门控最终分 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        ten = row["ten_dim"]
        four = row["four_dim"]
        lines.append(
            f"| {row['model']} | {ten['strict_pass_rate']:.2%} | {ten['macro_average']:.4f} | "
            f"{four['strict_pass_rate']:.2%} | {four['aggregate_of_dimension_means']['four_dim_macro']:.4f} | "
            f"{four['aggregate_of_dimension_means']['four_dim_harmonic']:.4f} | "
            f"{four['mean_per_item']['final_op_penalized_score']:.4f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    models = []
    for slug, label in MODELS:
        source_base = args.source_root / slug
        model_out = args.output_root / "per_item" / slug
        ten = process_ten(
            source_base / "judges_huawei10/deepseek/results.jsonl",
            model_out / "huawei10_all_or_zero.jsonl",
        )
        four = process_four(
            source_base / "judges_balanced4/deepseek/results.jsonl",
            model_out / "balanced4_all_or_zero.jsonl",
        )
        models.append({"model_key": slug, "model": label, "ten_dim": ten, "four_dim": four})
    summary = {
        "rule": "Within each protocol, if any direct dimension score for an item is below 4, set every direct dimension for that item to 0 before aggregation.",
        "threshold": 4,
        "dataset": "teacher-balanced-v2 main 1000",
        "models": models,
    }
    write_json(args.output_root / "summary.json", summary)
    (args.output_root / "summary.md").write_text(markdown(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
