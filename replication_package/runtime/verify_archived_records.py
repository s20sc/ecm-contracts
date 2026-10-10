"""Validate archived bytes and reported summaries; does not execute ROS or Docker."""
from pathlib import Path
import hashlib,json,re,math,argparse
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
root=Path(__file__).resolve().parent
manifest=json.loads((root/'ARCHIVE_MANIFEST.json').read_text())
for rel,v in manifest['files'].items():
 data=(root/rel).read_bytes();assert len(data)==v['bytes'] and hashlib.sha256(data).hexdigest()==v['sha256'],rel
lines=(root/'qos_window_probe_run/probe.jsonl').read_text().splitlines()
assert lines[0]=='ROS_DISTRO=humble'
lines=lines[1:]
assert all(not s.strip() or s.startswith('{') for s in lines)
rows=[json.loads(s) for s in lines if s.strip() and not s.startswith('#')]
assert len(rows)==30
assert {(r['pair'],r['variant'],r['repeat']) for r in rows}=={(p,v,i) for p in ('matched','incompatible') for v in ('original','warmup','warmup_drain') for i in range(5)}
summary={}
for r in rows:
 expected=0 if r['pair']=='incompatible' else 80 if r['variant']=='warmup_drain' else 79
 missing=list(range(80)) if expected==0 else [] if expected==80 else [79]
 assert r['sent']==80 and r['received']==expected and r['missing_seq']==missing,r
 summary.setdefault(r['pair']+'/'+r['variant'],[]).append(r['received'])
log=(root/'repeats.log').read_text()
single=[float(x) for x in re.findall(r'SINGLE writer .*?: dx=([-\d.]+)m',log)]
two=[tuple(map(float,x)) for x in re.findall(r'TWO writers .*?: dx=([-\d.]+)m dyaw=([-\d.]+)rad',log)]
assert len(single)==len(two)==5
assert [round(min(single),2),round(max(single),2)]==[.37,.77]
assert [round(min(x[0] for x in two),2),round(max(x[0] for x in two),2)]==[.02,.08]
assert round(max(abs(x[1]) for x in two),1)==1.5
cm=(root/'ws4_res_conflict/cm.log').read_text()
assert "[ctrlA]: activate successful" in cm
assert "Resource conflict for controller 'ctrlB'. Command interface 'joint1/position' is already claimed." in cm
assert "Could not activate controller : 'ctrlB'" in cm
frame=(root/'ws4_res_conflict/frame_mismatch.log').read_text()
points=re.findall(r':\s*\(([-\d.]+), ([-\d.]+), ([-\d.]+)\)',frame)
assert len(points)==3,points
producer,correct,naive=[tuple(map(float,t)) for t in points]
assert producer==naive==(1.,0.,0.) and correct==(-.2,-.5,0.)
error=math.dist(correct,naive);assert math.isclose(error,1.3)
assert 'FRAME-MISMATCH ERROR = 1.300 m' in frame
out={'status':'archival_records_verified','runtime_rerun':False,'archived_files':len(manifest['files']),'qos_rows':len(rows),'qos_received':summary,'single_writer_dx':single,'two_writer_dx_dyaw':two,'controller_conflict_verified':True,'frame_error_m':error,'scope':'Existing captured outputs checked offline. Not independent live replication, not evidence of unknown-failure detection; no corpus scores changed.'}
Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
