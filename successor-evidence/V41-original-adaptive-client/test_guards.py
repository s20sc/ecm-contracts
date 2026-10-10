"""Integrity regressions; no original client endpoint is invoked by these tests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


def runner():
    spec = importlib.util.spec_from_file_location('adaptive_guard_subject', Path(__file__).with_name('run_adaptive.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Guards(unittest.TestCase):
    def test_prior_comparison_requires_every_cell_and_identical_metadata(self):
        subject = runner()
        inventory = {'candidate_count': 1, 'sha256': 'metadata'}
        cells = [{'valid_complete': True, 'receipt': {'provider': p, 'workflow': w,
                  'prepared_sha256': 'prior', 'metadata_before': inventory, 'metadata_after': inventory}}
                 for p in subject.base.PROVIDERS for w in ('rosidl_pytest', 'pip_list')]
        result = {'prepared_sha256': 'prior', 'cells': cells}
        subject.bind_previous_metadata(inventory, result, 'prior')
        with self.assertRaises(RuntimeError):
            subject.bind_previous_metadata({'candidate_count': 1, 'sha256': 'changed'}, result, 'prior')
        with self.assertRaises(RuntimeError):
            subject.bind_previous_metadata(inventory, dict(result, cells=cells[:-1]), 'prior')
        with self.assertRaises(RuntimeError):
            subject.bind_previous_metadata(inventory, result, 'different-seal')

    def test_endpoint_retry_and_broken_symlink_are_rejected_before_input_loading(self):
        subject = runner()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            output = root / 'u0395.json'
            output.write_text('original receipt')
            with self.assertRaisesRegex(RuntimeError, 'Existing'):
                subject.cell(root, 'u0395')
            self.assertEqual(output.read_text(), 'original receipt')
            output.unlink()
            output.symlink_to(root / 'missing')
            with self.assertRaisesRegex(RuntimeError, 'Existing'):
                subject.cell(root, 'u0395')

    def test_changed_source_is_rejected(self):
        subject = runner()
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'source.py'
            f.write_text('original')
            pins = {str(f): subject.base.pin(f)}
            f.write_text('changed')
            with self.assertRaises(RuntimeError):
                subject.verify_pins(pins)

    def test_output_equality_requires_every_provider_and_nonempty_groups(self):
        subject = runner()
        payload = {'console_scripts': [{'name': 'a', 'value': 'm:f', 'group': 'console_scripts'}],
                   'pytest11': [{'name': 'b', 'value': 'n:g', 'group': 'pytest11'}]}
        cells = [{'provider': p, 'status': 'complete', 'groups': payload} for p in subject.base.PROVIDERS]
        self.assertTrue(subject.mapping_equal(cells))
        self.assertFalse(subject.mapping_equal(cells[:-1]))
        bad = [dict(c) for c in cells]
        bad[2]['groups'] = dict(payload, pytest11=[])
        self.assertFalse(subject.mapping_equal(bad))
        changed = [dict(c) for c in cells]
        changed[2]['groups'] = dict(payload, pytest11=[{'name': 'b', 'value': 'changed:g', 'group': 'pytest11'}])
        self.assertFalse(subject.mapping_equal(changed))

    def test_receipt_cannot_be_accepted_for_another_seal_or_provider(self):
        subject = runner()
        receipt = {'status': 'complete', 'provider': 'u0395', 'prepared_sha256': 'seal'}
        self.assertTrue(subject.valid_receipt(receipt, 'u0395', 'seal', 0))
        self.assertFalse(subject.valid_receipt(receipt, 'u0394', 'seal', 0))
        self.assertFalse(subject.valid_receipt(receipt, 'u0395', 'other', 0))
        self.assertFalse(subject.valid_receipt(receipt, 'u0395', 'seal', 1))


if __name__ == '__main__':
    unittest.main()
