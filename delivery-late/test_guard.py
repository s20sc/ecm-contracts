"""Targeted guards and comparisons; includes a local synthetic replay, not original science."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import os
import json
import subprocess
import sys
from types import SimpleNamespace

spec=importlib.util.spec_from_file_location('delivery_late',Path(__file__).with_name('replay.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Guards(unittest.TestCase):
    def setUp(self):
        self.guard=m.ReadOnlyGuard(set());self.guard.enabled=True
    def test_write_modes_and_flags(self):
        for mode,flags in [('w',0),('r+',0),('r',os.O_CREAT),('r',os.O_RDWR)]:
            with self.assertRaises(RuntimeError):self.guard('open',('/tmp/no-write',mode,flags))
    def test_network_subprocess_and_mutation(self):
        for event in ['socket.connect','subprocess.Popen','os.remove','os.rename','os.system','ctypes.dlopen']:
            with self.assertRaises(RuntimeError):self.guard(event,())
    def test_unsealed_read(self):
        with self.assertRaises(RuntimeError):self.guard('open',('/tmp/unsealed-private','r',0))
    def test_unknown_logical_alias(self):
        with self.assertRaises(RuntimeError):m.LogicalProject({})/'undeclared'
    def test_escape_and_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for relative in ['../outside','/absolute']:
                with self.assertRaises(ValueError):m.contained_file(root,relative)
            (root/'outside').symlink_to(Path(__file__).resolve())
            with self.assertRaises(ValueError):m.contained_file(root,'outside')
    def test_typed_diff(self):
        self.assertTrue(m.differences({'a':1},{'a':True}))
        self.assertTrue(m.differences({'a':1},{'b':1}))
        self.assertFalse(m.differences({'a':[1,2]},{'a':[1,2]}))
    def test_native_and_bytecode_cannot_replace_helper(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=root/'canonical.py';source.write_text('VALUE = 17\n')
            (root/'canonical.so').write_bytes(b'not an extension')
            (root/'canonical.pyc').write_bytes(b'not bytecode')
            finder=m.SourceOnlyFinder({'canonical':source},{source:m.sha(source)})
            found=finder.find_spec('canonical')
            self.assertIsInstance(found.loader,m.SourceOnlyLoader)
            self.assertEqual(found.origin,str(source))
            from types import ModuleType
            loaded=ModuleType('fixture_helper'); found.loader.exec_module(loaded)
            self.assertEqual(loaded.VALUE,17)
            self.assertEqual(loaded.__file__,str(source))
    def test_bad_source_pin_before_execution(self):
        with self.assertRaises(RuntimeError):m.load_module('cannot_execute_unpinned',Path(__file__).resolve(),'0'*64)

    def test_pinned_runner_profile_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve(); runner=root/'replay.py'; runner.write_text('VALUE = 17\n')
            identity=m.Identity({runner:m.sha(runner)},root)
            frame=SimpleNamespace(f_code=SimpleNamespace(co_filename=str(runner),co_name='run'),
                                  f_globals={'__file__':str(runner),'__name__':'fixture_runner'})
            identity.profile(frame,'call',None)
            self.assertEqual(identity.records[str(runner)]['function_calls'],{'run':1})
            runner.write_text('VALUE = 18\n')
            with self.assertRaisesRegex(RuntimeError,'Runtime source identity mismatch'):
                identity.profile(frame,'call',None)

    def test_pinned_runner_does_not_whitelist_sibling_module(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve(); runner=root/'replay.py'; runner.write_text('VALUE = 17\n')
            identity=m.Identity({runner:m.sha(runner)},root)
            unsealed=root/'sibling.py'; unsealed.write_text('VALUE = 18\n')
            frame=SimpleNamespace(f_code=SimpleNamespace(co_filename=str(unsealed),co_name='run'),
                                  f_globals={'__file__':str(unsealed),'__name__':'unsealed'})
            with self.assertRaisesRegex(RuntimeError,'Unsealed runtime module'):
                identity.profile(frame,'call',None)

    def test_synthetic_run_pins_exact_runner_under_public_root(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td).resolve();root=base/'public';root.mkdir();entry=root/'delivery-late';entry.mkdir()
            runner=entry/'replay.py';runner.write_bytes(Path(m.__file__).read_bytes())
            expected={'rows':[],'outcome_census':{},'aggregate_source_reported_failures':{}}
            files={'freeze.json':{'files':{},'ledgers':{}},'inputs.json':expected,'reference.json':expected}
            for name,value in files.items(): (root/name).write_text(json.dumps(value))
            (root/'original.py').write_text('def evaluate(data):\n    return data\n')
            seal={'schema':1,'files':{name:m.sha(root/name) for name in [*files,'original.py']},
                  'replay':'original.py','inputs':'inputs.json','project_aliases':{},
                  'modes':{'historical':{'modules':{},'freeze':'freeze.json','reference':'reference.json'}}}
            seal_path=entry/'public-input-seal.json';seal_path.write_text(json.dumps(seal))
            out=base/'result'
            run=subprocess.run([sys.executable,'-B',str(runner),'--public-root',str(root),
                                '--seal',str(seal_path),'--seal-sha256',m.sha(seal_path),
                                '--mode','historical','--output-dir',str(out)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+'\n'+run.stderr)
            receipt=json.loads((out/'receipt.json').read_text())
            self.assertEqual(receipt['status'],'matched')
            records={r['actual_file']:r for r in receipt['runtime_identity']}
            self.assertIn(str(runner),records)
            self.assertEqual(records[str(runner)]['expected_sha256'],m.sha(runner))
            self.assertTrue(records[str(runner)]['function_execution_observed'])
            runner.write_text(runner.read_text().replace('        expected[runner] = runner_hash\n',''))
            failed=subprocess.run([sys.executable,'-B',str(runner),'--public-root',str(root),
                                   '--seal',str(seal_path),'--seal-sha256',m.sha(seal_path),
                                   '--mode','historical','--output-dir',str(base/'regression')],capture_output=True,text=True)
            self.assertNotEqual(failed.returncode,0)
            self.assertIn('Unsealed runtime module',failed.stdout+failed.stderr)


if __name__=='__main__':unittest.main()
