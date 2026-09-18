"""Build publication tables/figures solely from checked-in evaluation results.

Run: python tools/build_performance_reports.py [--plots]
No model calls. Stdlib for data validation/tables; matplotlib for scientific figures.
"""
from pathlib import Path
from collections import defaultdict
import argparse
import csv
import hashlib
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/model_performance'
SRC = OUT / 'sources'
MODELS = ['gpt_4o','gpt_oss_20b','harmonic_step600','opsd_step1192','opsd_step900','qwen35_9b_base']
NAMES = dict(zip(MODELS, ['GPT-4o','GPT-OSS-20B','Harmonic Step600','OPSD Step1192','OPSD Step900','Qwen3.5-9B 原版']))
ALIASES = {'harmonic0830_step600':'harmonic_step600','qwen35_9b_grpo_opsd_step1192':'opsd_step1192',
           'qwen35_9b_grpo_opsd_step900':'opsd_step900','qwen35_9b':'qwen35_9b_base'}
TABLES = []
PLOTS = {}
CHECKS = []

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def csvrows(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def close(a,b):
    assert math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,abs_tol=1e-9), (a,b)

def value(v):
    if v is None: return '—'
    if isinstance(v,float): return f'{v:.4f}'
    return str(v).replace('|','\\|').replace('\n',' ')

def table(slug,title,rows,note):
    assert rows
    headers=list(rows[0])
    assert all(list(r)==headers for r in rows)
    path=OUT/'tables'/slug
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix('.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=headers,lineterminator='\n')
        writer.writeheader();writer.writerows(rows)
    md=f'# {title}\n\n{note}\n\n'
    md+='| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'
    md+=''.join('| '+' | '.join(value(r[h]) for h in headers)+' |\n' for r in rows)
    path.with_suffix('.md').write_text(md,encoding='utf-8')
    TABLES.append({'slug':slug,'title':title,'rows':len(rows)})

def check_summary(d):
    assert d.get('num_items',d.get('count'))==1000
    assert d.get('api_errors',0)==0 and d.get('parse_failures',0)==0
    assert len(d['dimension_averages'])==10
    assert all(1<=v<=5 for v in d['dimension_averages'].values())
    close(statistics.mean(d['dimension_averages'].values()),d['macro_average'])

def build_10d():
    aggregates=csvrows(SRC/'deepseek_rejudge/aggregate_all_methods.csv')
    assert len(aggregates)==36
    lookup={(r['协议'],r['模型目录'],r['口径']):r for r in aggregates}
    assert len(lookup)==36
    audit=read(SRC/'deepseek_rejudge/audit.json')
    oss=read(SRC/'gptoss_rejudge_summary.json')
    original_ids={json.loads(line)['query_id'] for line in (ROOT/'benchmark/benchmark_1000.jsonl').read_text().splitlines()}
    paired={(r['协议'],r['模型目录']):r for r in csvrows(SRC/'deepseek_rejudge/deepseek_vs_gptoss_raw.csv')}
    combined=[]; ranked=[]; dims=[]; abc=[]
    for protocol,title in [('old','旧版十维'),('new','新版十维')]:
        detail=csvrows(SRC/f'deepseek_rejudge/{protocol}_10d_detail.csv')
        assert len(detail)==6000
        bymodel=defaultdict(list)
        for r in detail:
            assert r['协议']==protocol
            bymodel[r['模型目录']].append(r)
        assert set(bymodel)==set(MODELS)
        first={}; current={}; other={}
        comparison=[]
        for m in MODELS:
            records=bymodel[m]
            assert len(records)==1000 and len({r['query_id'] for r in records})==1000
            assert {r['query_id'] for r in records}==original_ids
            d=read(ROOT/f'models/{m}/deepseek_summary_10d.json') if protocol=='old' else read(SRC/f'deepseek_first_new10d/{m}/summary.json')
            check_summary(d);check_summary(oss[protocol][m])
            if protocol=='old':
                original=[json.loads(line) for line in (ROOT/f'models/{m}/deepseek_scores_10d.jsonl').read_text().splitlines()]
                assert len(original)==1000 and {r['query_id'] for r in original}==original_ids
                for dim,expected in d['dimension_averages'].items():
                    close(statistics.mean(r['scores'][dim] for r in original),expected)
            assert d['inference_results_sha256']==audit['input_sha256'][m]==oss[protocol][m]['input_sha256']
            dimensions=list(d['dimension_averages'])
            matrix=[[int(r[f'{dim}_分']) for dim in dimensions] for r in records]
            assert all(all(1<=v<=5 for v in row) for row in matrix)
            assert all(all(r[f'{dim}_理由'].strip() for dim in dimensions) for r in records)
            assert all(r['输入SHA256']==audit['input_sha256'][m] for r in records)
            zero_count=sum(any(v<4 for v in row) for row in matrix)
            for method in ['A_raw','B_single_zero','C_whole_zero']:
                transformed=[row if method=='A_raw' else [v if v>=4 else 0 for v in row] if method=='B_single_zero'
                             else row if min(row)>=4 else [0]*10 for row in matrix]
                total=sum(map(sum,transformed));record=lookup[protocol,m,method]
                assert total==int(record['保留分数总和'])
                close(total/10000,float(record['十维均分_分母10000']))
                assert zero_count==int(record['整题归零题数'])
                close(zero_count/1000,float(record['整题归零比例']))
                for i,dim in enumerate(dimensions):
                    close(sum(row[i] for row in transformed)/1000,float(record[f'{dim}_均分_分母1000']))
            first[m]=d['macro_average'];current[m]=float(lookup[protocol,m,'A_raw']['十维均分_分母10000']);other[m]=oss[protocol][m]['macro_average']
            close(current[m],float(paired[protocol,m]['DeepSeek十维均分']))
            close(other[m],float(paired[protocol,m]['GPTOSS十维均分']))
            row={'模型':NAMES[m],'DeepSeek_首次':first[m],'DeepSeek_复评':current[m],'GPTOSS_复评':other[m]}
            comparison.append(row);combined.append({'协议':title,**row})
            abc.append({'协议':title,'模型':NAMES[m],'A_原始均分':current[m],
                        'B_单维归零':float(lookup[protocol,m,'B_single_zero']['十维均分_分母10000']),
                        'C_整题归零':float(lookup[protocol,m,'C_whole_zero']['十维均分_分母10000']),
                        '整题归零题数':zero_count,'整题归零比例':zero_count/1000,
                        'C_保留分数总和':int(lookup[protocol,m,'C_whole_zero']['保留分数总和'])})
            for judge,metrics in [('DeepSeek_首次',d['dimension_averages']),('GPTOSS_复评',oss[protocol][m]['dimension_averages']),
                                  ('DeepSeek_复评',{dim:float(lookup[protocol,m,'A_raw'][f'{dim}_均分_分母1000']) for dim in dimensions})]:
                dims.append({'协议':title,'Judge批次':judge,'模型':NAMES[m],**metrics})
        table(f'{protocol}_10d_judges',f'{title}：三组Judge评分',comparison,
              '早期1000题，同一批回答；原始1–5分均值。首次DeepSeek读取实际summary.json；复评读取逐题CSV并重算。GPT-OSS给GPT-OSS-20B的评分属于自评。')
        PLOTS[f'{protocol}_10d_three_judges']={'title':f'{title}：三组 Judge 评分','ylabel':'十维均分（1–5 分）',
                 'series':{'DeepSeek：首次':[first[m] for m in MODELS],'DeepSeek：复评':[current[m] for m in MODELS],
                           'GPT-OSS：复评':[other[m] for m in MODELS]},'ylim':[3.9,5.03]}
        for label,scores in [('DeepSeek_首次',first),('DeepSeek_复评',current),('GPTOSS_复评',other)]:
            for m in MODELS:
                ranked.append({'协议':title,'Judge批次':label,'模型':NAMES[m],'均分':scores[m],
                               '排名':1+sum(v>scores[m]+1e-12 for v in scores.values())})
        CHECKS.append(f'{protocol}: 6000 model/query rows match benchmark IDs; all A/B/C totals and 180 dimension means recomputed')
    table('10d_rankings','十维排名',ranked,'早期1000题；按完整精度均分降序计算排名，相同分数共享排名。不同协议与Judge分别排名。')
    table('10d_dimensions','十维逐维均分',dims,'早期1000题，三组Judge、两套评分协议；每个维度分母均为1000。')
    table('10d_abc','DeepSeek复评：三种统计口径',abc,'A：原始分；B：仅低于4的维度归零；C：任一维低于4则整题归零。三种总体分母均为1000×10，不删除题目。')
    for protocol,title in [('old','旧版十维'),('new','新版十维')]:
        rows=[r for r in abc if r['协议']==title]
        PLOTS[f'{protocol}_10d_abc']={'title':f'{title}：原始与归零口径','ylabel':'十维均分（归零后 0–5 分）',
                 'series':{k:[r[k] for r in rows] for k in ['A_原始均分','B_单维归零','C_整题归零']},'ylim':[0,5]}

def build_4d():
    rows=[];direct=[];slices=[];comparison=[]
    for m in MODELS:
        early=read(ROOT/f'models/{m}/deepseek_summary_4d.json')
        strictfile=SRC/f'strict4d/{m}.json'
        strict=read(strictfile) if strictfile.exists() else None
        if strict:
            assert strict['num_items']==1000
            assert strict['inference_results_sha256']==early['input_sha256']
        comparison.append({'模型':NAMES[m],'严格四维_均分':strict['overall']['macro_average'] if strict else None,
                            '严格四维_调和分':strict['overall']['top_level_harmonic'] if strict else None,
                            '平衡四维_均分':early['mean_per_item']['four_dim_macro'],
                            '平衡四维_调和分':early['mean_per_item']['four_dim_harmonic']})
        for dataset,base in [('早期题库',ROOT),('修订题库',ROOT/'v2')]:
            p=base/f'models/{m}/deepseek_summary_4d.json'
            if not p.exists():continue
            d=read(p);assert d['num_items']==1000
            assert sum(d['op_score_distribution'].values())==1000
            bad=sum(d['op_score_distribution'][str(i)] for i in [1,2,3])
            rows.append({'题库':dataset,'模型':NAMES[m],'题数':1000,'四维均分':d['mean_per_item']['four_dim_macro'],
                         '四维调和分':d['mean_per_item']['four_dim_harmonic'],
                         'OP惩罚后最终分':d['mean_per_item']['final_op_penalized_score'],'OP低于4题数':bad,'OP低于4比例':bad/1000})
            direct.append({'题库':dataset,'模型':NAMES[m],**d['direct_dimension_averages'],
                           'EI_逐题调和后均值':d['mean_per_item']['emotional_intelligence_harmonic']})
            for category,g in d['groups'].items():
                slices.append({'题库':dataset,'模型':NAMES[m],'类别':category,'题数':g['count'],'OP惩罚后最终分':g['mean_final_op_penalized_score']})
    table('balanced4_overview','两套题库：平衡四维',rows,'均分、调和分、OP惩罚后分数均为逐题计算后平均1000题。GPT-4o无修订题库结果。OP低于4仅为计数，不改变均分。')
    table('balanced4_dimensions','平衡四维：直接维度与EI',direct,'Task、Memory、OP、Resonation、Expression、Reception为六个直接评分字段；EI为后三项逐题调和后平均。')
    table('balanced4_categories','平衡四维：类别切片',slices,'各类别分别以自身题数为分母；早期每类250题，修订题库配额不同，不应把类别均值不加权平均成总分。')
    table('strict_vs_balanced4','早期题库：严格四维与平衡四维',comparison,'使用实际summary.json。两套评分协议不同，不是两套题库；GPT-4o严格四维缺失，留空。')
    PLOTS['strict_vs_balanced4']={'title':'早期题库：严格四维与平衡四维','ylabel':'四维评分（1–5 分）',
                               'series':{key:[r[key] for r in comparison] for key in list(comparison[0])[1:]},'ylim':[3.35,4.95]}
    for metric,slug,lim in [('四维均分','balanced4_datasets',[4.4,4.9]),('OP低于4比例','op_badcase_rates',[0,.13])]:
        PLOTS[slug]={'title':f'两套题库：{metric}','ylabel':metric+('（0–1）' if '比例' in metric else '（1–5 分）'),
            'series':{ds:[next((r[metric] for r in rows if r['题库']==ds and r['模型']==NAMES[m]),None) for m in MODELS]
                      for ds in ['早期题库','修订题库']},'ylim':lim}

def build_teacher():
    rows=[];gated=[];safety=[];slices=[];reasoning=[]
    gate=read(SRC/'teacher_all_or_zero.json')
    bymodel={ALIASES.get(x['model_key'],x['model_key']):x for x in gate['models']}
    evaldata=read(SRC/'teacher_safety_reasoning.json')
    safebymodel={ALIASES.get(x['model_key'],x['model_key']):x for x in evaldata['safety_100']}
    reasonbymodel={ALIASES.get(x['model_key'],x['model_key']):x for x in evaldata['reasoning_comparison']['models']}
    for m in MODELS[1:]:
        d=read(SRC/f'teacher_old10d/{m}.json');check_summary(d)
        assert d['inference_results_sha256']==sha(ROOT/f'v2/models/{m}/responses.jsonl')
        rows.append({'模型':NAMES[m],'题数':d['num_items'],'十维均分':d['macro_average'],**d['dimension_averages']})
        g=bymodel[m];four=g['four_dim'];ten=g['ten_dim']
        assert four['items']==ten['items']==1000
        assert four['source_sha256']==sha(ROOT/f'v2/models/{m}/deepseek_scores_4d.jsonl')
        actual=[json.loads(line) for line in (ROOT/f'v2/models/{m}/deepseek_scores_4d.jsonl').read_text().splitlines()]
        assert len(actual)==1000
        passed=[r for r in actual if min(r['scores'].values())>=4]
        assert len(passed)==four['strict_pass_count']
        derived=defaultdict(float);original_cap_total=0
        for r in passed:
            s=r['scores'];ei=statistics.harmonic_mean([s['resonation'],s['expression'],s['reception']])
            top=[s['task_quality'],s['memory_usage'],s['over_personalization_restraint'],ei]
            harmonic=statistics.harmonic_mean(top)
            derived['four_dim_macro']+=statistics.mean(top)
            derived['four_dim_harmonic']+=harmonic
            derived['final_op_penalized_score']+=min(harmonic,{1:1.5,2:2.5,3:3.5,4:4.5,5:5}[s['over_personalization_restraint']])
            original_cap_total+=min(harmonic,{1:1.5,2:2.5,3:3.5,4:5,5:5}[s['over_personalization_restraint']])
        for key,total in derived.items():close(total/1000,four['mean_per_item'][key])
        close(ten['strict_pass_count']/1000,ten['strict_pass_rate']);close(four['strict_pass_count']/1000,four['strict_pass_rate'])
        close(statistics.mean(ten['dimension_averages'].values()),ten['macro_average'])
        gated.append({'模型':NAMES[m],'十维通过题数':ten['strict_pass_count'],'十维通过比例':ten['strict_pass_rate'],
                      '十维归零均分':ten['macro_average'],'四维通过题数':four['strict_pass_count'],'四维通过比例':four['strict_pass_rate'],
                      '四维均分_逐题平均':four['mean_per_item']['four_dim_macro'],
                      '四维调和分_逐题平均':four['mean_per_item']['four_dim_harmonic'],
                      '最终分_原平衡协议OP4上限5':original_cap_total/1000,
                      '最终分_历史后处理OP4上限4.5':four['mean_per_item']['final_op_penalized_score'],
                      '四维均分_先维度平均':four['aggregate_of_dimension_means']['four_dim_macro'],
                      '四维调和分_先维度平均':four['aggregate_of_dimension_means']['four_dim_harmonic']})
        s=safebymodel[m];assert s['items']==100
        close(s['hard_failure_count']/100,s['hard_failure_rate'])
        safety.append({'模型':NAMES[m],'题数':100,'严格通过比例':s['strict_pass_rate'],'硬失败题数':s['hard_failure_count'],
                       '硬失败比例':s['hard_failure_rate'],'安全总分':s['overall_safety_score'],
                       '必做项遵循':s['must_do_compliance'],'记忆边界安全':s['memory_boundary_safety']})
        assert sum(x['count'] for x in s['slices'].values())==100
        assert sum(x['hard_failure_count'] for x in s['slices'].values())==s['hard_failure_count']
        for cat,x in s['slices'].items():
            slices.append({'模型':NAMES[m],'切片':cat,**x})
        r=reasonbymodel[m];assert r['items']==1000
        off=r['thinking_off']['final_op_penalized_score'];on=r['thinking_on']['final_op_penalized_score']
        close(off,read(ROOT/f'v2/models/{m}/deepseek_summary_4d.json')['mean_per_item']['final_op_penalized_score'])
        close(on-off,r['delta_on_minus_off']['final_op_penalized_score'])
        reasoning.append({'模型':NAMES[m],'Off最终分':off,'Off排名':r['thinking_off']['rank'],
                          'On最终分':on,'On排名':r['thinking_on']['rank'],'On减Off':on-off,
                          '逐维一致比例':r['per_item_agreement']['overall_exact_score_rate'],
                          '逐维平均绝对差':r['per_item_agreement']['overall_mean_absolute_difference'],
                          '逐题最终分Spearman':r['per_item_agreement']['final_score_spearman']})
    table('teacher_old10d','修订题库：旧版十维',rows,'这是修订后的1000题，采用旧版十维rubric。与“早期题库＋新版十维”不同，不混用排名。')
    table('teacher_all_or_zero','修订题库：整题归零',gated,'十维对十个直接维度门控；平衡四维对六个直接字段门控。任一低于4则该协议该题全0，分母仍1000。默认逐题平均。历史后处理另把OP=4的上限从5改成4.5；保留该历史结果并单列按原平衡协议重算的结果，不混用。')
    table('safety100','独立Safety-100',safety,'与主1000题分开。比例用0–1表示；安全评分1–5，Judge thinking-off。严格通过与无硬失败不是同一指标。')
    table('safety100_slices','Safety-100：切片',slices,'每模型四类各25题。所有切片比例以对应25题为分母。')
    table('reasoning_modes','修订题库：Judge thinking on/off',reasoning,'复用同一批回答，只改变Judge thinking mode。最终分是OP惩罚后逐题平均；不是被测模型切换thinking。五模型排名Spearman=0.9（来源汇总）。')
    PLOTS['judge_thinking_modes']={'title':'修订题库：Judge thinking on/off','ylabel':'OP惩罚后最终分（1–5 分）',
                'series':{k:[None]+[r[k] for r in reasoning] for k in ['Off最终分','On最终分']},'ylim':[4.4,4.9]}
    PLOTS['safety100_pass_rates']={'title':'Safety-100：严格通过与硬失败','ylabel':'比例（0–1）',
                'series':{k:[None]+[r[k] for r in safety] for k in ['严格通过比例','硬失败比例']},'ylim':[0,1]}
    CHECKS.append('Teacher summaries: 5×1000; gate source SHA matches published rows and all four-dimensional gate means recomputed; historical OP4 cap=4.5 and original cap=5 reported separately; safety slice totals and reasoning off/on deltas match')

def plots():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    available={f.name for f in font_manager.fontManager.ttflist}
    font=next((n for n in ['Arial Unicode MS','Noto Sans CJK SC','SimHei'] if n in available),'DejaVu Sans')
    plt.rcParams.update({'font.family':font,'axes.unicode_minus':False,'font.size':12,'pdf.fonttype':42,'svg.fonttype':'path','svg.hashsalt':'ei-op-evaluation'})
    colors=['#24759C','#C66A24','#7853A2','#397C54'];markers=['o','s','^','D']
    for slug,d in PLOTS.items():
        fig,ax=plt.subplots(figsize=(12.6,7.3))
        fig.subplots_adjust(left=.085,right=.97,bottom=.20,top=.78)
        fig.text(.085,.94,d['title'],fontsize=22,weight='bold')
        fig.text(.085,.888,'固定模型顺序；由结果文件自动生成',fontsize=12,color='#555555')
        for i,(name,vals) in enumerate(d['series'].items()):
            y=[math.nan if v is None else v for v in vals]
            assert len(y)==6
            ax.plot(range(6),y,label=name,color=colors[i],marker=markers[i],linewidth=2,markersize=7,
                    linestyle=['--','-','-.',':'][i])
        ax.set_xticks(range(6),['GPT-4o','GPT-OSS-20B','Harmonic\nStep600','OPSD\nStep1192','OPSD\nStep900','Qwen3.5-9B\n原版'])
        ax.set_xlim(-.25,5.25);ax.set_ylim(*d['ylim']);ax.set_ylabel(d['ylabel'])
        ax.grid(axis='y',alpha=.22);ax.spines[['top','right']].set_visible(False)
        ax.legend(loc='lower left',bbox_to_anchor=(-.01,1.015),ncol=2 if len(d['series'])==4 else 3,frameon=False,fontsize=11)
        fig.text(.085,.08,f"纵轴范围 {d['ylim'][0]}–{d['ylim'][1]}；模型是离散类别，连线不代表训练时间。",fontsize=10,color='#666666')
        fig.text(.085,.04,'缺失结果保留为空，不补零、不插值；精确数值见对应 CSV 与 Markdown 表。',fontsize=10,color='#666666')
        for ext in ['png','svg','pdf']:
            metadata={'CreationDate':None,'ModDate':None} if ext=='pdf' else {'Date':None} if ext=='svg' else {}
            fig.savefig(OUT/f'figures/{slug}.{ext}',dpi=180,facecolor='white',metadata=metadata)
        plt.close(fig)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plots',action='store_true');args=parser.parse_args()
    sources=read(OUT/'source_manifest.json')['files']
    for item in sources:
        assert sha(ROOT/item['published'])==item['sha256'],item['published']
    (OUT/'figures').mkdir(parents=True,exist_ok=True)
    build_10d();build_4d();build_teacher()
    (OUT/'figures/plot_data.json').write_text(json.dumps({'models':MODELS,'plots':PLOTS},ensure_ascii=False,indent=2)+'\n')
    if args.plots:plots()
    report={'status':'PASS','source_files_verified':len(sources),'tables':TABLES,'figures':list(PLOTS),
            'checks':CHECKS,'limits':'Historical strict, first/new10d, GPTOSS, teacher10d, safety and reasoning use recorded summaries; first/old10d and teacher four-dimensional gating additionally recomputed from published rows; DeepSeek rescore A/B/C recomputed from 12000 detail rows. No fresh judging or statistical significance claim.'}
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'PASS','tables':len(TABLES),'figures':len(PLOTS)},ensure_ascii=False))

if __name__=='__main__':main()
