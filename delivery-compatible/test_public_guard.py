from pathlib import Path
import json
import importlib.machinery
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
import public_guard
import replay


class GuardTests(unittest.TestCase):
    def test_root_and_symlink_escape_and_no_reuse(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(); inputs = root / 'inputs'; inputs.mkdir()
            roots = {'package': inputs}
            with self.assertRaises(ValueError): public_guard.check_output(inputs / 'new', roots)
            (root / 'alias').symlink_to(inputs, target_is_directory=True)
            with self.assertRaises(ValueError): public_guard.check_output(root / 'alias' / 'new', roots)
            with self.assertRaises(FileExistsError): public_guard.check_output(inputs, roots)
            (inputs / 'escape').symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError): public_guard.child(inputs, 'escape/file.py')
            for path in ('../x', '/absolute', 'x\\y'):
                with self.assertRaises(ValueError): public_guard.child(inputs, path)

    def test_tamper_and_added_source_and_bytecode_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); source = root / 'sealed'; source.mkdir()
            entry = source / 'a.py'; entry.write_text('x = 1\n')
            manifest = root / 'inputs.json'
            value = {'schema': 1, 'files': [{'root': 'retained', 'relative': 'a.py',
                      'sha256': public_guard.digest(entry)}],
                     'exact_python_trees': [{'root': 'retained', 'relative': '.', 'paths': ['a.py']}]}
            manifest.write_text(json.dumps(value))
            with patch.object(public_guard, 'MANIFEST', manifest):
                self.assertEqual(public_guard.verify({'retained': source})['files'], 1)
                entry.write_text('x = 2\n')
                with self.assertRaisesRegex(ValueError, 'changed'): public_guard.verify({'retained': source})
                entry.write_text('x = 1\n'); extra = source / 'b.py'; extra.write_text('')
                with self.assertRaisesRegex(ValueError, 'inventory'): public_guard.verify({'retained': source})
                extra.unlink(); (source / 'b.pyc').write_bytes(b'not trusted')
                with self.assertRaisesRegex(ValueError, 'import binary'): public_guard.verify({'retained': source})

    def test_native_extension_cannot_shadow_sealed_python(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); entry = root / 'a.py'; entry.write_text('x = 1\n')
            manifest = root / 'inputs.json'
            manifest.write_text(json.dumps({'schema': 1, 'files': [
                {'root': 'retained', 'relative': 'a.py', 'sha256': public_guard.digest(entry)}],
                'exact_python_trees': [{'root': 'retained', 'relative': '.', 'paths': ['a.py']}]}))
            native = root / ('a' + importlib.machinery.EXTENSION_SUFFIXES[0])
            native.write_bytes(b'non-executed test fixture')
            chosen = importlib.machinery.PathFinder.find_spec('a', [str(root)])
            self.assertEqual(chosen.origin, str(native))
            with patch.object(public_guard, 'MANIFEST', manifest):
                with self.assertRaisesRegex(ValueError, 'import binary'):
                    public_guard.verify({'retained': root})

    def test_failed_preflight_keeps_attempt_and_never_executes_cells(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); inputs = root / 'inputs'; inputs.mkdir()
            config = root / 'config.json'; config.write_text('{}')
            output = root / 'attempt'
            with patch.object(public_guard, 'load_config', return_value={'runtime': inputs}), \
                 patch.object(public_guard, 'verify', side_effect=ValueError('changed source')), \
                 patch.object(replay, 'main') as endpoint:
                self.assertEqual(replay.launch(config, output), 1)
                endpoint.assert_not_called()
                self.assertTrue((output / 'started.json').is_file())
                self.assertEqual(json.loads((output / 'run-summary.json').read_text())['status'], 'failed')
                with self.assertRaises(FileExistsError): replay.launch(config, output)


if __name__ == '__main__': unittest.main()
