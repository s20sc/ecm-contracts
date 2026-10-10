"""Exercise actual shared-archive input gates; fixtures never expand a corpus."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

WRAPPER = Path(os.environ.get('ECM_REPRO_WRAPPER', Path(__file__).with_name('reproduce.py')))
spec = importlib.util.spec_from_file_location('shared_repro_test', WRAPPER)
repro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repro)


class SharedSnapshotInputs(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.package = self.base / 'package'
        self.package.mkdir()
        self.archive = self.base / 'external archive.zip'
        self.archive.write_bytes(b'fixture archive bytes')
        self.source = self.package / 'source.txt'
        self.source.write_text('fixture source')
        self.manifest = {'files': {'snapshots.zip': repro.digest(self.archive),
                                   'source.txt': repro.digest(self.source)}}
        self.write_manifest()

    def write_manifest(self):
        (self.package / 'PACKAGE_MANIFEST.json').write_text(json.dumps(self.manifest))

    def test_external_archive_without_local_copy(self):
        self.assertEqual(repro.verify_package_inputs(self.package, self.archive), self.archive.resolve())
        self.assertFalse((self.package / 'snapshots.zip').exists())

    def test_default_self_contained_archive(self):
        local = self.package / 'snapshots.zip'
        local.write_bytes(self.archive.read_bytes())
        self.assertEqual(repro.verify_package_inputs(self.package), local.resolve())

    def test_default_requires_local_archive(self):
        with self.assertRaises(FileNotFoundError):
            repro.verify_package_inputs(self.package)

    def test_wrong_external_archive_cannot_fall_back_to_good_local(self):
        (self.package / 'snapshots.zip').write_bytes(self.archive.read_bytes())
        self.archive.write_bytes(b'wrong archive')
        with self.assertRaises(ValueError):
            repro.verify_package_inputs(self.package, self.archive)

    def test_missing_external_archive_cannot_fall_back_to_good_local(self):
        (self.package / 'snapshots.zip').write_bytes(self.archive.read_bytes())
        with self.assertRaises(FileNotFoundError):
            repro.verify_package_inputs(self.package, self.base / 'missing.zip')

    def test_every_other_package_input_remains_pinned(self):
        self.source.write_text('changed')
        with self.assertRaises(ValueError):
            repro.verify_package_inputs(self.package, self.archive)

    def test_missing_archive_pin_rejected(self):
        del self.manifest['files']['snapshots.zip']
        self.write_manifest()
        with self.assertRaises(ValueError):
            repro.verify_package_inputs(self.package, self.archive)

    def test_actual_main_rejects_bad_input_before_output_or_extraction(self):
        self.archive.write_bytes(b'wrong archive')
        out = self.base / 'output'
        argv = [str(WRAPPER), '--out', str(out), '--snapshot-archive', str(self.archive)]
        with mock.patch.object(repro, 'ROOT', self.package), mock.patch.object(sys, 'argv', argv), \
             mock.patch.object(repro, 'copy_private_tree') as copy, \
             mock.patch.object(repro.zipfile, 'ZipFile') as unzip:
            with self.assertRaises(ValueError):
                repro.main()
            copy.assert_not_called()
            unzip.assert_not_called()
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
