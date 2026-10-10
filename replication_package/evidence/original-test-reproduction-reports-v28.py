"""Regression probes for report integrity and fresh output; no scientific reruns."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

WRAPPER = Path(os.environ.get('ECM_REPRO_WRAPPER', Path(__file__).with_name('reproduce.py')))
spec = importlib.util.spec_from_file_location('repro_under_test', WRAPPER)
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)

class ReportIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.expected, self.actual = self.base/'expected', self.base/'actual'
        for p in (self.expected, self.actual):
            (p/'report').mkdir(parents=True)
            (p/'source.json').write_text('{"value": 3}\n')
            self.write(p, 'numbers.json', {'submodules': [{'submodules': 1}], 'optional': None})
            self.write(p, 'binary_metrics.json', {'population_verification': {'aggregate_reproduced': True},
                'source_sha256': {'source.json': hashlib.sha256((p/'source.json').read_bytes()).hexdigest()}})

    def write(self, root, name, value):
        (root/'report'/name).write_text(json.dumps(value))

    def gate(self):
        return repro.verify_report_outputs(self.expected, self.actual)

    def test_stable_semantics_allow_json_formatting(self):
        p=self.actual/'report/binary_metrics.json'
        p.write_text(json.dumps(json.loads(p.read_text()),sort_keys=True,indent=3))
        self.assertEqual(self.gate()['binary_metrics.json']['source_hashes_verified'], 1)

    def test_scalar_types_and_key_presence(self):
        for a,b in [(True,1),(False,0),(1,1.0),({'a':None},{}),({}, {'a':None}),
                    ({'a':[{'b':None}]},{'a':[{}]})]:
            with self.subTest(a=a,b=b):
                self.assertTrue(repro.differences(a,b))

    def test_report_bool_is_not_integer(self):
        p=self.actual/'report/binary_metrics.json'; value=json.loads(p.read_text())
        value['population_verification']['aggregate_reproduced']=1
        self.write(self.actual,p.name,value)
        with self.assertRaises(RuntimeError): self.gate()

    def test_report_count_is_not_bool(self):
        p=self.actual/'report/numbers.json'; value=json.loads(p.read_text())
        value['submodules'][0]['submodules']=True
        self.write(self.actual,p.name,value)
        with self.assertRaises(RuntimeError): self.gate()

    def test_missing_null_key(self):
        p=self.actual/'report/numbers.json'; value=json.loads(p.read_text()); del value['optional']
        self.write(self.actual,p.name,value)
        with self.assertRaises(RuntimeError): self.gate()

    def test_source_mutation_or_loss(self):
        p=self.actual/'source.json'
        p.write_text('changed')
        with self.assertRaises(RuntimeError): self.gate()
        p.unlink()
        with self.assertRaises(RuntimeError): self.gate()

    def test_missing_hash_or_report(self):
        p=self.actual/'report/binary_metrics.json'; value=json.loads(p.read_text()); value['source_sha256']={}
        self.write(self.actual,p.name,value)
        with self.assertRaises(RuntimeError): self.gate()
        p.unlink()
        with self.assertRaises(FileNotFoundError): self.gate()

    def test_generators_must_emit_both_reports(self):
        # Exercise the actual orchestration segment, replacing only generator
        # invocation with controlled emit/no-op stubs. No snapshot expansion.
        main=next(n for n in ast.parse(WRAPPER.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='main')
        def assignment(n,name):
            return isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)
        start=next(i for i,n in enumerate(main.body) if assignment(n,'tables'))
        end=next(i for i,n in enumerate(main.body) if assignment(n,'report_comparisons'))
        code=compile(ast.Module(body=main.body[start:end+1],type_ignores=[]),str(WRAPPER),'exec')
        root=self.base/'package'; ref=root/'experiments/pathb_v2/report'; ref.mkdir(parents=True)
        originals={n:(self.expected/'report'/n).read_bytes() for n in ('numbers.json','binary_metrics.json')}
        for name,data in originals.items(): (ref/name).write_bytes(data)
        for i,emitted in enumerate([set(),{'numbers.json'},{'binary_metrics.json'},set(originals)]):
            with self.subTest(emitted=sorted(emitted)):
                for name,data in originals.items(): (self.actual/'report'/name).write_bytes(data)
                out=self.base/('run'+str(i));out.mkdir(); calls=[]
                def run(script,*args):
                    if not calls:
                        for name in originals: self.assertFalse((self.actual/'report'/name).exists())
                    calls.append(script.name)
                    name={'make_report.py':'numbers.json','supplementary_binary_metrics.py':'binary_metrics.json'}[script.name]
                    if name in emitted: (self.actual/'report'/name).write_bytes(originals[name])
                env={'out':out,'pb':self.actual,'ROOT':root,'run':run,'verify_report_outputs':repro.verify_report_outputs}
                if len(emitted)==2: exec(code,env)
                else:
                    with self.assertRaises(FileNotFoundError): exec(code,env)
                for name,data in originals.items(): self.assertEqual((out/'input-derived-reports'/name).read_bytes(),data)



import copy
import shutil
import subprocess
import sys
from unittest import mock
import loudness_report_gate as loud_gate

HERE = Path(__file__).resolve().parent
REBUILT = HERE/'experiments/pathb_v2'

class WrapperLoudnessSeamTests(unittest.TestCase):
    """Execute the actual main AST from table generation through final summary.

    Only main's earlier expensive reconstruction is excluded. Small pinned
    score/spec files are copied from the distributed archived inputs. The real
    gate, analyzer, file checks, table publication and final summary run here.
    """
    @classmethod
    def setUpClass(cls):
        pins=json.loads((HERE/'derived_loudness/frozen-input-pins.json').read_text())['files']
        cls.pinned={n:(REBUILT/n).read_bytes() for n in pins}
        cls.pilot=(REBUILT/'pilot/PILOT_CASES.json').read_bytes()
        for n,b in cls.pinned.items():
            if hashlib.sha256(b).hexdigest()!=pins[n]:raise AssertionError('Input pin changed: '+n)
        cls.original=ast.parse((HERE/'evidence/original-reproduce-v23.py').read_text())

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='seam-')
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.root=self.base/'package'
        self.out=self.base/'out';self.out.mkdir()
        self.pb=self.out/'work/experiments/pathb_v2';self.pb.mkdir(parents=True)
        self.expected=self.root/'experiments/pathb_v2'
        for p in (self.pb,self.expected):
            (p/'report').mkdir(parents=True)
            (p/'source.json').write_text('{"value":3}\n')
        self.reports={'numbers.json':json.dumps({'optional':None}).encode(),
            'binary_metrics.json':json.dumps({'source_sha256':{'source.json':repro.digest(self.pb/'source.json')}}).encode()}
        for p in (self.pb,self.expected):
            for n,b in self.reports.items():(p/'report'/n).write_bytes(b)
        for n,b in self.pinned.items():
            p=self.pb/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        (self.pb/'pilot').mkdir();(self.pb/'pilot/PILOT_CASES.json').write_bytes(self.pilot)
        (self.pb/'ledger').mkdir();(self.pb/'ledger/adjudicators.json').write_text('{"fixture":"archived models"}')
        for dirname in ('derived_loudness','evidence'):
            repro.copy_private_tree(HERE/dirname,self.root/dirname)
        td=self.root/'expected/tables';td.mkdir(parents=True)
        for i in range(44):(td/f'table{i:02}.tex').write_text(f'Test fragment {i}\n')
        self.calls=[]
        def run(script,*args):
            self.calls.append(script.name)
            if script.name=='make_report.py':
                (self.pb/'report/numbers.json').write_bytes(self.reports['numbers.json'])
                for p in td.iterdir():shutil.copyfile(p,self.out/'tables'/p.name)
            elif script.name=='supplementary_binary_metrics.py':
                (self.pb/'report/binary_metrics.json').write_bytes(self.reports['binary_metrics.json'])
            elif script.name!='test_supplementary_binary_metrics.py':
                raise AssertionError('Unexpected scientific execution: '+script.name)
        main=next(n for n in ast.parse(WRAPPER.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='main')
        def assigned(n,name):return isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)
        start=next(i for i,n in enumerate(main.body) if assigned(n,'tables'))
        self.code=compile(ast.Module(body=main.body[start:],type_ignores=[]),str(WRAPPER),'exec')
        self.env=dict(vars(repro),ROOT=self.root,out=self.out,pb=self.pb,run=run,
            snapshot_checks=[],expanded=0,comparisons={'fixture':{'accepted':True}},
            score_comparisons={'fixture':{'changed_files':[]}},runs=[],regenerate_and_verify=loud_gate.regenerate_and_verify)

    def execute(self):
        with mock.patch('builtins.print'):exec(self.code,self.env)

    def blocked(self):
        with self.assertRaises((ValueError,RuntimeError,OSError,TypeError,AttributeError)):self.execute()
        self.assertFalse((self.out/'verification.json').exists())
        self.assertNotIn('test_supplementary_binary_metrics.py',self.calls)

    def test_normal_path_uses_rebuilt_source_and_publishes_generated_table(self):
        calls=[]
        def tracked(**kw):calls.append(kw);return loud_gate.regenerate_and_verify(**kw)
        self.env['regenerate_and_verify']=tracked
        self.execute()
        self.assertEqual(len(calls),1);self.assertEqual(calls[0]['source_dir'],self.pb)
        self.assertNotEqual(calls[0]['source_dir'],self.expected)
        receipt=json.loads((self.out/'verification.json').read_text())
        self.assertEqual(receipt['status'],'verified')
        self.assertIs(receipt['loudness_v24']['fresh_generation_verified'],True)
        self.assertNotIn('loudness_source_and_counts_verified',receipt)
        fresh=(self.out/'loudness-v24/loudness-sensitivity.tex').read_bytes()
        self.assertEqual((self.out/'tables/loudness_sensitivity.tex').read_bytes(),fresh)
        self.assertNotEqual(fresh,(self.root/'evidence/loudness_table_source.tex').read_bytes())
        self.assertFalse((self.out/'loudness_single_case.json').exists())
        self.assertEqual(receipt['loudness_v24']['source_pin_count'],252)
        self.assertEqual(receipt['loudness_v24']['original_failure_prediction_count'],93)
        self.assertEqual(self.calls,['make_report.py','supplementary_binary_metrics.py','test_supplementary_binary_metrics.py'])

    def test_noop_actual_generator_blocks_final_summary(self):
        with mock.patch.object(loud_gate,'_write_generated',return_value=None):self.blocked()

    def test_partial_actual_generator_blocks_final_summary(self):
        writer=loud_gate._write_generated
        def omit(a,source,out):writer(a,source,out);(out/'summary.json').unlink()
        with mock.patch.object(loud_gate,'_write_generated',side_effect=omit):self.blocked()

    def test_failed_gate_blocks_final_summary(self):
        self.env['regenerate_and_verify']=mock.Mock(side_effect=ValueError('injected gate failure'))
        self.blocked()

    def test_noop_gate_blocks_final_summary(self):
        self.env['regenerate_and_verify']=lambda **kw:None
        self.blocked()

    def test_false_success_without_files_blocks_final_summary(self):
        def liar(**kw):
            return {'status':'verified_derived_report','fresh_generation_verified':True,
              'complete_json_and_scalar_types_verified':True,'tex_matches_json_and_reference':True,
              'all_scenarios_corpora_methods_verified':True,'source_pin_count':252,
              'original_failure_prediction_count':93,'outputs_sha256':{}}
        self.env['regenerate_and_verify']=liar;self.blocked()

    def change_receipt(self,change):
        def changed(**kw):
            result=loud_gate.regenerate_and_verify(**kw);change(result,kw);return result
        self.env['regenerate_and_verify']=changed

    def test_false_receipt_with_valid_outputs_blocks_final_summary(self):
        self.change_receipt(lambda r,k:r.__setitem__('fresh_generation_verified',False));self.blocked()

    def test_integer_success_is_not_boolean_success(self):
        self.change_receipt(lambda r,k:r.__setitem__('fresh_generation_verified',1));self.blocked()

    def test_missing_completion_flag_blocks_final_summary(self):
        self.change_receipt(lambda r,k:r.pop('all_scenarios_corpora_methods_verified'));self.blocked()

    def test_valid_receipt_then_missing_output_blocks_final_summary(self):
        self.change_receipt(lambda r,k:(k['out_dir']/'loudness-analysis.json').unlink());self.blocked()

    def test_table_changed_after_gate_blocks_final_summary(self):
        self.change_receipt(lambda r,k:(k['out_dir']/'loudness-sensitivity.tex').write_text('changed'))
        self.blocked()

    def test_output_manifest_changed_after_gate_blocks_final_summary(self):
        self.change_receipt(lambda r,k:(k['out_dir']/'output-sha256.json').write_text('{}'))
        self.blocked()

    def test_inherited_directory_blocks_gate_before_call(self):
        (self.out/'loudness-v24').mkdir()
        call=mock.Mock();self.env['regenerate_and_verify']=call
        self.blocked();call.assert_not_called()

    def test_symlinked_output_blocks_final_summary(self):
        def change(r,k):
            p=k['out_dir']/'summary.json';target=self.base/'summary-copy.json'
            target.write_bytes(p.read_bytes());p.unlink();p.symlink_to(target)
        self.change_receipt(change);self.blocked()

    def test_existing_published_table_is_not_overwritten(self):
        original=self.env['run']
        def run(script,*args):
            original(script,*args)
            if script.name=='supplementary_binary_metrics.py':
                (self.out/'tables/loudness_sensitivity.tex').write_text('existing sentinel')
        self.env['run']=run;self.blocked()
        self.assertEqual((self.out/'tables/loudness_sensitivity.tex').read_text(),'existing sentinel')

    def test_bad_original_pinned_source_blocks_final_summary(self):
        n=next(iter(self.pinned));(self.pb/n).write_bytes(self.pinned[n]+b' ')
        self.blocked()

    def test_published_table_comes_from_generation_not_late_reference_copy(self):
        self.change_receipt(lambda r,k:k['reference_tex'].write_text('late reference sentinel'))
        self.execute()
        self.assertEqual((self.out/'tables/loudness_sensitivity.tex').read_bytes(),
                         (self.out/'loudness-v24/loudness-sensitivity.tex').read_bytes())
        self.assertNotEqual((self.out/'tables/loudness_sensitivity.tex').read_text(),'late reference sentinel')

    def test_actual_main_seam_structure_and_preceding_gates_preserved(self):
        def main(tree):return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        old=main(self.original);new=main(ast.parse(WRAPPER.read_text()))
        def assigned(n,name):return isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)
        oi=next(i for i,n in enumerate(old.body) if assigned(n,'tables'))
        ni=next(i for i,n in enumerate(new.body) if assigned(n,'tables'))
        before=[n for n in new.body[:ni] if not isinstance(n,ast.ImportFrom)]
        self.assertEqual(ast.dump(ast.Module(body=before,type_ignores=[])),ast.dump(ast.Module(body=old.body[:oi],type_ignores=[])))
        gi=next(i for i,n in enumerate(new.body) if assigned(n,'loudness_gate'))
        call=new.body[gi].value;self.assertEqual(call.func.id,'regenerate_and_verify')
        self.assertEqual(next(k.value.id for k in call.keywords if k.arg=='source_dir'),'pb')
        self.assertTrue(assigned(new.body[gi+1],'loudness_table'))
        self.assertEqual(new.body[gi+1].value.func.id,'verify_loudness_gate_receipt')
        self.assertIsInstance(new.body[gi+2],ast.With)
        self.assertIn("'xb'",ast.unparse(new.body[gi+2]))
        si=next(i for i,n in enumerate(new.body) if assigned(n,'summary'))
        self.assertGreater(si,gi+2)
        summary=new.body[si].value
        fields={k.value:v for k,v in zip(summary.keys,summary.values)}
        self.assertEqual(ast.dump(fields['loudness_v24']),ast.dump(ast.Name(id='loudness_gate',ctx=ast.Load())))
        self.assertNotIn('loudness_source_and_counts_verified',fields)
        imports=[i for i,n in enumerate(new.body) if isinstance(n,ast.ImportFrom) and n.module=='loudness_report_gate']
        self.assertEqual(len(imports),1)
        mi=next(i for i,n in enumerate(new.body) if assigned(n,'manifest'))
        self.assertIsInstance(new.body[mi+1],ast.For)
        self.assertGreater(imports[0],mi+1)

if __name__ == '__main__': unittest.main(verbosity=2)
