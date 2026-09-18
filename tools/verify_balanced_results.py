#!/usr/bin/env python3
"""Offline verification and tables for two datasets scored with balanced 4D.

No inference, Judge calls or edits to source responses/scores/summaries.
Run from any directory: python3 tools/verify_balanced_results.py
"""
import ast
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'balanced_four_dim_v2_no_gold_op_penalty'
JUDGE = 'deepseek-v4-flash-0731'
MODELS = {
    'opsd_step900': ('OPSD Step900', 'qwen35_9b_grpo_opsd_step900'),
    'opsd_step1192': ('OPSD Step1192', 'qwen35_9b_grpo_opsd_step1192'),
    'qwen35_9b_base': ('Qwen3.5-9B 原版', 'qwen35_9b'),
    'gpt_4o': ('GPT-4o', 'gpt_4o'),
    'harmonic_step600': ('Harmonic Step600', 'harmonic0830_step600'),
    'gpt_oss_20b': ('GPT-OSS-20B', 'gpt_oss_20b'),
}
DIMS = ('task_quality','memory_usage','over_personalization_restraint','resonation','expression','reception')
CAPS = {1:1.5,2:2.5,3:3.5,4:5.0,5:5.0}


def load(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def harmonic(values):
    return len(values)/math.fsum(1/v for v in values)


def close(a,b,label):
    if not math.isclose(a,b,rel_tol=0,abs_tol=1e-10):
        raise ValueError(f'{label}: {a} != {b}')


def table(rows):
    header=['模型','题数','四维均分','四维调和分','OP惩罚后最终分','OP<4题数']
    lines=['| '+' | '.join(header)+' |','| '+' | '.join(['---']*len(header))+' |']
    for r in sorted(rows,key=lambda r:r['four_dim_macro'],reverse=True):
        lines.append('| '+' | '.join([r['model'],str(r['num_items']),*[f'{r[k]:.4f}' for k in ('four_dim_macro','four_dim_harmonic','final_op_penalized_score')],str(r['op_below_4'])])+' |')
    return '\n'.join(lines)+'\n'


def main():
    sources=json.loads((ROOT/'reports/balanced4_source_manifest.json').read_text())
    for relative, item in sources['files'].items():
        assert sha(ROOT/relative)==item['sha256'], f'source snapshot changed: {relative}'
    # Derivation must still match both exact scoring source snapshots.
    for source in (ROOT/'protocols/evaluate_4d.py',ROOT/'v2/protocols/balanced4_scoring_snapshot/evaluate_4d.py'):
        tree=ast.parse(source.read_text())
        nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in ('harmonic','derived_scores')) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OP_CAPS' for t in n.targets))]
        ns={}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
        for score in range(1,6):
            s=dict.fromkeys(DIMS,score)
            derived=ns['derived_scores'](s)
            close(derived['four_dim_macro'],score,'protocol macro')
            close(derived['final_op_penalized_score'],min(score,CAPS[score]),'protocol cap')
    audit={'status':'PASS','protocol':PROTOCOL,'judge':JUDGE,'datasets':{},'source_manifest':'reports/balanced4_source_manifest.json'}
    all_rows=[]
    for version,base in [('early',ROOT),('teacher',ROOT/'v2')]:
        dataset=base/'benchmark/benchmark_1000.jsonl'
        benchmark=load(dataset)
        by_id={r['query_id']:r for r in benchmark}
        assert len(benchmark)==len(by_id)==1000
        dataset_sha=sha(dataset)
        models={k:v for k,v in MODELS.items() if version=='early' or k!='gpt_4o'}
        info={'benchmark_sha256':dataset_sha,'num_items':1000,'models':{}}
        table_rows=[]
        for slug,(display,target) in models.items():
            if version == 'teacher' and slug == 'qwen35_9b_base':
                target = 'qwen35_9b_base'
            folder=base/'models'/slug
            response_file=folder/'responses.jsonl'
            score_file=folder/'deepseek_scores_4d.jsonl'
            summary_file=folder/'deepseek_summary_4d.json'
            responses=load(response_file)
            scored=load(score_file)
            summary=json.loads(summary_file.read_text())
            response_map={r['query_id']:r for r in responses}
            score_map={r['query_id']:r for r in scored}
            assert len(responses)==len(response_map)==len(scored)==len(score_map)==1000,(version,slug)
            assert set(response_map)==set(score_map)==set(by_id),(version,slug,'ID set')
            input_sha=sha(response_file)
            assert summary['input_sha256']==input_sha
            assert summary['dataset_sha256']==dataset_sha
            assert summary['num_items']==1000 and summary['api_errors']==summary['parse_failures']==0
            assert summary['protocol']==PROTOCOL and summary['judge_model']==JUDGE and summary['target_model']==target
            rebuilt=[]
            for qid,row in score_map.items():
                response=response_map[qid]
                b=by_id[qid]
                for key in ('query','extracted_memories','category','prompt'):
                    assert row[key]==response[key]==b[key],(version,slug,qid,key)
                assert row['response']==response['response'] and row['response'].strip(),(version,slug,qid,'response')
                assert row['target_model']==response['target_model']==target
                assert row['input_dataset_sha256']==response['input_dataset_sha256']==dataset_sha
                assert row['input_sha256']==input_sha and row['protocol']==PROTOCOL and row['judge_model']==JUDGE
                assert not row.get('error') and row.get('judge_raw')
                s=row['scores']
                assert set(s)==set(row['reasons'])==set(DIMS)
                assert all(type(s[d]) is int and 1<=s[d]<=5 for d in DIMS)
                assert all(isinstance(row['reasons'][d],str) and row['reasons'][d].strip() for d in DIMS)
                ei=harmonic([s[d] for d in ('resonation','expression','reception')])
                top=[s[d] for d in DIMS[:3]]+[ei]
                h=harmonic(top)
                derived={'emotional_intelligence_harmonic':ei,'four_dim_macro':math.fsum(top)/4,'four_dim_harmonic':h,
                         'over_personalization_cap':CAPS[s['over_personalization_restraint']],
                         'final_op_penalized_score':min(h,CAPS[s['over_personalization_restraint']])}
                for key,value in derived.items():
                    close(value,row['derived_scores'][key],f'{version}/{slug}/{qid}/{key}')
                rebuilt.append(derived)
            for key,value in summary['mean_per_item'].items():
                close(math.fsum(r[key] for r in rebuilt)/1000,value,f'{slug}/summary/{key}')
            for key in DIMS:
                close(math.fsum(r['scores'][key] for r in scored)/1000,summary['direct_dimension_averages'][key],key)
            op=Counter(str(r['scores']['over_personalization_restraint']) for r in scored)
            assert all(op[str(i)]==summary['op_score_distribution'][str(i)] for i in range(1,6))
            for group,group_summary in summary['groups'].items():
                matched=[r for r in scored if r['category'].split('::',1)[0]==group]
                assert len(matched)==group_summary['count']
                close(math.fsum(r['derived_scores']['final_op_penalized_score'] for r in matched)/len(matched),group_summary['mean_final_op_penalized_score'],group)
            entry={'dataset':version,'model':display,'model_slug':slug,'num_items':1000,
                   **{k:summary['mean_per_item'][k] for k in ('four_dim_macro','four_dim_harmonic','final_op_penalized_score')},
                   'op_below_4':sum(op[str(i)] for i in range(1,4)),**summary['direct_dimension_averages'],
                   'emotional_intelligence_harmonic':summary['mean_per_item']['emotional_intelligence_harmonic']}
            table_rows.append(entry)
            info['models'][slug]={'num_items':1000,'unique_query_ids':1000,'query_memory_prompt_match_benchmark':True,
                                'response_matches_inference':True,'derived_and_summary_recomputed':True,
                                'paths':{p.name:str(p.relative_to(ROOT)) for p in (response_file,score_file,summary_file)}}
        audit['datasets'][version]=info
        all_rows.extend(table_rows)
        if version=='teacher':
            (base/'summary_table.md').write_text('# 修订题库：DeepSeek 平衡四维评分\n\n五个模型各1000题。GPT-4o 尚无此题库结果。均分、调和分、OP惩罚后分数均为逐题计算后平均。\n\n'+table(table_rows))
            with (base/'summary_table.csv').open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(table_rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(sorted(table_rows,key=lambda r:r['four_dim_macro'],reverse=True))
    (ROOT/'reports/balanced4_validation.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    with (ROOT/'reports/balanced4_versions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(all_rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(all_rows)
    text='''# 两套题库的平衡四维评分

这里的“早期/修订”指数据版本。两组均使用平衡四维协议 `balanced_four_dim_v2_no_gold_op_penalty`，Judge 为 `deepseek-v4-flash-0731`，不是早期约3.5–3.8分的严格四维评分。不同题库的绝对分差不直接等同于模型能力变化。

## 早期1000题（六个模型，包含GPT-4o）

原始评分位于根目录 `models/<模型>/deepseek_scores_4d.jsonl`，与NAS的 `harmonic_four_dimension_eval_1000_balanced_v2/results/<模型>/deepseek/results.jsonl` 字节一致，原有结果未改动。

'''+table([r for r in all_rows if r['dataset']=='early'])+'''
## 老师建议修订后的1000题（五个模型）

新增结果位于 `v2/models/<模型>/`，来自NAS的 `harmonic_four_dimension_eval_1000_teacher_balanced_v2/evaluation_all_models_v1/<模型>/judges_balanced4/deepseek/`。GPT-4o未在本题库评分，不能用早期题库分数补入。

'''+table([r for r in all_rows if r['dataset']=='teacher'])+'''
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
'''
    (ROOT/'reports/balanced4_versions.md').write_text(text)
    existing_paths={line.split('  ',1)[1] for line in (ROOT/'SHA256SUMS.txt').read_text().splitlines() if line.strip()}
    existing_paths.update({'tools/verify_balanced_results.py','reports/balanced4_versions.md',
                           'reports/balanced4_versions.csv','reports/balanced4_source_manifest.json',
                           'reports/balanced4_validation.json'})
    (ROOT/'SHA256SUMS.txt').write_text(''.join(f'{sha(ROOT/p)}  {p}\n' for p in sorted(existing_paths)))
    print(json.dumps({'status':'PASS','early_groups':6,'teacher_groups':5,'total_scored':11000},ensure_ascii=False))


if __name__=='__main__':
    main()
