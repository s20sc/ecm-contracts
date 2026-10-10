from pathlib import Path
import json,hashlib,sys,ast,re,math,datetime,collections
ROOT=Path('/historical/project');B=ROOT/'V32-EMSE/replication_package/experiments/pathb_v2';O=Path('/historical/runs/p5-v39-review-R1/mechanism-ledger');sys.dont_write_bytecode=True;sys.path.insert(0,str(B));import adjudication_guard as AG
HASHES={}
def source(p,ptr='$'):
 p=Path(p);h=hashlib.sha256(p.read_bytes()).hexdigest();HASHES[str(p)]=h;return {'path':str(p),'sha256':h,'pointer':ptr}
def read(p):source(p);return json.loads(Path(p).read_text())
sc=B/'scoring.py';tree=ast.parse(sc.read_text());source(sc)
PLANNED_N=next(ast.literal_eval(x.value) for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='C3_PLANNED_N' for t in x.targets))
MATCH_NODE=next(x for x in tree.body if isinstance(x,ast.AnnAssign) and isinstance(x.target,ast.Name) and x.target.id=='MATCH')
MATCH=ast.literal_eval(MATCH_NODE.value)
def match_source(class_name: str) -> dict:
 return {k:v for k,v in {**source(sc),'lines':[MATCH_NODE.lineno,MATCH_NODE.end_lineno],'syntax_pointer':'MATCH['+class_name+']'}.items() if k!='pointer'}
code={'field_break':{'dimension':'Ver','function':'_ver','lines':[165,176]},'type_mismatch':{'dimension':'Sig','function':'_sig','lines':None}}
ck=B.parent/'pathb/checker/contract_checker.py';ctree=ast.parse(ck.read_text());source(ck)
for x in ctree.body:
 if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name in {'_ver','_sig'}:
  for k,z in code.items():
   if z['function']==x.name:z['implementation_source']={**source(ck),'lines':[x.lineno,x.end_lineno]}
roles=read(B/'ledger/adjudicators.json');labels=read(B/'ledger/method_labels.json');tasks=read(B/'ledger/tasks.json')['tasks'];pilot=set(read(B/'pilot/PILOT_CASES.json')['quarantined_pilot_cases'])
# Capture the exact JSON bytes read by the existing coverage loader, including
# active role records not subsequently selected by an ECM credit mechanism.
GUARD_READS={}
original_read_text=Path.read_text
def guard_read_text(path: Path, *args, **kwargs) -> str:
 if args or kwargs:raise ValueError('Unexpected read_text options in guard loader')
 data=path.read_bytes();h=hashlib.sha256(data).hexdigest();HASHES[str(path)]=h;GUARD_READS[str(path)]=h
 return data.decode('utf-8')
Path.read_text=guard_read_text
try:cov=AG.load_coverage(B)
finally:Path.read_text=original_read_text
fold=read(B/'adjudicated/fold_log.json');fold_by_item={x['item']:(i,x) for i,x in enumerate(fold)}
assert not read(B/'adjudicated/overrides.json'),'Nonempty overrides require explicit support'
source(B/'adjudication_guard.py');source(B/'adjudicated/fold_log.json');source(B/'ledger/a2_r3_supersedes.json');source(B/'adjudicated/provenance_verdicts.json');source(B/'adjudicated/overrides.json')
packets={}
for p in sorted((B/'adjudication/packets').glob('A2_*.json')):
 for i,item in enumerate(read(p)):
  packets[item['item_id']]={'data':item,'source':source(p,f'$[{i}]')}
rows={p.stem:read(p) for p in sorted((B/'scores_adjudicated').glob('*.json'))};specs={p.stem:read(p) for p in sorted((B/'specs').glob('*.json'))}
# Independent explicit reconstruction of C3 frozen walk (no scorer or aggregate execution).
order=read(B/'candidates/C3_order.json');hits=read(B/'candidates/C3_ledger.json')['hits'];selected=[];perrepo=collections.Counter();walk=[]
for i,url in enumerate(order['ordered']):
 cid=f'C3-{i+1:03d}';repo=hits[url]['repo'];sp=specs.get(cid);reason='not_eligible_failure'
 if perrepo[repo]>=order['per_repo_cap']:reason='repo_cap'
 elif sp is None:reason='missing_spec';walk.append({'index':i,'case_id':cid,'url':url,'reason':reason});break
 elif sp.get('eligible') and sp.get('outcome_class')=='failure':selected.append(cid);perrepo[repo]+=1;reason='selected'
 walk.append({'index':i,'case_id':cid,'url':url,'reason':reason})
 if len(selected)==PLANNED_N:break
frows={k:r for k,r in rows.items() if r['outcome_class']=='failure' and (r['corpus']!='C3' or k in selected)}
issues=[];cases=[];credits=[]
# Trigger paths reproduced from exact frozen mapping for only the two empirically credited rules.
def paths(rule,token):return [f'ver_delta.changed_fields[{token}]',f'ver_delta.consumer_reads[{token}]'] if rule=='field_break' else ['producer.outputs[0].msg_type','consumer.inputs[0].msg_type']
def rawsource_refs(text: str,unit: dict,trigger_path: str | None=None) -> list:
 refs=[]
 for m in re.finditer(r'(?:snapshot:)?(?:s2_work/tasks/(u\d+)/snapshot/)?([\w./+@-]+\.[A-Za-z0-9]+):(\d+)(?:-(\d+))?',text):
  tid,path,start,end=m.groups();line_start=int(start);line_end=int(end or start);path=path.removeprefix('snapshot:');taskmap=unit.get('tasks') or {}
  if tid: tids=[tid];resolution='EXPLICIT_TASK_POINTER'
  else:
   preceding=text[:m.start()];named=list(re.finditer(r'\b(built|running):',preceding));role=named[-1].group(1) if named else ('producer' if (trigger_path or '').startswith('producer.') else 'consumer' if (trigger_path or '').startswith(('consumer.','ver_delta.consumer_reads')) else None)
   if role and role in taskmap:tids=[taskmap[role]];resolution='TASK_ROLE_FROM_ASSEMBLED_TRIGGER'
   else:tids=list(dict.fromkeys(taskmap.values()));resolution='AMBIGUOUS_TASK_CANDIDATES_UNVERIFIED'
  for task in tids:
   if not task:continue
   known=tasks.get(task,{});candidates=[B/'s2_work/tasks'/task/'snapshot'/path,ROOT/'experiments/pathb_v2/s2_work/tasks'/task/'snapshot'/path,ROOT/'V32-EMSE/replication_package/posthoc_review_v28/source-extracts'/task/path]
   if path=='artifact.txt':candidates=[B/'s2_work/tasks'/task/path,ROOT/'experiments/pathb_v2/s2_work/tasks'/task/path]+candidates
   existing=[p for p in candidates if p.is_file()] if resolution!='AMBIGUOUS_TASK_CANDIDATES_UNVERIFIED' else []
   z={'task_id':task,'task_resolution':resolution,'source_relative_path':path,'line':line_start,'line_start':line_start,'line_end':line_end,'reported_pointer':m.group(0),'task_record_source':source(B/'ledger/tasks.json',f'$.tasks.{task}'),'repo':known.get('repo'),'revision':known.get('revision'),'resolved_commit':known.get('resolved_commit'),'snapshot_tree_sha256_declared':known.get('snapshot_sha256'),'original_file_verified_this_task':False,'original_file_verified_this_task_scope':'Compatibility alias of source_line_range_read; not literal trigger truth verification','original_file_bytes_read':False,'source_line_range_read':False,'trigger_value_literal_verified':False,'trigger_value_literal_verification':'NOT_PERFORMED; source bytes/range reading does not validate field-specific trigger semantics','snapshot_tree_pin_recomputed':False}
   if existing:
    p=existing[0];ss=p.read_text(errors='replace').splitlines();valid=0<line_start<=line_end<=len(ss);z.update(original_file_verified_this_task=valid,original_file_bytes_read=True,source_line_range_read=valid,local_original_file=source(p),line_excerpt='\n'.join(ss[line_start-1:line_end]) if valid else None,line_excerpts=[{'line':i+1,'text':ss[i]} for i in range(line_start-1,line_end)] if valid else [],verification='LOCAL_FILE_BYTES_AND_COMPLETE_LINE_RANGE_READ; literal trigger semantics and complete snapshot tree/revision authentication not verified' if valid else 'UNVERIFIED_LINE_RANGE_OUT_OF_RANGE')
   else:z['verification']='UNVERIFIED_ORIGINAL_FILE_NOT_MATERIALIZED_AT_KNOWN_PATHS; exact reported pointer retained'
   refs.append(z)
 return refs
for cid,r in frows.items():
 sp=specs[cid];assert sp['eligible'] and cid not in pilot,(cid,'selection');assert r['corpus']!='C3' or r['c3_selected'],cid
 p=B/'assembled'/f'{cid}.json';assembled=read(p) if p.exists() else None;comp=assembled['compositions']['broken'] if assembled else None;conds=sp.get('failed_conditions',[])
 item={'case_id':cid,'corpus':r['corpus'],'operation':r['operation'],'outcome_label':'model-written documented failure','human_reference':False,'score_source':source(B/'scores_adjudicated'/f'{cid}.json'),'spec_source':source(B/'specs'/f'{cid}.json'),'failed_conditions':[{'class':c['class'],'implicated_elements':c.get('implicated_elements'), 'reported_quote':c.get('quote'),'reported_url':c.get('url'),'spec_pointer':f'$.failed_conditions[{i}]','original_reference_truth':'NOT_INDEPENDENT_HUMAN_VALIDATED'} for i,c in enumerate(conds)],'assembled_source':source(p) if p.exists() else None,'assembly_status':r['assembled_status'],'assembly_reason':r.get('assembled_reason'),'method_states':{m:x['state'] for m,x in r['broken'].items()},'method_score_pointers':{m:f'$.broken.{m}.state' for m in r['broken']},'ECM_credit':r['broken']['ECM']['state']=='right_reason','MATCH_applicable_rules':[{'class':c['class'],'method':m,'rule':rule,'match_kind':how} for c in conds for m,rule,how in MATCH.get(c['class'],[])],'ECM_matches':r['broken']['ECM'].get('matched',[]),'credit_mechanisms':[]}
 if item['ECM_credit']:
  for mi,match in enumerate(r['broken']['ECM'].get('matched',[])):
   rule,token=match['rule'],match.get('token');rule_findings=[(fi,f) for fi,f in enumerate(r['broken']['ECM']['findings']) if f['rule']==rule and f.get('token')==token and f.get('element')==match.get('element') and f['provenance']=='verified'];assert rule_findings,(cid,match)
   fi,f=rule_findings[0];pp=paths(rule,token);mechanism={'match':match,'MATCH_rule':MATCH[match['class']],'MATCH_source':match_source(match['class']),'score_matched_pointer':f'$.broken.ECM.matched[{mi}]','score_finding_pointer':f'$.broken.ECM.findings[{fi}]','stored_finding':f,'implementation':code.get(rule),'trigger_paths':pp,'assembled_trigger_candidates':[],'A2_active_covering_items':[],'source_provenance_scope':'Stored model source-adjudication; not independent human truth.'}
   for ui,u in enumerate(comp['units']):
    if u.get('status')!='done' or u['kind']!=f['unit_kind']:continue
    if rule=='field_break' and token not in (u['encoding'].get('ver_delta',{}).get('changed_fields') or []):continue
    if rule=='type_mismatch' and u.get('element')!=match.get('element'):continue
    entries=cov.get(cid,{}).get('broken',[]);covered=[e for e in entries if AG.finding_covered([e],'ECM',f,u,pp)]
    if not covered:continue
    trigger={'assembled_pointer':f'$.compositions.broken.units[{ui}]','unit_kind':u['kind'],'element':u.get('element'),'tasks':u.get('tasks'),'encoding':u['encoding'],'values':[],'active_A2_items':[e['item_id'] for e in covered]}
    for q in pp:
     value=AG.trigger_value(u['encoding'],q);prov=u['provenance'].get(q);trigger['values'].append({'path':q,'assembled_value':value,'assembled_source_provenance':prov,'source_refs':rawsource_refs(prov or '',u,q)})
    mechanism['assembled_trigger_candidates'].append(trigger)
    for e in covered:
     pack=packets[e['item_id']];fold_i,fold_record=fold_by_item[e['item_id']];ae={'item_id':e['item_id'],'packet_source':pack['source'],'active_fold_source':{**source(B/'adjudicated/fold_log.json',f'$[{fold_i}]'),'record':fold_record},'operation_edge_fold':e['operation_edge'],'value_verdict_fold':e['values'],'current_trigger_exactly_covered_by_guard':True,'model_records':[]}
     for role in ['ADJ1','ADJ2','ADJ3']:
      recp=B/'adjudication'/roles[role]/f"{e['item_id']}.json"
      if not recp.exists():continue
      rec=read(recp);ae['model_records'].append({'role':role,'source':source(recp),'operation_edge':rec.get('operation_edge'),'values':[{'path':v['path'],'verdict':v.get('verdict'),'source_excerpt':v.get('source_excerpt'),'record_pointer':f'$.values[{vi}]','source_refs':rawsource_refs(v.get('source_excerpt',''),u,v['path'])} for vi,v in enumerate(rec.get('values',[])) if v['path'] in pp],'substance':rec.get('substance')})
     mechanism['A2_active_covering_items'].append(ae)
   if not mechanism['assembled_trigger_candidates']:issues.append({'case_id':cid,'match':match,'status':'UNVERIFIED_CURRENT_ASSEMBLY_A2_MATCH_NOT_FOUND'})
   if rule=='field_break':mechanism['consumer_restriction']={'matched_token_in_changed_fields_and_consumer_reads':True,'removing_consumer_intersection_preserves_this_existing_trigger':bool(mechanism['assembled_trigger_candidates']),'score_recomputed_under_ablation':False,'interpretation':'Structural survival of already-credited field_break. Does not establish additional benefit or unchanged control specificity.'}
   else:mechanism['consumer_restriction']={'applicable':False,'interpretation':'Nominal type rule is not consumer-restricted version rule.'}
   item['credit_mechanisms'].append(mechanism)
  artifact_paths=[(t,v) for m in item['credit_mechanisms'] for t in m['assembled_trigger_candidates'] for v in t['values'] if 'artifact.txt:' in (v.get('assembled_source_provenance') or '')]
  item['platform_failure_record_credit']=bool(artifact_paths) and cid in {'B-Ver-05','B-Sig-02'}
  item['platform_credit_evidence']=[{'trigger_path':v['path'],'task_ids':t['tasks'],'reported_artifact_pointer':v['assembled_source_provenance'],'source_refs':v['source_refs']} for t,v in artifact_paths]
  item['withheld_analysis_credit']=not item['platform_failure_record_credit'];item['platform_record_evidence_basis']='Trigger provenance/excerpt-based task records and platform-type/MD5 quoted failure source; withholding is analysis label, not source-value deletion.' if item['platform_failure_record_credit'] else 'Code/definition source provenance; direct raw-file availability separately marked.'
  credits.append(item)
 cases.append(item)
# All 93 individual rows supply independent arithmetic footprints, not expected aggregate output.
per=collections.Counter(r['corpus'] for r in frows.values());creditper=collections.Counter(x['corpus'] for x in credits);ops=collections.Counter(x['operation'] for x in credits);dims=collections.Counter({d:sum(any(m['implementation'] and m['implementation']['dimension']==d for m in x['credit_mechanisms']) for x in credits) for d in ['Sig','Beh','Res','Perm','Rec','Ver']})
hcases=[x for x in cases if x['corpus']=='C3'];E={x['case_id'] for x in hcases if x['method_states']['ECM']=='right_reason'};D={x['case_id'] for x in hcases if x['method_states']['DQ']=='right_reason'};bb,cc=len(E-D),len(D-E);n=bb+cc;pval=min(1.,2*sum(math.comb(n,i) for i in range(min(bb,cc)+1))/(2**n)) if n else 1.
summary={'primary_failures':len(cases),'by_corpus_failures':dict(per),'ECM_cause_credits':len(credits),'by_corpus_ECM_credits':dict(creditper),'credit_operations':dict(ops),'credit_dimensions':dict(dims),'platform_record_credit_cases':[x['case_id'] for x in credits if x['platform_failure_record_credit']],'withheld_credit_cases':[x['case_id'] for x in credits if x['withheld_analysis_credit']],'withheld_credits':sum(x['withheld_analysis_credit'] for x in credits),'H1':{'n':len(hcases),'ECM_cases':sorted(E),'DQ_cases':sorted(D),'ECM_only':sorted(E-D),'DQ_only':sorted(D-E),'both':sorted(E&D),'neither':sorted({x['case_id'] for x in hcases}-E-D),'b':bb,'c':cc,'exact_two_sided_p':pval,'method':'Independent exact binomial sum on per-case discordances; no scorer aggregate loaded.','DQ_credit_trace':[{'case_id':cid,'scope':'PARTIAL_STORED_SCORE_ONLY','definition_trigger_A2_source_chain_complete':False,'source_literal_trigger_validation_performed':False,'limitation':'Stored DQ finding/matched footprint only; di_definition_mismatch implementation, pair_view definition_id trigger and exact active A2/source chain are not reconstructed by this generator.','score_source':source(B/'scores_adjudicated'/f'{cid}.json','$.broken.DQ'),'stored_DQ_findings':rows[cid]['broken']['DQ'].get('findings'),'stored_DQ_matched':rows[cid]['broken']['DQ'].get('matched')} for cid in sorted(D)]},'A2_mechanisms_with_no_exact_coverage':issues,'human_reference':False,'consumer_credit_survival':'13 version existing triggers structurally survive consumer restriction removal; ablation not re-executed here.','confidence_scope':'No accuracy against independent labels or deployment prevalence inferred.'}
ledger={'schema':'V39_primary_case_mechanism_ledger_v1','generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'active_scope':str(B),'source_policy':'Read-only current V32 activity. Inventory pins explicitly read data/source files and every JSON input actually consumed by AG.load_coverage from captured bytes. All listed hashes must match; this is not a full transitive Python import/runtime seal or whole snapshot-tree authentication. Scores/specs/A2 remain model-authored reconstructions. Source bytes and complete line-range reads are separate from field-specific literal trigger validation, which is not performed. Absent/ambiguous sources remain UNVERIFIED. Full mechanisms cover the two credited ECM rules; DQ is explicitly a partial stored-score footprint.','guard_read_inventory':{'capture_method':'Temporarily scoped Path.read_text reader during AG.load_coverage; hash and decoded JSON derive from the same captured bytes; original reader restored in finally.','paths_sha256':GUARD_READS,'role_record_paths':[p for p in GUARD_READS if '/adjudication/' in p and '/packets/' not in p],'all_guard_JSON_reads_pinned':all(HASHES.get(p)==h for p,h in GUARD_READS.items())},'summary':summary,'independent_C3_selection':{'source':source(B/'candidates/C3_order.json'),'ledger_source':source(B/'candidates/C3_ledger.json'),'selected':selected,'walk':walk,'matches_stored_selected_flags':set(selected)=={cid for cid,r in rows.items() if r.get('c3_selected')}},'cases':cases,'human_reference_and_compatible_controls_still_open':True,'no_accept_verdict':True,'no_source_or_score_writes':True,'no_tests_or_full_reproduction':True}
(O/'mechanism-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2));(O/'source-sha256.json').write_text(json.dumps(HASHES,indent=2));(O/'credit-case-index.json').write_text(json.dumps({'summary':summary,'credit_cases':[{'case_id':x['case_id'],'corpus':x['corpus'],'operation':x['operation'],'failed_conditions':x['failed_conditions'],'platform_failure_record_credit':x['platform_failure_record_credit'],'withheld_analysis_credit':x['withheld_analysis_credit'],'ledger_pointer':f'$.cases[{cases.index(x)}]','matched_rules':[m['match'] for m in x['credit_mechanisms']]} for x in credits]},ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2));print('source_files',len(HASHES),'ledger_bytes',(O/'mechanism-ledger.json').stat().st_size)
