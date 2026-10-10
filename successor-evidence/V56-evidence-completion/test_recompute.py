"""Bounded integration tests; no primary input or source record is edited."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parents[1] / 'replication_package'


class RecomputeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.evidence = self.base / 'evidence'
        shutil.copytree(HERE, self.evidence)
        self.output = self.base / 'result.json'

    def seal(self):
        files = {p.relative_to(self.evidence).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.evidence.rglob('*') if p.is_file() and p.name != 'EVIDENCE_FILES.json'}
        (self.evidence / 'EVIDENCE_FILES.json').write_text(json.dumps({'files': files}))

    def run_command(self):
        return subprocess.run([sys.executable, '-B', str(self.evidence / 'recompute.py'),
                               '--package', str(PACKAGE), '--out', str(self.output)],
                              capture_output=True, text=True)

    def test_baseline_and_portable_receipt(self):
        result = self.run_command()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(self.output.read_text())
        self.assertTrue(data['original_reaggregation_matches'])
        credit = data['exclusion']['all']['methods']['ECM']['right_reason']
        self.assertEqual((credit['k'], credit['n']), (14, 92))
        self.assertEqual(data['exclusion']['H1']['mcnemar_exact_two_sided_p'], 0.5)
        self.assertTrue(all(k.startswith(('package/', 'evidence/')) for k in data['input_sha256']))
        self.assertNotIn(str(self.base), self.output.read_text())

    def test_tampered_source_rejected(self):
        p = next((self.evidence / 'sources').rglob('*.py'))
        p.write_bytes(p.read_bytes() + b'\n# tampered\n')
        result = self.run_command()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('hash mismatch', result.stderr)
        self.assertFalse(self.output.exists())

    def test_bad_quote_rejected_after_inventory_update(self):
        p = self.evidence / 'control-source-review.json'
        data = json.loads(p.read_text()); data['items'][0]['evidence'][0]['quote'] += 'wrong'
        p.write_text(json.dumps(data)); self.seal()
        result = self.run_command()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Nonverbatim quote', result.stderr)
        self.assertFalse(self.output.exists())

    def test_missing_method_rejected_after_inventory_update(self):
        p = self.evidence / 'retained-boundary-replay.json'
        data = json.loads(p.read_text()); del data['rows'][0]['broken']['SV']
        p.write_text(json.dumps(data)); self.seal()
        result = self.run_command()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Incomplete or invalid boundary method states', result.stderr)
        self.assertFalse(self.output.exists())

    def test_output_inside_evidence_rejected(self):
        self.output = self.evidence / 'new-result.json'
        result = self.run_command()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('outside the package and evidence trees', result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
