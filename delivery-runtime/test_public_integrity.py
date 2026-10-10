"""Guard regressions using small independent fixtures, no scientific rerun."""
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch
import json
import tempfile
import public_integrity as public


class PublicGuardTests(TestCase):
    def test_modified_missing_and_added_source_fail(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); source = root / 'source'; source.mkdir()
            f = source / 'one.py'; f.write_text('original')
            seal = root / 'manifest.json'
            seal.write_text(json.dumps({'schema': 1, 'files': [
                {'root': 'runtime', 'relative': 'source/one.py', 'sha256': public.digest(f)}],
                'exact_python_trees': [{'root': 'runtime', 'relative': 'source', 'paths': ['source/one.py']}]}))
            with patch.object(public, 'MANIFEST', seal), patch.object(public, 'roots', return_value={'runtime': root}):
                self.assertEqual(public.verify()['verified_files'], 1)
                f.write_text('modified')
                with self.assertRaisesRegex(RuntimeError, 'changed'): public.verify()
                f.write_text('original'); extra = source / 'extra.py'; extra.write_text('injected import')
                with self.assertRaisesRegex(RuntimeError, 'inventory'): public.verify()
                extra.unlink(); f.unlink()
                with self.assertRaisesRegex(RuntimeError, 'missing'): public.verify()

    def test_relative_configuration_relocates(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); config = root / 'config.json'
            config.write_text(json.dumps({'schema': 1, 'package': 'data/package', 'retained': 'data/tasks',
                'intake': 'data/intake', 'previous_contrast': 'outputs/contrast'}))
            with patch.dict('os.environ', ECM_REPLAY_CONFIG=str(config)):
                self.assertEqual(public.roots()['package'], (root / 'data/package').resolve())
                self.assertEqual(public.previous_contrast(), (root / 'outputs/contrast').resolve())
                with self.assertRaises(ValueError): public.check_output(root / 'data/package/result')
                public.check_output(root / 'outputs/new')

    def test_traversal_and_escape_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); inside = root / 'inside'; inside.mkdir(); outside = root / 'outside'; outside.write_text('x')
            for rel in ('../outside', '/outside', 'a\\b'):
                with self.assertRaises(ValueError): public.safe_child(inside, rel)
            (inside / 'link').symlink_to(outside)
            with self.assertRaises(ValueError): public.safe_child(inside, 'link')

    def test_attempt_marker_and_prepared_tampering(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name); prepared = output / 'prepared.json'; prepared.write_text('{"prediction": "accept"}')
            public.seal_prepared(output); public.verify_prepared(output)
            prepared.write_text('{"prediction": "reject"}')
            with self.assertRaises(RuntimeError): public.verify_prepared(output)
            with patch.object(public, 'check_output'):
                public.claim_attempt(output, 'cell', ['cell.json'])
                with self.assertRaises(FileExistsError): public.claim_attempt(output, 'cell', ['cell.json'])
                (output / 'other.json').symlink_to(output / 'missing')
                with self.assertRaises(RuntimeError): public.claim_attempt(output, 'other', ['other.json'])

    def test_guard_does_not_accept_duplicate_or_empty_seal(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); f = root / 'x'; f.write_text('x'); seal = root / 'manifest.json'
            row = {'root': 'runtime', 'relative': 'x', 'sha256': public.digest(f)}
            with patch.object(public, 'MANIFEST', seal), patch.object(public, 'roots', return_value={'runtime': root}):
                for rows in ([], [row, row]):
                    seal.write_text(json.dumps({'schema': 1, 'files': rows}))
                    with self.assertRaises(ValueError): public.verify()


if __name__ == '__main__': main()
