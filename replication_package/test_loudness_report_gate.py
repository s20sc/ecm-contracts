"""Local gate probes only; no full reproduction, scorer, models or network."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import loudness_report_gate as gate

HERE=Path(__file__).resolve().parent
ANALYZER=HERE/'derived_loudness/loudness_analysis.py'
SOURCE=HERE/'experiments/pathb_v2'
REFERENCE=HERE/'evidence'
OLD_REFERENCE=SOURCE.parents[1]/'evidence/loudness_single_case.json'


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='gate-probe-')
        self.root=Path(self.temp.name)
        self.refs=self.root/'references';self.refs.mkdir()
        shutil.copyfile(REFERENCE/'loudness_v24.json',self.refs/'report.json')
        shutil.copyfile(REFERENCE/'loudness_v24_table.tex',self.refs/'table.tex')
        self.kwargs={'source_dir':SOURCE,'analyzer_path':ANALYZER,
                     'reference_json':self.refs/'report.json','reference_tex':self.refs/'table.tex',
                     'out_dir':self.root/'fresh'}
        self.a=gate.load_analyzer(ANALYZER)

    def tearDown(self):
        self.temp.cleanup()

    def run_gate(self,**kwargs):
        return gate.regenerate_and_verify(**dict(self.kwargs,**kwargs))

    def copy_source(self):
        dest=self.root/'relocated-source'
        pins=self.a.read_json(HERE/'derived_loudness/frozen-input-pins.json')['files']
        for name in pins:
            p=dest/name;p.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(SOURCE/name,p)
        return dest

    def refresh_output_hashes(self,out):
        names=gate.EXPECTED_FILES-{'output-sha256.json'}
        (out/'output-sha256.json').write_bytes(self.a.encoded({n:self.a.digest((out/n).read_bytes()) for n in names if (out/n).exists()}))

    def reject_output_mutation(self,mutation,message=None):
        original=gate._write_generated
        def corrupt(a,source,out):
            original(a,source,out)
            data=a.read_json(out/'loudness-analysis.json')
            mutation(data)
            (out/'loudness-analysis.json').write_bytes(a.encoded(data))
            # Keep output hashes coherent, so these tests exercise schema/source
            # comparisons, not just a stale output checksum.
            self.refresh_output_hashes(out)
        with mock.patch.object(gate,'_write_generated',corrupt):
            if message:
                with self.assertRaisesRegex(ValueError,message):self.run_gate()
            else:
                with self.assertRaises(ValueError):self.run_gate()

    def test_valid_fresh_generation_checks_all_252_pins_and_93_predictions(self):
        result=self.run_gate()
        self.assertIs(result['fresh_generation_verified'],True)
        self.assertEqual(result['source_pin_count'],252)
        self.assertEqual(result['original_failure_prediction_count'],93)
        actual=self.a.read_json(self.kwargs['out_dir']/'loudness-analysis.json')
        self.assertEqual(actual,self.a.read_json(self.kwargs['reference_json']))

    def test_default_cli_preflight_writes_nothing_and_is_not_fresh_success(self):
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        command=[sys.executable,'-B',str(HERE/'loudness_report_gate.py'),'--source',str(SOURCE),'--analyzer',str(ANALYZER),
                 '--reference-json',str(self.kwargs['reference_json']),'--reference-tex',str(self.kwargs['reference_tex'])]
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads(result.stdout)
        self.assertIs(report['fresh_generation_verified'],False)
        self.assertIs(report['wrote_outputs'],False)
        after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_missing_write_noop_generator_fails(self):
        with mock.patch.object(gate,'_write_generated',return_value=None):
            with self.assertRaisesRegex(ValueError,'omitted'):self.run_gate()

    def test_partial_write_missing_tex_fails(self):
        original=gate._write_generated
        def omit(a,source,out):
            original(a,source,out);(out/'loudness-sensitivity.tex').unlink()
        with mock.patch.object(gate,'_write_generated',omit):
            with self.assertRaisesRegex(ValueError,'omitted'):self.run_gate()

    def test_valid_inherited_output_directory_is_rejected(self):
        self.run_gate()
        with mock.patch.object(gate,'_write_generated') as writer:
            with self.assertRaisesRegex(ValueError,'inherited'):self.run_gate()
            writer.assert_not_called()

    def test_two_equal_stale_reference_and_actual_cannot_pass(self):
        r=self.a.read_json(self.kwargs['reference_json'])
        r['scenarios']['all_seven_stage_only_post_outcome']['corpora']['C3']=copy.deepcopy(r['scenarios']['retained']['corpora']['C3'])
        self.kwargs['reference_json'].write_bytes(self.a.encoded(r))
        self.kwargs['reference_tex'].write_text(self.a.tex_table(r))
        # A writer copying the same stale reference would fool a two-file-only
        # comparison. Source-derived preflight rejects it before that writer runs.
        def stale_writer(a,source,out):
            shutil.copyfile(self.kwargs['reference_json'],out/'loudness-analysis.json')
        with mock.patch.object(gate,'_write_generated',side_effect=stale_writer) as writer:
            with self.assertRaisesRegex(ValueError,'schema'):self.run_gate()
            writer.assert_not_called()
        self.assertFalse(self.kwargs['out_dir'].exists())

    def test_missing_corpus_method_scenario_and_ids_fail(self):
        mutations=[lambda r:r['scenarios']['retained']['corpora'].pop('C3N'),
                   lambda r:r['scenarios']['retained']['corpora']['C1']['detections'].pop('SV'),
                   lambda r:r['scenarios'].pop('all_seven_stage_only_post_outcome'),
                   lambda r:r['scenarios']['retained']['corpora']['C1'].pop('silent_case_ids')]
        for i,mutation in enumerate(mutations):
            with self.subTest(i=i):
                self.kwargs['out_dir']=self.root/f'fresh-{i}'
                self.reject_output_mutation(mutation,'schema')

    def test_omitted_seventh_case_fails(self):
        self.reject_output_mutation(lambda r:r['scenarios']['all_seven_stage_only_post_outcome']['reclassified_case_ids'].remove('C3-143'),'schema')

    def test_c1_only_denominator_update_fails(self):
        def mutate(r):
            r['scenarios']['all_seven_stage_only_post_outcome']['corpora']['C3']=copy.deepcopy(r['scenarios']['single_case_post_outcome']['corpora']['C3'])
        self.reject_output_mutation(mutate,'schema')

    def test_old_single_case_schema_cannot_pass_complete_gate(self):
        historical=self.a.read_json(OLD_REFERENCE)
        self.assertEqual((historical['retained']['n'],historical['protocol_single_case']['n']),(22,23))
        self.kwargs['reference_json'].write_bytes(self.a.encoded(historical))
        with self.assertRaisesRegex(ValueError,'schema'):self.run_gate()
        self.assertFalse(self.kwargs['out_dir'].exists())

    def test_changed_original_prediction_even_with_updated_digest_fails(self):
        def mutate(r):
            row=next(x for x in r['original_failure_predictions'] if x['case_id']=='robust_bdda1fa')
            row['broken']['ECM']['state']='accept'
            h=self.a.digest(self.a.encoded(r['original_failure_predictions']))
            r['original_predictions_sha256']=h
            for s in r['scenarios'].values():s['unchanged_predictions_sha256']=h
        self.reject_output_mutation(mutate,'schema')

    def test_bool_int_and_int_float_count_confusion_fails(self):
        for i,value in enumerate([True,1.0,'1']):
            with self.subTest(value=value):
                self.kwargs['out_dir']=self.root/f'fresh-{i}'
                self.reject_output_mutation(lambda r:r['scenarios']['single_case_post_outcome']['corpora']['C1']['detections']['ECM'].__setitem__('count',value),'schema')

    def test_missing_input_pin_in_report_fails(self):
        self.reject_output_mutation(lambda r:r['input_sha256'].pop(next(iter(r['input_sha256']))),'schema')

    def test_wrong_case_id_with_correct_count_fails(self):
        self.reject_output_mutation(lambda r:r['scenarios']['single_case_post_outcome']['corpora']['C1']['detections']['ECM'].__setitem__('case_ids',['robust_fc95a19']),'schema')

    def test_tex_mismatch_fails_even_with_correct_output_hash(self):
        original=gate._write_generated
        def corrupt(a,source,out):
            original(a,source,out)
            tex=out/'loudness-sensitivity.tex';tex.write_text(tex.read_text().replace('C3 & 31','C3 & 26'))
            self.refresh_output_hashes(out)
        with mock.patch.object(gate,'_write_generated',corrupt):
            with self.assertRaisesRegex(ValueError,'TeX differs'):self.run_gate()

    def test_reference_tex_mismatch_fails_before_generation(self):
        self.kwargs['reference_tex'].write_text('inherited wrong table')
        with self.assertRaisesRegex(ValueError,'reference TeX'):self.run_gate()
        self.assertFalse(self.kwargs['out_dir'].exists())

    def test_summary_boolean_count_fails(self):
        original=gate._write_generated
        def corrupt(a,source,out):
            original(a,source,out);p=out/'summary.json';d=a.read_json(p);d['failure_count']=True;p.write_bytes(a.encoded(d));self.refresh_output_hashes(out)
        with mock.patch.object(gate,'_write_generated',corrupt):
            with self.assertRaisesRegex(ValueError,'summary schema'):self.run_gate()

    def test_hash_manifest_missing_key_fails(self):
        original=gate._write_generated
        def corrupt(a,source,out):
            original(a,source,out);p=out/'output-sha256.json';d=a.read_json(p);d.pop('summary.json');p.write_bytes(a.encoded(d))
        with mock.patch.object(gate,'_write_generated',corrupt):
            with self.assertRaisesRegex(ValueError,'hash manifest'):self.run_gate()

    def test_symlink_to_inherited_report_fails(self):
        original=gate._write_generated
        def symlink(a,source,out):
            original(a,source,out);p=out/'loudness-analysis.json';p.unlink();p.symlink_to(self.kwargs['reference_json'])
        with mock.patch.object(gate,'_write_generated',symlink):
            with self.assertRaisesRegex(ValueError,'symlinks'):self.run_gate()

    def test_duplicate_json_keys_fails(self):
        original=gate._write_generated
        def corrupt(a,source,out):
            original(a,source,out);p=out/'loudness-analysis.json';p.write_text('{"failure_count":93,"failure_count":92}')
            self.refresh_output_hashes(out)
        with mock.patch.object(gate,'_write_generated',corrupt):
            with self.assertRaisesRegex(ValueError,'duplicate'):self.run_gate()

    def test_source_prediction_file_mutation_fails_pin_verification(self):
        source=self.copy_source();p=source/'scores_adjudicated/robust_bdda1fa.json'
        d=self.a.read_json(p);d['broken']['ECM']['state']='accept';p.write_bytes(self.a.encoded(d))
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.run_gate(source_dir=source)

    def test_source_spec_file_missing_fails(self):
        source=self.copy_source();(source/'specs/C3-143.json').unlink()
        with self.assertRaisesRegex(ValueError,'missing pinned'):self.run_gate(source_dir=source)

    def test_source_changed_during_generation_fails(self):
        source=self.copy_source();original=gate._write_generated
        def change(a,data,out):
            original(a,data,out)
            p=source/'specs/C3-143.json';p.write_bytes(p.read_bytes()+b' ')
        with mock.patch.object(gate,'_write_generated',change):
            with self.assertRaisesRegex(ValueError,'hash mismatch'):self.run_gate(source_dir=source)

    def test_portable_explicit_paths_do_not_use_analyzer_default(self):
        source=self.copy_source();analyzer=self.root/'relocated-analyzer';analyzer.mkdir()
        code=ANALYZER.read_text().replace("DEFAULT_SOURCE = HERE.parent / 'experiments/pathb_v2'", "DEFAULT_SOURCE = Path('/nonexistent/unused/default')")
        self.assertIn("DEFAULT_SOURCE = Path('/nonexistent/unused/default')", code)
        (analyzer/'loudness_analysis.py').write_text(code)
        shutil.copyfile(HERE/'derived_loudness/frozen-input-pins.json',analyzer/'frozen-input-pins.json')
        result=self.run_gate(source_dir=source,analyzer_path=analyzer/'loudness_analysis.py')
        self.assertIs(result['fresh_generation_verified'],True)

    def test_source_tree_output_refused(self):
        with self.assertRaisesRegex(ValueError,'outside source tree'):
            self.run_gate(out_dir=SOURCE/'never-written-output')

    def test_two_fresh_runs_are_byte_reproducible(self):
        self.run_gate();second=self.root/'fresh-2';self.run_gate(out_dir=second)
        for n in gate.EXPECTED_FILES:
            self.assertEqual((self.kwargs['out_dir']/n).read_bytes(),(second/n).read_bytes())


if __name__=='__main__':
    unittest.main(verbosity=2)
