# 1000题个性化对话评测 v2

沿用 v1 的 JSONL、protocols、manifest 和 SHA256 校验格式；独立保存，不覆盖原题库和历史结果。本次只交付 benchmark 与评分协议，跑分尚未作为本版本结果发布。

## 内容结构

- `benchmark/benchmark_1000.jsonl`：修订后的主评测集，1000题。
- `benchmark/archive/archived_task_100.jsonl`：从主榜移出的100题 Task，保留归档。
- `benchmark/source_manifest.json`：服务器生成时保存的原始 manifest；其中路径为来源记录。
- `benchmark/validation_report.json`：来源数据验收结果。
- `annotations/memory_roles.jsonl`：逐题逐条记忆角色、理由、must-do / must-not-do；对目标模型不可见。
- `annotations/ei_memory_dependency.jsonl`：250题 EI 的依赖分析，175题 memory-dependent、75题 control。
- `safety_100/benchmark_100.jsonl`：独立100题安全集，不混入1000题主榜。
- `safety_100/hidden_annotations.jsonl`：逐题安全硬失败条件，只供独立安全评分使用。
- `protocols/10d_v1/`：原十维评分标准、可读 prompt、输出 schema、完整评分脚本。
- `protocols/10d_v2/`：新版统一十维标准与场景指导、可读 prompt、输出 schema、完整评分脚本。
- `protocols/evaluate_4d.py`：保留的四维平衡评分实现。
- `protocols/evaluate_safety.py`：独立安全集评分实现。
- `protocols/construction/`：v2生成/审计/隐藏标注脚本与构念参考来源。
- `tools/build_metadata.py`：离线验收数据、导出两版 prompt/schema、生成 manifest 和校验值；不调用模型 API。
- `delivery_manifest.json` / `SHA256SUMS.txt`：本交付版本的数量、协议编号和文件校验信息。

本次没有新增 `models/`、`summary_table.*`、`all_models_by_question.jsonl` 或分数报告。仓库根目录这些文件均属于原 v1，不能作为新题库的结果。

## 数据构成

| 主类别 | 题数 | 子类结构 |
|---|---:|---|
| Memory | 350 | 相关约束、多记忆综合、陈旧信息覆盖、无关/错误抑制、归属/冲突；各70题 |
| Over-personalization | 250 | 无关记忆克制、敏感最小披露、第三方边界、不确定/错误记忆、反推断/来源提示；各50题 |
| Emotional intelligence | 250 | 情绪共鸣、隐含需求、表达校准、冲突修复、支持行动；各50题 |
| Task | 150 | 约束遵循、数量推理、信息转换、规划决策、写作修改；各30题 |

主集中文500题、英文500题，1000个唯一 query_id。独立安全集为过敏/用药、敏感披露、主体错配、陈旧信息，四类各25题。

相对原交付，先逐项修复老师指出的166条 FAIL，再调整类别配额、重写175条 EI 以加强记忆依赖，并增加1000题隐藏角色标注和独立安全集。原有结果不迁移到新题目。

## 输入格式

主集和 v1 一样，每行包含：

```json
{
  "session_id": "h4eval_0001",
  "query_id": "h4eval_0001:0",
  "query": "当前用户问题",
  "category": "task_quality::constraint_following",
  "extracted_memories": ["一条历史记忆", "另一条历史记忆"],
  "memory_key": "m1",
  "prompt": "完整模型输入，包含memory和query"
}
```

上述是字段示意，不是新增测试题。推理只发送每行 `prompt`，不要把整行 JSON 或 `annotations/` 拼进输入。`memory_key` 是来源元数据，不作为十维或四维评分的参考答案。角色标注也不进入常规 Judge 输入。

保存模型回答时保留 query_id、query、extracted_memories、category、response、target_model 和 dataset_sha256。复用回答前必须确认题库 hash 和题目内容对应；两版十维协议可复用同一份匹配的回答，但不能把 v1 旧题回答直接绑定到 v2 修改后的题目。

## 两版十维 Judge

两版均直接独立打1–5整数分并逐维提供理由：整体满意度、对话意愿、情绪愉悦度、意图判断准确、记忆信息准确、信息内容表达清晰、交流流畅、情感表达恰当、风格恰当、社会智能。

| 项目 | 十维 v1 | 十维 v2 |
|---|---|---|
| 协议编号 | `blind_huawei10_v1_query_memory_response_only` | `project_10d_v2_unified_scene_guidance` |
| 标准来源 | 原Huawei十维标准 | 项目统一十维标准，增加场景校准 |
| 场景处理 | 原维度文字 | 明确任务/QA、建议、讨论、情感支持、闲聊、记忆及OP场景 |
| Judge可见输入 | query + memory + 已有response + rubric | 同左 |
| 隐藏标注 | 不传入 | 不传入 |
| 默认汇总 | 原始十维平均分 | 原始十维平均分 |

v2明确客观任务不强求共情、追问或个性化；没有相关记忆时不使用记忆可以获得高分，依然扣罚过度个性化、主体错配与不必要披露。这里只记录现有 prompt，没有重新改写评分尺度。

完整语句见 [`10d_v1/scoring_prompt.md`](protocols/10d_v1/scoring_prompt.md) 与 [`10d_v2/scoring_prompt.md`](protocols/10d_v2/scoring_prompt.md)。两者从实际脚本和 criteria 自动导出，而不是摘要。`score < 4 → 0` 不在 Judge prompt 中，也不是这两个脚本的默认汇总；需要时属于另行后处理。

## 复用已有回答评分

```bash
python3 -m pip install -r v2/requirements.txt
export JUDGE_API_KEY='YOUR_KEY'

python3 v2/protocols/10d_v1/evaluate_10d.py \
  --input /path/to/matching_responses.jsonl \
  --output /path/to/results/10d_v1/results.jsonl \
  --summary-output /path/to/results/10d_v1/summary.json \
  --target-model YOUR_TARGET_MODEL \
  --judge-model deepseek-v4-flash-0731 \
  --base-url http://YOUR_HOST:8010/v1

python3 v2/protocols/10d_v2/evaluate_10d.py \
  --input /path/to/matching_responses.jsonl \
  --output /path/to/results/10d_v2/results.jsonl \
  --summary-output /path/to/results/10d_v2/summary.json \
  --target-model YOUR_TARGET_MODEL \
  --judge-model deepseek-v4-flash-0731 \
  --base-url http://YOUR_HOST:8010/v1
```

输出目录必须分开，避免把两版评分混在一起。目标模型名称按回答文件中的 `target_model` 填写。脚本包含断点续跑、协议编号、回答文件 SHA256 和逐题结果；不会重新生成模型回答。新十维入口默认使用同目录基类，无需依赖服务器绝对路径。Judge推理参数保持来源代码原样，本次没有启动任何评分或更改运行任务。

四维脚本的 `--dataset-sha256` 默认仍为旧题库 hash；用于此主集时必须显式传入 `delivery_manifest.json` 中的 benchmark SHA256。独立安全脚本有意读取隐藏硬失败条件，与常规十维/四维评分分开。

## 离线校验

```bash
python3 v2/tools/build_metadata.py
cd v2
shasum -a 256 -c SHA256SUMS.txt
```

人工双标、Judge人工校准与真正多轮评测不在本次交付完成范围内；隐藏标注来自 DeepSeek，不能表述为已经人工双标验收。
