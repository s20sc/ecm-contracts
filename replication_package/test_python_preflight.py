"""Small mocked import/entry-point probes; never expand archived snapshots."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

WRAPPER = Path(os.environ.get('ECM_REPRO_WRAPPER', Path(__file__).with_name('reproduce.py')))
spec = importlib.util.spec_from_file_location('preflight_repro_test', WRAPPER)
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)


class StopAtCopy(Exception):
    pass


class PythonPreflightTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=os.environ.get('ECM_PREFLIGHT_TEST_TMPDIR'))
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        real_temp = tempfile.TemporaryDirectory
        patcher = mock.patch.object(repro.tempfile, 'TemporaryDirectory',
                                    side_effect=lambda **kw: real_temp(dir=self.base, **kw))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_exact_interpreter_guard_and_cleanup(self):
        probes = []
        def smoke(argv, **kwargs):
            self.assertEqual(argv[:3], [repro.PY, '-B', str(repro.ROOT / 'guarded_python.py')])
            root, script = Path(argv[3]), Path(argv[4])
            self.assertTrue(script.is_relative_to(root))
            self.assertEqual(script.read_text(), 'import pkgutil\n')
            self.assertEqual(kwargs['env']['PYTHONDONTWRITEBYTECODE'], '1')
            probes.append(root)
            return subprocess.CompletedProcess(argv, 0, '', '')
        with mock.patch.object(repro.subprocess, 'run', side_effect=smoke) as run:
            repro.preflight_guarded_python()
            run.assert_called_once()
        self.assertFalse(probes[0].exists())

    def exercise_main(self, interpreter, returncode, diagnostic):
        out = self.base / 'output'
        result = subprocess.CompletedProcess([], returncode, '', diagnostic)
        gate = types.SimpleNamespace(regenerate_and_verify=mock.Mock())
        with mock.patch.object(repro, 'PY', interpreter), \
             mock.patch.object(repro, 'verify_package_inputs', return_value=self.base / 'archive.zip') as verify, \
             mock.patch.object(repro.subprocess, 'run', return_value=result) as run, \
             mock.patch.object(repro, 'copy_private_tree', side_effect=StopAtCopy) as copy, \
             mock.patch.object(repro.zipfile, 'ZipFile') as unzip, \
             mock.patch.dict(sys.modules, {'loudness_report_gate': gate}), \
             mock.patch.object(sys, 'argv', [str(WRAPPER), '--out', str(out)]):
            if returncode:
                with self.assertRaisesRegex(RuntimeError, 'preflight failed before materialization') as raised:
                    repro.main()
                self.assertIn(diagnostic, str(raised.exception))
                self.assertIn(interpreter, str(raised.exception))
                self.assertIn('Do not disable the guard', str(raised.exception))
                copy.assert_not_called()
                self.assertFalse(out.exists())
            else:
                with self.assertRaises(StopAtCopy):
                    repro.main()
                copy.assert_called_once()
                self.assertTrue(out.is_dir())
            verify.assert_called_once()
            run.assert_called_once()
            unzip.assert_not_called()
        self.assertFalse(any(self.base.glob('ecm-python-preflight-*')))

    def test_home_stdlib_failure_stops_actual_main_before_materialization(self):
        self.exercise_main('/Users/example/miniforge3/bin/python3', 1,
                           'PermissionError: Author-home dependency forbidden: /Users/example/miniforge3/lib/python3.11/pkgutil.py')

    def test_supported_system_interpreter_reaches_copy(self):
        self.exercise_main('/usr/local/bin/python3', 0, '')

    def test_home_executable_with_compatible_stdlib_is_not_rejected_by_location(self):
        self.exercise_main('/Users/example/venv/bin/python3', 0, '')

    def test_unavailable_interpreter_fails_without_materialization(self):
        with mock.patch.object(repro.subprocess, 'run', side_effect=FileNotFoundError('missing')):
            with self.assertRaisesRegex(RuntimeError, 'select an available Python 3.10'):
                repro.preflight_guarded_python()
        self.assertEqual(list(self.base.iterdir()), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
