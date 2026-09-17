# 1000题个性化对话评测交付包

## 版本入口

- 本目录原有 `benchmark/`、`models/`、`summary_table.*`、`reports/` 是 **v1 结果快照**，保留不变。
- [`v2/README.md`](v2/README.md) 是新增的 **v2 数据与协议交付**：修订后的1000题、独立100题安全集、两版十维 Judge prompt 及可运行实现。
- v2 本次仅更新数据、协议与校验工具，**不发布或覆盖任何跑分数据**；根目录分数仍属于 v1，不是 v2 新题库分数。

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
- 模型数量：6
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
