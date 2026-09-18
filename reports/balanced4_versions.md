# 两套题库的平衡四维评分

这里的“早期/修订”指数据版本。两组均使用平衡四维协议 `balanced_four_dim_v2_no_gold_op_penalty`，Judge 为 `deepseek-v4-flash-0731`，不是早期约3.5–3.8分的严格四维评分。不同题库的绝对分差不直接等同于模型能力变化。

## 早期1000题（六个模型，包含GPT-4o）

原始评分位于根目录 `models/<模型>/deepseek_scores_4d.jsonl`，与NAS的 `harmonic_four_dimension_eval_1000_balanced_v2/results/<模型>/deepseek/results.jsonl` 字节一致，原有结果未改动。

| 模型 | 题数 | 四维均分 | 四维调和分 | OP惩罚后最终分 | OP<4题数 |
| --- | --- | --- | --- | --- | --- |
| OPSD Step900 | 1000 | 4.7558 | 4.7400 | 4.7358 | 21 |
| OPSD Step1192 | 1000 | 4.6385 | 4.6152 | 4.6051 | 63 |
| Qwen3.5-9B 原版 | 1000 | 4.6267 | 4.6050 | 4.6006 | 27 |
| GPT-4o | 1000 | 4.6154 | 4.5921 | 4.5921 | 4 |
| Harmonic Step600 | 1000 | 4.5768 | 4.5439 | 4.5280 | 107 |
| GPT-OSS-20B | 1000 | 4.5422 | 4.5140 | 4.5103 | 43 |

## 老师建议修订后的1000题（五个模型）

新增结果位于 `v2/models/<模型>/`，来自NAS的 `harmonic_four_dimension_eval_1000_teacher_balanced_v2/evaluation_all_models_v1/<模型>/judges_balanced4/deepseek/`。GPT-4o未在本题库评分，不能用早期题库分数补入。

| 模型 | 题数 | 四维均分 | 四维调和分 | OP惩罚后最终分 | OP<4题数 |
| --- | --- | --- | --- | --- | --- |
| OPSD Step900 | 1000 | 4.7618 | 4.7454 | 4.7425 | 24 |
| OPSD Step1192 | 1000 | 4.6393 | 4.6130 | 4.6027 | 66 |
| Qwen3.5-9B 原版 | 1000 | 4.6321 | 4.6082 | 4.6054 | 23 |
| GPT-OSS-20B | 1000 | 4.5857 | 4.5607 | 4.5566 | 32 |
| Harmonic Step600 | 1000 | 4.5777 | 4.5448 | 4.5246 | 114 |

## 三种分数如何计算

Judge直接输出Task、Memory、OP restraint、Resonation、Expression、Reception六项1–5整数分。先对后面三项求调和均值得到EI，再用Task、Memory、OP restraint、EI组成顶层四维。

- 四维均分：每题四个顶层分数的算术平均，再对1000题平均。
- 四维调和分：每题四个顶层分数的调和平均，再对1000题平均。
- OP惩罚后最终分：每题取四维调和分与OP上限的较小值，再对1000题平均。OP为1/2/3/4/5时，上限分别为1.5/2.5/3.5/5/5。

`summary.json` 的 `mean_per_item` 是上述表格口径；`aggregate_of_dimension_means` 是先跨题求维度均值再聚合的另一口径，两者不得混用。本表保留全部1000题，不实施低于4分归零。

早期精确评分脚本位于 `protocols/evaluate_4d.py`；修订题库评分来源脚本快照位于 `v2/protocols/balanced4_scoring_snapshot/evaluate_4d.py`。两份来源脚本的评分rubric和派生公式一致，修订脚本增加题库hash参数及JSON理由格式指示。该快照与已有的通用 `v2/protocols/evaluate_4d.py` 分开保留，便于追溯实际结果。

## 严格四维评分的历史位置

NAS：`/NAS/jfxiao/wangdh/harmonic_four_dimension_eval_1000_v2/evaluation_blind_1000_v1/<模型>/judges_blind/deepseek/`。这是另一套协议，不属于上述两个平衡四维表格。本次未导入或改写这些历史严格评分。

## 验收与复核

`python3 tools/verify_balanced_results.py` 离线核对11组共11000条结果：唯一query_id、题库hash、query/memory/prompt、推理回答逐字一致、六项整数分、非空理由、逐题派生公式、汇总分及类别分组。不会调用模型API。

来源路径与逐文件SHA256见 `reports/balanced4_source_manifest.json`；验收报告见 `reports/balanced4_validation.json`；完整数值见 `reports/balanced4_versions.csv`。来源summary中API/解析错误计数均为0；这不代表历史运行从未发生并已修复的重试。
