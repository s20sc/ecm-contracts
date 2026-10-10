"""Prospective fold regressions; only temporary synthetic records are written."""
import contextlib,copy,importlib.util,io,json,os,tempfile,unittest
from pathlib import Path
SOURCE=Path(os.environ.get('P5_FOLD_SOURCE',str(Path(__file__).with_name('adjudicate.py'))))
DOMAINS={'eligibility':('reason_code','E2','E3','E4'), 'loudness':('proposed','silent_documented','loud','unknown'), 'resolution':('proposed','observed','recommended','unknown'), 'class':('proposed_class','frame_mismatch','unit_mismatch','other'), 'elements':('proposed_elements',['topic:/a'],['topic:/b'],['topic:/c'])}
def record():
 return {'item_id':'A1-case','kind':'A1','case_id':'case','eligibility':{'verdict':'agree','stop_step':6,'reason_code':None},'loudness':{'verdict':'agree','proposed':None},'resolution':{'verdict':'agree','proposed':None},'failed_conditions':[{'index':0,'class_verdict':'agree','proposed_class':None,'elements_verdict':'agree','proposed_elements':[]}],'missed_conditions':[]}
def domain_part(row,domain):
 return row['failed_conditions'][0] if domain in ('class','elements') else row[domain]
def change(row,domain,value,verdict='disagree'):
 part=domain_part(row,domain);part[domain+'_verdict' if domain in ('class','elements') else 'verdict']=verdict
 part[DOMAINS[domain][0]]=value
 if domain=='eligibility' and verdict=='disagree':part['stop_step']=1
 return row
def run(a,b,c=None,adj1_only=False,eligible=True):
 spec=importlib.util.spec_from_file_location('prospective_fold',SOURCE);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 with tempfile.TemporaryDirectory(prefix='p5-fold-regression-') as temp:
  root=Path(temp);module.HERE=str(root);module.ADJ=str(root/'adjudication');module.OUT=str(root/'adjudicated')
  (root/'specs').mkdir();(root/'specs/case.json').write_text(json.dumps({'eligible':eligible,'loudness':'original','resolution':{'status':'original'},'failed_conditions':[{'class':'original','implicated_elements':['topic:/original']}]}))
  for who,row in [('adj1',a),('withdrawn_google',b),('adj1_repeat',c)]:
   if row is not None:
    folder=root/'adjudication'/who;folder.mkdir(parents=True);(folder/'A1-case.json').write_text(json.dumps(row))
  with contextlib.redirect_stdout(io.StringIO()):module.fold(adj1_only=adj1_only)
  out=root/('adjudicated_adj1only' if adj1_only else 'adjudicated')
  return {name:json.loads((out/(name+'.json')).read_text()) for name in ['overrides','splits','fold_log']}
def selected(result,domain):
 ov=result['overrides'].get('case',{})
 if domain=='eligibility':return ov.get('ineligible_reason')
 if domain=='class':return ov.get('failed_conditions',[{}])[0].get('class')
 if domain=='elements':return ov.get('failed_conditions',[{}])[0].get('implicated_elements')
 if domain=='resolution':return ov.get('resolution',{}).get('status')
 return ov.get(domain)
class ProposalConflicts(unittest.TestCase):
 def test_both_disagree_conflicts_stay_pending_in_either_order(self):
  for domain,(_,first,second,_) in DOMAINS.items():
   for x,y in [(first,second),(second,first)]:
    with self.subTest(domain=domain,first=x):
     result=run(change(record(),domain,x),change(record(),domain,y))
     self.assertEqual(result['splits'],[{'item':'A1-case','domain':domain,'detail':0 if domain in ('class','elements') else None}])
     self.assertEqual(result['overrides'],{})
 def test_third_own_replacement_decides_conflict(self):
  for domain,(_,first,second,third) in DOMAINS.items():
   with self.subTest(domain=domain):
    result=run(change(record(),domain,first),change(record(),domain,second),change(record(),domain,third))
    self.assertEqual(result['splits'],[]);self.assertEqual(selected(result,domain),third)
 def test_third_own_replacement_decides_verdict_split(self):
  for domain,(_,first,_,third) in DOMAINS.items():
   with self.subTest(domain=domain):
    result=run(change(record(),domain,first),record(),change(record(),domain,third))
    self.assertEqual(result['splits'],[]);self.assertEqual(selected(result,domain),third)
 def test_third_confirmation_retains_original(self):
  for domain,(_,first,second,_) in DOMAINS.items():
   with self.subTest(domain=domain):
    result=run(change(record(),domain,first),change(record(),domain,second),record())
    self.assertEqual(result['splits'],[]);self.assertEqual(result['overrides'],{})
 def test_unanswered_third_domain_stays_pending(self):
  for domain,(_,first,second,_) in DOMAINS.items():
   with self.subTest(domain=domain):
    c=record()
    if domain in ('class','elements'):c['failed_conditions']=[]
    else:c.pop(domain)
    result=run(change(record(),domain,first),change(record(),domain,second),c)
    self.assertEqual(len(result['splits']),1);self.assertEqual(result['overrides'],{})
 def test_equal_proposals_and_adj1_sensitivity_retained(self):
  for domain,(_,first,second,_) in DOMAINS.items():
   with self.subTest(domain=domain):
    for result in [run(change(record(),domain,first),change(record(),domain,first)),run(change(record(),domain,first),change(record(),domain,second),adj1_only=True)]:
     self.assertEqual(result['splits'],[]);self.assertEqual(selected(result,domain),first)
 def test_element_order_is_not_disagreement(self):
  result=run(change(record(),'elements',['topic:/a','topic:/b']),change(record(),'elements',['topic:/b','topic:/a']))
  self.assertEqual(result['splits'],[]);self.assertEqual(set(selected(result,'elements')),{'topic:/a','topic:/b'})
 def test_third_disagree_without_replacement_stays_pending(self):
  for domain in ['class','elements','loudness','resolution']:
   _,first,second,_=DOMAINS[domain]
   with self.subTest(domain=domain):
    result=run(change(record(),domain,first),change(record(),domain,second),change(record(),domain,None))
    self.assertEqual(len(result['splits']),1);self.assertEqual(result['overrides'],{})
 def test_both_disagree_missing_replacements_stay_pending(self):
  for domain in ['class','elements','loudness','resolution']:
   with self.subTest(domain=domain):
    result=run(change(record(),domain,None),change(record(),domain,None))
    self.assertEqual(len(result['splits']),1);self.assertEqual(result['overrides'],{})
 def test_eligibility_different_stop_steps_are_not_consensus(self):
  a=change(record(),'eligibility',None);b=copy.deepcopy(a);b['eligibility']['stop_step']=2
  result=run(a,b);self.assertEqual(len(result['splits']),1);self.assertEqual(result['overrides'],{})
 def test_eligibility_missing_stop_step_is_pending(self):
  a=change(record(),'eligibility',None);a['eligibility'].pop('stop_step')
  result=run(a,copy.deepcopy(a));self.assertEqual(len(result['splits']),1);self.assertEqual(result['overrides'],{})
 def test_step_one_null_reason_is_a_valid_historical_decision(self):
  a=change(record(),'eligibility',None);a['eligibility']['reason']='No two independently released units.'
  result=run(a,copy.deepcopy(a));self.assertEqual(result['splits'],[])
  self.assertEqual(result['overrides'],{'case':{'eligible':False,'ineligible_reason':None}})
 def test_reinclusion_with_step_six_and_null_reason_is_valid(self):
  a=change(record(),'eligibility',None);a['eligibility']['stop_step']=6
  result=run(a,copy.deepcopy(a),eligible=False)
  self.assertEqual(result['splits'],[]);self.assertEqual(result['overrides'],{'case':{'eligible':True,'ineligible_reason':None}})
if __name__=='__main__':unittest.main()
