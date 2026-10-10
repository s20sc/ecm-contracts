from pathlib import Path
import hashlib
import json
import tempfile
import unittest
import zipfile
from restore_retained import restore, validate_relative


class RestoreTests(unittest.TestCase):
    def test_content_binding_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); package = root / 'package'; package.mkdir(); source = b'unchanged source'
            sha = hashlib.sha256(source).hexdigest(); archive = root / 'existing.zip'
            with zipfile.ZipFile(archive, 'w') as z: z.writestr('blobs/' + sha, source)
            manifest_dir = root / 'runtime'; manifest_dir.mkdir(); manifest = manifest_dir / 'inputs.json'
            value = {'schema': 1, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                     'files': [{'root': 'retained', 'relative': 'u0001/snapshot/example.py', 'sha256': sha}]}
            manifest.write_text(json.dumps(value)); output = root / 'restored'
            self.assertEqual(restore(manifest, archive, package, output)['file_count'], 1)
            self.assertEqual((output / 'u0001/snapshot/example.py').read_bytes(), source)
            with self.assertRaises(FileExistsError): restore(manifest, archive, package, output)
            archive.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'archive hash'): restore(manifest, archive, package, root / 'bad')
            self.assertFalse((root / 'bad').exists())

    def test_escape_and_non_task_layout_rejected(self):
        for value in ['../source.py', '/u0001/snapshot/x.py', 'u0001/snapshot/../../x',
                      'u0001/snapshot\\x.py', 'u0001/other/x.py']:
            with self.assertRaises(ValueError): validate_relative(value)


if __name__ == '__main__': unittest.main()
