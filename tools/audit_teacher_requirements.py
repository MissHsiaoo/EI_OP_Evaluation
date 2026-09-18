"""Recompute structural evidence, not human/semantic acceptance. No API calls."""
import collections
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/teacher_requirements'


def rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    data = rows(ROOT / 'v2/benchmark/benchmark_1000.jsonl')
    roles = rows(ROOT / 'v2/annotations/memory_roles.jsonl')
    ei = rows(ROOT / 'v2/annotations/ei_memory_dependency.jsonl')
    repairs = rows(OUT / 'sources/revision_records.jsonl')
    assert len(data) == len({r['query_id'] for r in data}) == 1000
    assert len(roles) == 1000 and {r['query_id'] for r in roles} == {r['query_id'] for r in data}
    assert len(repairs) == len({r['query_id'] for r in repairs}) == 166
    assert all(r['audit']['pass'] is True for r in repairs)
    explicit = re.compile(r'\[ERROR[^\]]*\]|\[不确定[^\]]*\]|\[错误[^\]]*\]', re.I)
    categories = ['memory::irrelevant_error_suppression', 'over_personalization::uncertain_error_memory']
    labels = {}
    for cat in categories:
        subset = [r for r in data if r['category'] == cat]
        marked = [r['query_id'] for r in subset if explicit.search(' '.join(r['extracted_memories']))]
        labels[cat] = dict(total=len(subset), with_explicit_label=len(marked), without_explicit_label=len(subset)-len(marked), marked_query_ids=marked)
    flags = []
    for r in roles:
        reasons = []
        entries = r.get('must_do', []) + r.get('must_not_do', [])
        if set(r.get('must_do', [])) & set(r.get('must_not_do', [])):
            reasons.append('identical_entry_in_must_do_and_must_not_do')
        if re.search(r'annotation|supplied case order|never renumber|memory_roles entry|Do not write an answer', ' '.join(entries), re.I):
            reasons.append('annotation_instruction_text')
        if any(s.strip().lower() in {'required', 'beneficial', 'neutral', 'prohibited', 'n/a', 'none'} for s in entries):
            reasons.append('bare_role_label_or_placeholder')
        if reasons:
            flags.append(dict(query_id=r['query_id'], flags=reasons))
    safety = rows(ROOT / 'v2/safety_100/benchmark_100.jsonl')
    report = {
        'scope': 'Published v2 snapshot; mechanical counts are not semantic validation or human sign-off.',
        'benchmark_sha256': digest(ROOT / 'v2/benchmark/benchmark_1000.jsonl'),
        'main_items': len(data),
        'unique_session_ids': len({r['session_id'] for r in data}),
        'category_counts': dict(collections.Counter(r['category'].split('::')[0] for r in data)),
        'repair_records': len(repairs), 'machine_audit_passes': sum(r['audit']['pass'] for r in repairs),
        'stale_repairs': sum(r['original_case']['category'] == 'memory::stale_memory_override' for r in repairs),
        'role_annotation_rows': len(roles),
        'ei_targeted_memory_dependent': sum(r['targeted_memory_dependent'] for r in ei),
        'ei_controls': sum(not r['targeted_memory_dependent'] for r in ei),
        'safety_items': len(safety),
        'error_label_check': {'pattern': explicit.pattern, 'categories': labels, 'limitation': 'Absence of these literal markers does not prove unambiguous factual reasoning.'},
        'annotation_screening': {'unique_flagged_items': len(flags), 'flag_counts': dict(collections.Counter(f for r in flags for f in r['flags'])), 'items': flags, 'limitation': 'Flags overlap and require human review; this is not an error rate.'},
    }
    (OUT / 'structural_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in {'annotation_screening', 'error_label_check'}}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
