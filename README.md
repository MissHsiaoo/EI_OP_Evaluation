# 1000题个性化对话评测交付包

## 版本入口

- **[十维评分真实案例：12组同题对照](reports/sample_cases_20260918/README.md)**：六模型25份回答，覆盖全部十维；包含题目、memory、完整回答、原始分数、Judge理由和独立核对，明确标出评分误判。[带缩进完整数据](reports/sample_cases_20260918/sample_cases_full.json)。采用早期1000题及2026-09-18新版十维复评，不混入v2修订题库。
- **[老师原始要求与完成情况](reports/teacher_requirements/README.md)**：逐项列出已完成、部分完成、未达标和待人工验收内容，附原始审阅表行号及实际文件证据。
- **[全部模型表现：表格与图](reports/model_performance/README.md)**：14张汇总/明细表、9张图，包含四维、两版十维、Judge对比、归零口径、安全集与thinking对照。全部从真实结果文件生成。
- 本目录原有 `benchmark/`、`models/`、`summary_table.*`、`reports/benchmark_report.*` 是 **v1 结果快照**，保留不变；新增跨版本表图集中在 `reports/model_performance/`。
- [`v2/README.md`](v2/README.md) 是 **v2 修订题库与协议交付**：修订后的1000题、独立100题安全集、两版十维 Judge prompt 及可运行实现。现已补充五个模型的 DeepSeek 平衡四维逐题评分、原始回答与汇总。
- 根目录分数属于早期 v1 题库（六模型，含 GPT-4o）；`v2/summary_table.*` 属于修订题库（五模型，无 GPT-4o）。两套题库使用同一平衡四维评分标准，不能交叉混用题目或分数。
- [两套题库平衡四维结果对照](reports/balanced4_versions.md)：区分四维均分、四维调和分、OP惩罚后最终分，并说明3.5–3.8分的历史严格四维是另一套评分协议。

## 2026-09-18 评分结果更新

从共享NAS同步已有评分，没有重新生成回答或调用Judge。早期六模型的评分与汇总文件与NAS逐字节一致，保留原样；新增修订题库五模型各1000条平衡四维评分。

- [修订题库分数表](v2/summary_table.md) / [CSV](v2/summary_table.csv)
- [两套题库对照表](reports/balanced4_versions.md) / [CSV](reports/balanced4_versions.csv)
- [11000条结果验收](reports/balanced4_validation.json) / [NAS来源与SHA256](reports/balanced4_source_manifest.json)

逐题JSONL新增部分为新题库平衡四维。现另外整理了[修订题库十维、安全集及thinking对照汇总](reports/model_performance/README.md)，独立分区展示，不混入旧题库分数。根目录原有十维结果继续保留。

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
