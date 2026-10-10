"""Read-only post-hoc census of frozen primary control findings and A2 coverage.

This reaggregates archived scores and historical adjudication decisions. It does
not run a checker, revise labels, validate sources, or add independent A2 review.
"""
from pathlib import Path
import argparse
import json
import hashlib
import sys
from collections import Counter

# The inherited semantic checks use assertions; never silently disable them.
if not __debug__:
    raise SystemExit("ERROR: Python optimization is unsupported; run without -O or PYTHONOPTIMIZE.")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--package', required=True, type=Path,
                    help='Absolute or relative replication_package directory')
args = parser.parse_args()
PB = args.package.resolve() / 'experiments/pathb_v2'
if not PB.is_dir():
    parser.error('package must contain experiments/pathb_v2')
inputs = {}
def read(p):
    p = PB / p
    resolved = p.resolve(strict=True)
    if not resolved.is_relative_to(PB.resolve()):
        raise ValueError('input escapes the pathb_v2 directory: ' + str(p))
    b = p.read_bytes()
    key = p.relative_to(PB).as_posix()
    digest = hashlib.sha256(b).hexdigest()
    if key in inputs and inputs[key] != digest:
        raise ValueError('input changed during census: ' + key)
    inputs[key] = digest
    return json.loads(b)

# This sidecar is scoped to the retained 126-score frozen primary cohort and
# five historical A2 packet files. Reject incomplete or expanded inventories.
score_paths = sorted((PB / 'scores_adjudicated').glob('*.json'))
packet_paths = sorted((PB / 'adjudication/packets').glob('A2_*.json'))
if len(score_paths) != 126 or len(packet_paths) != 5:
    raise ValueError('expected frozen primary inventory: 126 scores and 5 A2 packet files')
# Pin only the retained primary case identities, not their scientific outcomes.
# Derived from the archived independently checked census's 126 score paths.
# This is a historical scope constraint, not whole-package authentication.
EXPECTED_COHORT_ID_SHA256 = '465886ad493f4178b45e98c0902931ec211566b05c24b8db3a9ca8d02e81db36'
actual_cohort_digest = hashlib.sha256(('\n'.join(sorted(p.stem for p in score_paths)) + '\n').encode()).hexdigest()
if actual_cohort_digest != EXPECTED_COHORT_ID_SHA256:
    raise ValueError('score identities differ from the retained 126-case primary cohort')
roles=read(Path('ledger/adjudicators.json'))
labels=read(Path('ledger/method_labels.json'))
pilot=set(read(Path('pilot/PILOT_CASES.json'))['quarantined_pilot_cases'])
selected=set(read(Path('candidates/C3_selection.json'))['selected'])
overrides=read(Path('adjudicated/overrides.json'))
superseded=set(read(Path('ledger/a2_r3_supersedes.json')).values())
fold={x['item']:x for x in read(Path('adjudicated/fold_log.json')) if x['item'].startswith('A2-')}
packets={}
for path in packet_paths:
 for x in read(path.relative_to(PB)):
  assert x['item_id'] not in packets or packets[x['item_id']]==x
  packets[x['item_id']]=x
active={k:v for k,v in packets.items() if k in fold and k not in superseded and fold[k]['decision']=='provenance_folded' and not fold[k].get('splits')}
# Independent presence census deliberately does not equate negative adjudication with absence.
def match(it,cid,comp,method,fi):
 return (it['case_id']==cid and it['composition']==comp and it['method_label']==labels[method] and it['rule']==fi['rule'] and {'element':fi.get('element'),'token':fi.get('token')} in [{'element':it.get('element'),'token':it.get('token')}]+it.get('also_covers',[]))
def verdict(it):
 recs=[]
 for role in ['ADJ1','ADJ2','ADJ3']:
  p=Path('adjudication')/roles[role]/(it['item_id']+'.json')
  recs.append(read(p) if (PB/p).exists() else None)
 a,b,c=recs
 def decide(get):
  x,y=get(a or {}),get(b or {})
  return x if x is not None and x==y else get(c or {}) if c else None
 op=decide(lambda r:r.get('operation_edge',{}).get('verdict'))
 vals={p:decide(lambda r:next((v['verdict'] for v in r.get('values',[]) if v['path']==p),None)) for p in it['evidence']['trigger_paths']}
 substance={p:decide(lambda r:next((v['verdict'] for v in r.get('substance',[]) if v['path']==p),None)) for p in it['evidence']['trigger_paths'] if p.startswith('ver_delta.changed_fields[')}
 return {'initial_records_present':bool(a and b),'operation_edge':op,'trigger_verdicts':vals,'substance_verdicts':substance}
rows=[]; populations=[]; pseudo=[]; counts=Counter(); score_ids=[]
for path in score_paths:
 r=read(path.relative_to(PB)); cid=r['case_id']
 assert cid == path.stem and cid not in score_ids
 if cid in pilot:
  raise ValueError('pilot score present in retained nonpilot primary cohort: ' + cid)
 spec=read(Path('specs')/(cid+'.json')); spec.update(overrides.get(cid,{}))
 assert spec['eligible']
 assert r['outcome_class']==spec['outcome_class']
 assert r['resolution_status']==spec.get('resolution',{}).get('status')
 assert r['c3_selected']==(cid in selected)
 score_ids.append(cid)
 scopes=[]
 if r['outcome_class']=='warning_only':scopes.append(('warning_only','broken'))
 if r.get('resolved') and r['resolution_status'] in ['observed','recommended']: scopes.append(('fixed_'+r['resolution_status'],'resolved'))
 for scope,comp in scopes:
  populations.append({'case_id':cid,'scope':scope,'corpus':r['corpus']})
  for method in labels:
   s=r[comp][method]
   if s['state']=='unassessable':
    assert not s.get('findings'); pseudo.append({'case_id':cid,'scope':scope,'method':method}); continue
   rejected=s['state'] in (['right_reason','unverified','wrong_reason'] if comp=='broken' else ['reject'])
   if not rejected:
    assert not s.get('findings');continue
   assert s.get('findings')
   for fi in s['findings']:
    hits=[k for k,v in active.items() if match(v,cid,comp,method,fi)]
    allhits=[k for k,v in packets.items() if match(v,cid,comp,method,fi)]
    rows.append({'case_id':cid,'scope':scope,'composition':comp,'method':method,'state':s['state'],'rule':fi['rule'],'element':fi.get('element'),'token':fi.get('token'),'active_fold_items':hits,'all_packet_matches':allhits})
if len(score_ids) != 126 or len(set(score_ids)) != 126:
 raise ValueError('expected all 126 distinct nonpilot primary score rows')
item_ids=sorted({i for r in rows for i in r['active_fold_items']})
by_scope={}
for scope in ['warning_only','fixed_observed','fixed_recommended']:
 rr=[r for r in rows if r['scope']==scope]; pp=[p for p in populations if p['scope']==scope]
 by_scope[scope]={'population_compositions':len(pp),'population_by_corpus':dict(Counter(p['corpus'] for p in pp)),'actual_rejected_case_method_compositions':len({(r['case_id'],r['method']) for r in rr}),'actual_rejected_cases':len({r['case_id'] for r in rr}),'findings':len(rr),'uncovered_findings':sum(not r['active_fold_items'] for r in rr),'unique_a2_items':len({i for r in rr for i in r['active_fold_items']}),'pseudo_case_method_alarms':sum(p['scope']==scope for p in pseudo)}
gaps=[r for r in rows if not r['active_fold_items']]
result={'scope':'Primary frozen scores only; all nonpilot scored eligible rows; warning controls are not selected C3 failure cases. Controls include observed and recommended fixed compositions separately.','score_rows':len(score_ids),'by_scope':by_scope,'total_actual_findings':len(rows),'total_uncovered_findings':len(gaps),'gaps':gaps,'items':rows,'active_item_decisions':{i:verdict(active[i]) for i in item_ids},'pseudo_alarms':pseudo,'input_sha256':inputs}

# Derived counts make explicit the distinction between finding presence,
# recorded adjudicator decisions, and independent source-validation credit.
decisions = result['active_item_decisions']
transcription_items = sorted(i for i, d in decisions.items()
                             if 'transcription_only' in d['substance_verdicts'].values())
result['coverage_summary'] = {
    'covered_findings': len(rows) - len(gaps),
    'uncovered_findings': len(gaps),
    'uncovered_cases': sorted({r['case_id'] for r in gaps}),
    'actual_rejected_cases': len({r['case_id'] for r in rows}),
    'actual_rejected_case_method_compositions': len({(r['case_id'], r['composition'], r['method']) for r in rows}),
    'unique_covering_a2_items': len(item_ids),
    'transcription_only_covering_items': transcription_items,
    'transcription_only_covering_item_count': len(transcription_items),
    'covering_items_with_initial_records': sum(d['initial_records_present'] for d in decisions.values()),
    'covering_items_with_agree_operation_edge': sum(d['operation_edge'] == 'agree' for d in decisions.values()),
    'covering_items_with_all_trigger_values_verified': sum(bool(d['trigger_verdicts']) and all(v == 'verified' for v in d['trigger_verdicts'].values()) for d in decisions.values()),
}
result['input_manifest_scope'] = 'SHA-256 of every data file actually read, relative to experiments/pathb_v2; not the entire package or a source-validation certificate.'
result['inventory'] = {
    'scores': [p.relative_to(PB).as_posix() for p in score_paths],
    'a2_packets': [p.relative_to(PB).as_posix() for p in packet_paths],
    'read_file_count': len(inputs),
}
print(json.dumps(result, indent=2))
