"""Read-only post-outcome sensitivity. Does not edit or reselect frozen records."""
import sys,json,hashlib,copy,argparse
from pathlib import Path
if not __debug__:
    raise RuntimeError('Run without Python optimization: input consistency guards must remain enabled.')
parser=argparse.ArgumentParser(description="Reaggregate archived primary scores under a post-outcome same-source boundary alternative; never edits inputs.")
parser.add_argument('--package', type=Path, required=True, help='Path to the complete replication_package')
args=parser.parse_args()
PACKAGE=args.package.resolve(strict=True)
PB=PACKAGE/'experiments/pathb_v2'
if not (PB/'scoring.py').is_file():
    parser.error('Package must contain experiments/pathb_v2/scoring.py')
sys.dont_write_bytecode=True
# Record the package files actually opened by this invocation, including imported
# implementation, raw specifications, selection ledgers and active overrides.
opened=set()
def record_open(event, args):
    if event!='open' or not isinstance(args[0],(str,bytes)):
        return
    try:
        path=Path(args[0]).resolve()
        path.relative_to(PACKAGE)
    except (ValueError,TypeError,OSError):
        return
    opened.add(path)
sys.addaudithook(record_open)
sys.path.insert(0,str(PB))
import scoring as S
import supplementary_binary_metrics as B
read=lambda p:json.loads(p.read_text())
specs=S.load_specs(True)
selection=S.c3_selection(S.load_specs(False))
pilot=set(read(PB/'pilot/PILOT_CASES.json')['quarantined_pilot_cases'])
paths=sorted((PB/'scores_adjudicated').glob('*.json'))
rows,_=B.select_rows([read(p) for p in paths],specs,pilot,selection)
assert S.by_corpus(rows)==read(PB/'results_adjudicated.json')['by_corpus']
assert not specs['C3N-001']['eligible']
assert specs['C3-057']['eligible']
assert next(r for r in rows if r['case_id']=='C3-057')['assembled_status']=='unassessable'
alt=[r for r in rows if r['case_id']!='C3-057']
alt_specs=copy.deepcopy(specs);alt_specs['C3-057']['eligible']=False

def summary(rr,ss):
 funnel={}
 for c in B.CORPORA:
  s=[s for s in ss.values() if s['corpus']==c]
  eligible=[x for x in s if x.get('eligible')]
  failure=[x for x in eligible if x['outcome_class']=='failure']
  funnel[c]={'specified':len(s),'eligible':len(eligible),'documented_failures':len(failure),'failure_fraction':S.rate(len(failure),len(s))}
 strata={}
 for field in ['ros_generation','excerpt_based','unpinned','single_composition','adjudication_changed','built_against_basis','s1_model','same_repository','operation','loudness','detection_stage']:
  strata[field]={v:S.by_corpus([r for r in rr if str(r[field])==v]) for v in sorted({str(r[field]) for r in rr})}
 return {'funnel':funnel,'H1':S.h1_record(rr),'by_corpus':S.by_corpus(rr),'binary':B.calculate(rr),'strata':strata,'row_ids':[r['case_id'] for r in rr]}
before=summary(rows,specs);after=summary(alt,alt_specs)
assert after['H1']['n_eligible_failures']==39
assert after['H1']['b_ecm_only']==2 and after['H1']['c_dq_only']==0 and after['H1']['mcnemar_exact_two_sided_p']==.5
for c in B.CORPORA:
 if c!='C3':assert before['by_corpus'][c]==after['by_corpus'][c]
 assert before['binary'][c]['methods']==after['binary'][c]['methods']
 assert before['binary'][c]['observations']==after['binary'][c]['observations']
assert before['by_corpus']['C3']['complete_case']==after['by_corpus']['C3']['complete_case']
# Direct independent count guards for the focal population.
for rr,nn in [(rows,40),(alt,39)]:
 fails=[r for r in rr if r['corpus']=='C3' and r['outcome_class']=='failure']
 assert len(fails)==nn
 assert sum(r['broken']['ECM']['state']=='right_reason' for r in fails)==3
 assert sum(r['assembled_status']=='done' for r in fails)==30

def diff(a,b,path=''):
 if isinstance(a,dict) and isinstance(b,dict):
  return [d for k in sorted(set(a)|set(b)) for d in diff(a.get(k),b.get(k),path+'/'+k)]
 return [] if a==b else [{'path':path,'before':a,'after':b}]
result={'status':'post-outcome alternative boundary, not replacement primary analysis',
 'rule':'Treat issue5386/PR6336 as internal controller behavior under truthful odometry in BOTH retrieval frames. Exclude C3-057; C3N-001 remains excluded.',
 'limitations':['Source interpretation remains model-conditional; no new human reference.','No replacements, no resampling, no C3N-001 score invented.','Does not resolve other disputed exclusions or complete expanded-boundary sensitivity.'],
 'primary':before,'alternative':after,'differences':diff(before,after),
 'inputs':[{'path':str(p.relative_to(PB)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths+[PB/'specs/C3-057.json',PB/'specs/C3N-001.json',PB/'adjudicated/overrides.json',PB/'results_adjudicated.json']],
 'binary_complete_cases_unchanged':True,'c3_complete_case_aggregates_unchanged':True}
# The calculation is identical to the adjudicated preview; the dependency
# receipt now covers all files actually read, not only the focal specifications.
result['inputs']=[{'path':str(p.relative_to(PACKAGE)),
                   'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                  for p in sorted(opened) if p.is_file()]
print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
