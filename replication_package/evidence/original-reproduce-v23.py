"""Offline deterministic reproduction from archived research records; Python >=3.10."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
PY = sys.executable

def copy_private_tree(source, destination):
    """Copy bytes and internal relative links, never permissions or file flags.

    Review inputs may be read-only and immutable. Each output inode is new,
    with owner-only writable permissions; no copystat/copy2 metadata is used.
    """
    source = Path(source).resolve()
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    def copy_dir(src, dst):
        dst.mkdir(mode=0o700)
        dst.chmod(0o700)
        for item in sorted(src.iterdir()):
            target = dst / item.name
            mode = item.lstat().st_mode
            if stat.S_ISLNK(mode):
                link = os.readlink(item)
                if Path(link).is_absolute() or not (item.parent / link).resolve().is_relative_to(source):
                    raise ValueError('Non-local symbolic link: ' + str(item))
                target.symlink_to(link)
            elif stat.S_ISDIR(mode):
                copy_dir(item, target)
            elif stat.S_ISREG(mode):
                with item.open('rb') as reader, target.open('xb') as writer:
                    shutil.copyfileobj(reader, writer)
                target.chmod(0o600)
            else:
                raise ValueError('Unsupported file type: ' + str(item))
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy_dir(source, destination)

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def sha_dir(path):
    # Exact original materialize.py algorithm, including symbolic-link strings.
    h=hashlib.sha256()
    for root, dirs, files in sorted(os.walk(path)):
        dirs.sort()
        for fn in sorted(files+[d for d in dirs if os.path.islink(os.path.join(root,d))]):
            p=Path(root)/fn;h.update(os.path.relpath(p,path).encode())
            h.update(b'L'+os.readlink(p).encode() if p.is_symlink() else p.read_bytes())
    return h.hexdigest()

def differences(a,b,path=''):
    if type(a)!=type(b): return [[path,a,b]]
    if isinstance(a,dict):
        out=[]
        for k in sorted(a.keys()|b.keys()):
            if k not in a or k not in b:
                out.append([path+'/'+k, {'present': k in a, 'value': a.get(k)},
                            {'present': k in b, 'value': b.get(k)}])
            else:
                out.extend(differences(a[k],b[k],path+'/'+k))
        return out
    if isinstance(a,list):
        if len(a)!=len(b): return [[path,a,b]]
        return [d for i,(x,y) in enumerate(zip(a,b)) for d in differences(x,y,path+'/'+str(i))]
    return [] if a==b else [[path,a,b]]

def verify_report_outputs(expected_pb, actual_pb):
    """Compare regenerated reports, including source hashes and snapshot inventory."""
    reports = {}
    for name in ('numbers.json', 'binary_metrics.json'):
        expected = json.loads((expected_pb / 'report' / name).read_text())
        actual = json.loads((actual_pb / 'report' / name).read_text())
        equal = not differences(expected, actual)
        reports[name] = {'exact_semantic_match': equal}
        if not equal:
            raise RuntimeError('Generated report differs from package reference: ' + name)
    source_hashes = json.loads((actual_pb / 'report/binary_metrics.json').read_text())['source_sha256']
    if not source_hashes:
        raise RuntimeError('Binary report has no source hashes')
    for name, expected_hash in source_hashes.items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise RuntimeError('Non-local binary report source: ' + name)
        source = actual_pb / relative
        if not source.is_file() or digest(source) != expected_hash:
            raise RuntimeError('Binary report source hash mismatch: ' + name)
    reports['binary_metrics.json']['source_hashes_verified'] = len(source_hashes)
    return reports

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=ROOT/'reproduced')
    args=ap.parse_args();out=args.out.resolve()
    if out.exists(): raise SystemExit('Output exists; choose a new --out directory to preserve earlier results.')
    manifest=json.loads((ROOT/'PACKAGE_MANIFEST.json').read_text())
    for name,expected in manifest['files'].items():
        if digest(ROOT/name)!=expected: raise SystemExit('Package hash mismatch: '+name)
    out.mkdir(parents=True)
    work=out/'work'; copy_private_tree(ROOT/'experiments',work/'experiments')
    pb=work/'experiments/pathb_v2';snapshots=json.loads((ROOT/'snapshots.json').read_text())
    blobs=out/'snapshot-blobs';blobs.mkdir(); expanded=0
    with zipfile.ZipFile(ROOT/'snapshots.zip') as z:
        for tid,record in snapshots.items():
            base=pb/'s2_work/tasks'/tid/'snapshot';base.mkdir(parents=True,exist_ok=True)
            for item in record['entries']:
                rel=Path(item['path'])
                if rel.is_absolute() or '..' in rel.parts: raise RuntimeError('Unsafe snapshot path')
                p=base/rel;p.parent.mkdir(parents=True,exist_ok=True)
                if item['type']=='directory': p.mkdir(exist_ok=True)
                elif item['type']=='symlink':
                    target=item['target']
                    if Path(target).is_absolute() or not (p.parent/target).resolve().is_relative_to(base.resolve()):
                        raise RuntimeError('Snapshot contains an escaping symbolic link: '+tid+'/'+str(rel))
                    p.symlink_to(target)
                else:
                    blob=blobs/item['sha256']
                    if not blob.exists():
                        data=z.read('blobs/'+item['sha256'])
                        assert hashlib.sha256(data).hexdigest()==item['sha256']
                        blob.write_bytes(data)
                    try: os.link(blob,p)
                    except OSError: shutil.copyfile(blob,p)
                    expanded+=item['size']
    snapshot_checks=[]
    for tid,record in snapshots.items():
        actual=sha_dir(pb/'s2_work/tasks'/tid/'snapshot')
        expected=record['expected_snapshot_sha256']
        snapshot_checks.append({'task':tid,'actual':actual,'expected':expected,'match':actual==expected if expected else None})
    (out/'snapshot-verification.json').write_text(json.dumps(snapshot_checks,indent=2)+'\n')
    mismatches=[r['task'] for r in snapshot_checks if r['match'] is False]
    if mismatches: raise RuntimeError('Historical snapshot hashes differ: '+str(mismatches))
    print('Snapshot hashes verified:',len(snapshot_checks),flush=True)
    # The nested freeze-time reader receives only an internal link to this
    # output's materialized evidence, never the author's source directory.
    fr=pb/'frozen_run/pathb_v2'
    (fr/'s2_work').symlink_to('../../s2_work',target_is_directory=True)
    # All assembly readings use the same active adjudication evidence.
    (fr/'adjudication').symlink_to('../../adjudication',target_is_directory=True)
    # Preserve copied score snapshots outside the execution tree. Every reading
    # must regenerate its complete row set, never inherit leftover old files.
    score_paths = [Path('scores'), Path('scores_adjudicated'),
                   Path('scores_adjudicated_adj1only'), Path('scores_adjudicated_nosubstance')]
    score_paths += [Path('frozen_run/pathb_v2') / name for name in
                    ('scores', 'scores_adjudicated', 'scores_adjudicated_adj1only')]
    for rel in score_paths:
        original = out/'input-derived-scores'/rel
        original.parent.mkdir(parents=True, exist_ok=True)
        (pb/rel).rename(original)
    logs=out/'logs';logs.mkdir();runs=[]
    def run(script,*argv):
        name=f'{len(runs)+1:02d}-{script.stem}'+('-'+argv[0].lstrip('-') if argv else '')
        log=logs/(name+'.txt')
        with log.open('w') as fh:
            result=subprocess.run([PY,'-B',str(ROOT/'guarded_python.py'),str(out),str(script),*argv],
                                  stdout=fh,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        runs.append({'script':str(script.relative_to(work)),'args':list(argv),'exit_code':result.returncode,'log':str(log.relative_to(out))})
        if result.returncode: raise RuntimeError('Reproduction failed; see '+str(log))
    run(pb/'freeze.py','verify')
    # Rebuild all active folds from final research records, never rerun an LLM.
    for options in [(),('--adj1-only',),('--no-substance',)]: run(pb/'adjudicate.py','fold',*options)
    for d in ['adjudicated','adjudicated_adj1only','adjudicated_nosubstance']:
        assert json.loads((pb/d/'splits.json').read_text())==[],d
    # Rebuild current compositions, and independently the freeze-time reading.
    run(pb/'assemble.py','--write')
    for options in [(),('--adjudicated',),('--adj1-only',),('--adjudicated','--adj-dir','adjudicated_nosubstance')]:
        run(pb/'scoring.py',*options,'--write')
    for d in ['adjudicated','adjudicated_adj1only']:
        shutil.copytree(pb/d,fr/d,dirs_exist_ok=True)
    run(fr/'assemble.py','--write')
    for options,name in [((),'results_frozenasm.json'),(('--adjudicated',),'results_frozenasm_adjudicated.json'),(('--adj1-only',),'results_frozenasm_adjudicated_adj1only.json')]:
        run(fr/'scoring.py',*options,'--write')
        source='results_adjudicated_adj1only.json' if '--adj1-only' in options else ('results_adjudicated.json' if options else 'results.json')
        shutil.copy2(fr/source,pb/name)
    score_comparisons = {}
    for rel in score_paths:
        expected_dir = ROOT/'experiments/pathb_v2'/rel
        actual_dir = pb/rel
        expected_files = {p.name for p in expected_dir.glob('*.json')}
        actual_files = {p.name for p in actual_dir.glob('*.json')}
        same_names = expected_files == actual_files
        changed = [name for name in sorted(expected_files & actual_files)
                   if json.loads((expected_dir/name).read_text()) != json.loads((actual_dir/name).read_text())]
        ids = [json.loads(p.read_text())['case_id'] for p in actual_dir.glob('*.json')]
        identities_match = actual_files == {cid+'.json' for cid in ids} and len(ids) == len(set(ids))
        score_comparisons[str(rel)] = {'rows': len(ids), 'file_sets_equal': same_names,
                                      'unique_case_filenames': identities_match, 'changed_files': changed}
        if not same_names or changed or not identities_match:
            raise RuntimeError('Per-case scores differ: '+str(score_comparisons[str(rel)]))
    (out/'score-comparisons.json').write_text(json.dumps(score_comparisons,indent=2)+'\n')
    # Compare every field. The only permitted historical metadata differences
    # are five exact, disclosed H1 wording corrections in pre-adjudication data.
    comparisons={}
    for expected in sorted((ROOT/'expected/results').glob('*.json')):
        actual=pb/expected.name
        delta=differences(json.loads(expected.read_text()),json.loads(actual.read_text()))
        allowed=json.loads((ROOT/'evidence/known-pre-adjudication-wording-differences.json').read_text()) if expected.name=='results.json' else []
        comparisons[expected.name]={'exact_match':not delta,'accepted':not delta or delta==allowed,'differences':delta}
    (out/'result-comparisons.json').write_text(json.dumps(comparisons,indent=2)+'\n')
    if not all(v['accepted'] for v in comparisons.values()): raise RuntimeError('Results differ from archived reference: '+str(comparisons))
    tables=out/'tables';tables.mkdir()
    # Require these outputs to be emitted now, never inherited from the packet.
    saved_reports = out/'input-derived-reports'; saved_reports.mkdir()
    for name in ('numbers.json', 'binary_metrics.json'):
        (pb/'report'/name).rename(saved_reports/name)
    run(pb/'make_report.py','--out',str(tables))
    run(pb/'supplementary_binary_metrics.py','--tex',str(tables/'binary_casecontrol.tex'))
    report_comparisons = verify_report_outputs(ROOT/'experiments/pathb_v2', pb)
    (out/'report-comparisons.json').write_text(json.dumps(report_comparisons,indent=2)+'\n')
    table_comparisons={p.name:p.read_bytes()==(tables/p.name).read_bytes() for p in (ROOT/'expected/tables').glob('*.tex') if (tables/p.name).exists()}
    assert len(table_comparisons)==44, len(table_comparisons)
    assert all(table_comparisons.values()),table_comparisons
    # Recompute the labelled single-case stratum sensitivity without changing
    # any adjudicated record. Compare both case IDs and all five method counts.
    pilot=set(json.loads((pb/'pilot/PILOT_CASES.json').read_text())['quarantined_pilot_cases'])
    rows=[json.loads(p.read_text()) for p in (pb/'scores_adjudicated').glob('*.json')]
    rows=[r for r in rows if r['corpus']=='C1' and r['outcome_class']=='failure' and r['case_id'] not in pilot]
    methods=['ECM','NT','DI','DQ','SV']; loud={}
    for name,relabel in [('retained',False),('protocol_single_case',True)]:
        silent=[r for r in rows if r['loudness']=='silent_documented' or (relabel and r['case_id']=='robust_bdda1fa')]
        loud[name]={'n':len(silent),'detections':{m:sorted(r['case_id'] for r in silent if r['broken'][m]['state']=='right_reason') for m in methods}}
    assert loud==json.loads((ROOT/'evidence/loudness_single_case.json').read_text()),loud
    text=(ROOT/'evidence/loudness_table_source.tex').read_text()
    for label,key in [('Retained adjudicated labels','retained'),('Case relabelled by protocol','protocol_single_case')]:
        values=[loud[key]['n']]+[len(loud[key]['detections'][m]) for m in methods]
        actual=[int(x) for x in re.search(re.escape(label)+r'\s*&([^\\]+)',text).group(1).split('&')]
        assert actual==values,(label,actual,values)
    (tables/'loudness_sensitivity.tex').write_text(text)
    (out/'loudness_single_case.json').write_text(json.dumps(loud,indent=2)+'\n')
    run(pb/'test_supplementary_binary_metrics.py')
    summary={'status':'verified','offline':True,'original_author_home_reads':'denied in every deterministic subprocess',
             'snapshot_trees_verified':len(snapshot_checks),'snapshot_logical_bytes':expanded,
             'results_equal':comparisons,'tables_equal':table_comparisons,'loudness_source_and_counts_verified':True,
             'per_case_scores_equal':score_comparisons,
             'generated_reports_equal':report_comparisons,
             'commands':runs,'models':json.loads((pb/'ledger/adjudicators.json').read_text()),
             'runtime_experiments':'not executed','model_generation':'archived final records; not rerun'}
    (out/'verification.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('Verified all readings, 44 generated fragments and loudness sensitivity:',out,flush=True)

if __name__=='__main__': main()
