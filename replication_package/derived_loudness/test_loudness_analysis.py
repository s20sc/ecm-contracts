"""Bounded positive and mutation probes. No scorer, models or network.

Run: python3 -B -m unittest -v test_loudness_analysis.py
"""
import copy
import hashlib
import json
import subprocess
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import loudness_analysis as la


class LoudnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = la.load_source()
        cls.report = la.build_report(cls.source)

    def mutated_report_rejected(self, mutation):
        report = copy.deepcopy(self.report)
        mutation(report)
        with self.assertRaises(la.Invalid):
            la.validate_report(report, self.source)

    def records(self):
        return copy.deepcopy(self.source['records'])

    def case(self, records, cid):
        return next(r for r in records if r['score']['case_id'] == cid)

    def call(self, *args, script=None):
        script = script or la.HERE/'loudness_analysis.py'
        return subprocess.run([sys.executable, '-B', str(script), *map(str,args)],
                              capture_output=True, text=True)

    def test_valid_report_and_known_external_enumeration(self):
        la.validate_report(self.report,self.source)
        # Independent expected results from the prior all-93 enumeration. These
        # fixtures are tests only, never computation constants in the generator.
        expected = [(22,0,26,1), (23,1,26,1), (24,1,31,1)]
        for name, values in zip(la.SCENARIOS,expected):
            c=self.report['scenarios'][name]['corpora']
            self.assertEqual((c['C1']['silent_count'],c['C1']['detections']['ECM']['count'],
                              c['C3']['silent_count'],c['C3']['detections']['ECM']['count']),values)
            self.assertEqual(set(c),set(la.CORPORA))
            for corpus in la.CORPORA:
                self.assertEqual(set(c[corpus]['detections']),set(la.METHODS))
                self.assertEqual(len(c[corpus]['silent_case_ids']),c[corpus]['silent_count'])
                for m in la.METHODS:
                    self.assertEqual(c[corpus]['detections'][m]['count'],len(c[corpus]['detections'][m]['case_ids']))

    def test_seventh_case_omitted_from_source_set_fails(self):
        rows=self.records()
        r=self.case(rows,'C3-143')
        r['score']['loudness']=r['spec']['loudness']='silent_documented'
        with self.assertRaisesRegex(la.Invalid,'all seven'):
            la.validate_records(rows)

    def test_seventh_case_omitted_from_report_fails(self):
        self.mutated_report_rejected(lambda r:r['scenarios'][la.SCENARIOS[2]]['reclassified_case_ids'].remove('C3-143'))

    def test_population_125_instead_of_126_fails(self):
        with self.assertRaisesRegex(la.Invalid,'126'):
            la.validate_records(self.records()[:-1])

    def test_failure_population_92_instead_of_93_fails(self):
        rows=self.records();r=self.case(rows,'C3-143')
        r['score']['outcome_class']=r['spec']['outcome_class']='warning_only'
        with self.assertRaisesRegex(la.Invalid,'93'):
            la.validate_records(rows)

    def test_spec_score_metadata_mismatch_fails(self):
        for key,value in [('corpus','C1'),('operation','UPGRADE'),('loudness','silent_documented'),('detection_stage','build')]:
            with self.subTest(key=key):
                rows=self.records();self.case(rows,'C3-143')['spec'][key]=value
                with self.assertRaisesRegex(la.Invalid,'mismatch'):
                    la.validate_records(rows)

    def test_novel_or_unknown_method_state_fails(self):
        for state in ['UNKNOWN','unknown','rejected',None,1,True]:
            with self.subTest(state=state):
                rows=self.records();self.case(rows,'robust_bdda1fa')['score']['broken']['ECM']['state']=state
                with self.assertRaises(la.Invalid):la.validate_records(rows)

    def test_unknown_assembly_status_fails(self):
        rows=self.records();self.case(rows,'C3-143')['score']['assembled_status']='unknown'
        with self.assertRaises(la.Invalid):la.validate_records(rows)

    def test_unknown_resolved_status_fails(self):
        rows=self.records();self.case(rows,'robust_bdda1fa')['score']['resolved']['ECM']['state']='unknown'
        with self.assertRaises(la.Invalid):la.validate_records(rows)

    def test_missing_method_in_source_fails(self):
        rows=self.records();del self.case(rows,'C3-143')['score']['broken']['SV']
        with self.assertRaises(la.Invalid):la.validate_records(rows)

    def test_c1_only_report_fails(self):
        def mutate(r):
            for s in la.SCENARIOS:
                r['scenarios'][s]['corpora']={'C1':r['scenarios'][s]['corpora']['C1']}
        self.mutated_report_rejected(mutate)

    def test_c1_only_denominator_recomputation_fails(self):
        def mutate(r):
            # C1 uses all-seven reading, but C3 mistakenly retains single-case.
            r['scenarios'][la.SCENARIOS[2]]['corpora']['C3']=copy.deepcopy(r['scenarios'][la.SCENARIOS[1]]['corpora']['C3'])
        self.mutated_report_rejected(mutate)

    def test_prediction_changed_in_report_fails(self):
        def mutate(r):
            row=next(x for x in r['original_failure_predictions'] if x['case_id']=='robust_bdda1fa')
            row['broken']['ECM']['state']='accept'
        self.mutated_report_rejected(mutate)

    def test_prediction_changed_after_load_fails(self):
        source=copy.deepcopy(self.source)
        self.case(source['records'],'robust_bdda1fa')['score']['broken']['ECM']['state']='accept'
        with self.assertRaisesRegex(la.Invalid,'altered'):la.build_report(source)

    def test_source_reject_bool_cannot_be_integer(self):
        rows=self.records();self.case(rows,'robust_bdda1fa')['score']['broken']['ECM']['reject']=1
        with self.assertRaisesRegex(la.Invalid,'boolean'):la.validate_records(rows)

    def test_report_one_count_cannot_be_true(self):
        self.mutated_report_rejected(lambda r:r['scenarios'][la.SCENARIOS[2]]['corpora']['C1']['detections']['ECM'].__setitem__('count',True))

    def test_report_flag_cannot_be_integer(self):
        self.mutated_report_rejected(lambda r:r['scenarios'][la.SCENARIOS[2]].__setitem__('post_outcome_reinterpretation',1))

    def test_malformed_counts_fail(self):
        for value in [-1,'24',24.0,None,25]:
            with self.subTest(value=value):
                self.mutated_report_rejected(lambda r:r['scenarios'][la.SCENARIOS[2]]['corpora']['C1'].__setitem__('silent_count',value))

    def test_missing_keys_fail(self):
        for kind in ['methods','input_hash','detection_ids','scenario']:
            with self.subTest(kind=kind):
                def mutate(r):
                    if kind=='methods':del r['scenarios'][la.SCENARIOS[2]]['corpora']['C1']['detections']['NT']
                    elif kind=='input_hash':del r['input_sha256'][next(iter(r['input_sha256']))]
                    elif kind=='detection_ids':del r['scenarios'][la.SCENARIOS[2]]['corpora']['C1']['detections']['ECM']['case_ids']
                    else:del r['scenarios'][la.SCENARIOS[2]]
                self.mutated_report_rejected(mutate)

    def test_correct_count_but_wrong_id_fails(self):
        self.mutated_report_rejected(lambda r:r['scenarios'][la.SCENARIOS[2]]['corpora']['C1']['detections']['ECM'].__setitem__('case_ids',['robust_fc95a19']))

    def test_historical_single_case_evidence_not_complete_new_schema(self):
        historical=la.read_json(la.DEFAULT_SOURCE.parents[1]/'evidence/loudness_single_case.json')
        # Rejection means schema incompleteness, not refutation of this valid
        # historical C1-only single-case sensitivity.
        self.assertEqual(historical['retained']['n'],22)
        self.assertEqual(historical['protocol_single_case']['n'],23)
        with self.assertRaisesRegex(la.Invalid,'schema'):la.validate_report(historical,self.source)

    def test_no_records_mutated_and_deterministic_bytes(self):
        before=la.encoded(self.source)
        a=la.build_report(self.source);b=la.build_report(self.source)
        self.assertEqual(la.encoded(a),la.encoded(b))
        self.assertEqual(la.tex_table(a),la.tex_table(b))
        self.assertEqual(la.encoded(self.source),before)

    def test_default_cli_writes_nothing(self):
        def snapshot():
            return {str(p.relative_to(la.HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in la.HERE.rglob('*') if p.is_file()}
        before=snapshot();result=self.call();after=snapshot()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse(json.loads(result.stdout)['wrote_outputs'])
        self.assertEqual(before,after)

    def test_write_requires_both_flags_and_new_scratch_child(self):
        for args in [('--write',),('--out',la.HERE/'never-written'),('--write','--out',la.DEFAULT_SOURCE),('--write','--out',la.HERE)]:
            with self.subTest(args=args):
                result=self.call(*args)
                self.assertEqual(result.returncode,2,result.stdout+result.stderr)

    def test_explicit_write_roundtrip_and_overwrite_refused(self):
        with tempfile.TemporaryDirectory(prefix='probe-') as t:
            # Exercise the unmodified CLI in a private module copy, keeping
            # its module-child output boundary and the frozen inputs intact.
            module=Path(t)/'analyzer';module.mkdir()
            for name in ('loudness_analysis.py','frozen-input-pins.json'):
                shutil.copyfile(la.HERE/name,module/name)
            script=module/'loudness_analysis.py'
            out=module/'fresh'
            result=self.call('--source',la.DEFAULT_SOURCE,'--write','--out',out,script=script)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            la.validate_report(la.read_json(out/'loudness-analysis.json'),self.source)
            hashes=la.read_json(out/'output-sha256.json')
            self.assertEqual(set(hashes),{'loudness-analysis.json','loudness-sensitivity.tex','summary.json'})
            for name,h in hashes.items():self.assertEqual(la.digest((out/name).read_bytes()),h)
            self.assertEqual(self.call('--source',la.DEFAULT_SOURCE,'--write','--out',out,script=script).returncode,2)
            escaped=Path(t)/'outside-module'
            self.assertEqual(self.call('--source',la.DEFAULT_SOURCE,'--write','--out',escaped,script=script).returncode,2)
            self.assertFalse(escaped.exists())

    def test_input_hash_rejects_valid_json_prediction_mutation(self):
        with tempfile.TemporaryDirectory(prefix='probe-') as t:
            root=Path(t)
            # Local copy only; mutations never touch frozen input files.
            for name in self.source['input_sha256']:
                dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes((la.DEFAULT_SOURCE/name).read_bytes())
            p=root/'scores_adjudicated/robust_bdda1fa.json'
            r=la.read_json(p);r['broken']['ECM']['state']='accept';p.write_bytes(la.encoded(r))
            with self.assertRaisesRegex(la.Invalid,'hash mismatch'):la.load_source(root)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory(prefix='probe-') as t:
            p=Path(t)/'bad.json';p.write_text('{"count": 1, "count": 2}')
            with self.assertRaisesRegex(la.Invalid,'duplicate'):la.read_json(p)


if __name__=='__main__':
    unittest.main(verbosity=2)
