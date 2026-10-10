"""Hand-constructed examples, independent of the frozen study data."""
import unittest
from supplementary_binary_metrics import METHODS, calculate, prediction, select_rows


def scores(state='accept'):
    return {m: {'state': state} for m in METHODS}


def row(cid, outcome='failure', broken=None, resolved=None):
    return dict(case_id=cid, corpus='C1', outcome_class=outcome, broken=broken or scores(),
                resolved=resolved, resolution_status='observed', c3_selected=False)


class BinaryMetricsTest(unittest.TestCase):
    def test_hand_calculated_confusion_matrix(self):
        # One wrong-reason TP, one FN, one warning-only FP, one fixed TN.
        data = calculate([row('p', broken=scores('wrong_reason'), resolved=scores()),
                          row('miss'), row('warn', 'warning_only', scores('reject'))])['C1']
        for m in METHODS:
            v = data['methods'][m]
            self.assertEqual([v[k] for k in ('TP','FP','FN','TN')], [1,1,1,1])
            self.assertEqual([v[k] for k in ('precision','recall','f1')], [.5,.5,.5])
            self.assertEqual(v['cells']['TP'], ['p:broken'])
            self.assertEqual(v['cells']['FP'], ['warn:broken'])
            self.assertEqual(v['positive_rejections_by_state']['right_reason'], [])
            self.assertEqual(v['positive_rejections_by_state']['wrong_reason'], ['p:broken'])

    def test_abstention_excluded_from_every_method(self):
        broken = scores('right_reason'); broken['NT'] = {'state': 'unassessable'}
        fixed = scores(); fixed['DI'] = {'state': 'unassessable'}
        data = calculate([row('u', broken=broken, resolved=fixed), row('p', broken=scores('right_reason'))])['C1']
        self.assertEqual(data['excluded_unassessable_n'], 2)
        self.assertEqual(data['complete_case_n'], 1)
        for m in METHODS:
            self.assertEqual(data['methods'][m]['TP'], 1)
            self.assertEqual(data['methods'][m]['TN'], 0)

    def test_no_predictions_has_undefined_precision_but_zero_f1(self):
        v = calculate([row('miss')])['C1']['methods']['ECM']
        self.assertIsNone(v['precision']); self.assertEqual(v['recall'], 0); self.assertEqual(v['f1'], 0)

    def test_empty_population_all_metrics_undefined(self):
        v = calculate([])['C1']['methods']['ECM']
        for k in ('precision','recall','f1'):
            self.assertIsNone(v[k])

    def test_no_actual_positives_with_false_positive_f1_is_zero(self):
        v = calculate([row('warn', 'warning_only', scores('reject'))])['C1']['methods']['ECM']
        self.assertEqual(v['precision'], 0); self.assertIsNone(v['recall']); self.assertEqual(v['f1'], 0)

    def test_not_supported_is_not_automatic_acceptance(self):
        self.assertFalse(prediction({'state':'not_supported','reject':False,'findings':[]}))
        self.assertTrue(prediction({'state':'not_supported','reject':True,'findings':[{'rule':'x'}]}))
        self.assertTrue(prediction({'state':'not_supported','findings':[{'rule':'x'}]}))

    def test_rejection_flag_inconsistency_fails(self):
        with self.assertRaises(ValueError):
            prediction({'state':'right_reason','reject':False})

    def test_recommended_and_undocumented_are_not_controls(self):
        a = row('a', 'undocumented', resolved=scores()); a['resolution_status'] = 'recommended'
        self.assertEqual(calculate([a])['C1']['candidate_n'], 0)

    def test_selection_drops_stale_pilot_and_unselected_failures(self):
        rows = [row('pilot'), row('ok'), row('late'), row('unselected'), row('ineligible')]
        specs = {r['case_id']: dict(r, eligible=r['case_id']!='ineligible') for r in rows}
        for cid in ('late','unselected'):
            specs[cid]['corpus'] = 'C3'
        selected, excluded = select_rows(rows, specs, {'pilot'}, {'selected':[], 'capped':[], 'after_stop':['late']})
        self.assertEqual([r['case_id'] for r in selected], ['ok'])
        self.assertEqual(excluded, dict(pilot='quarantined_pilot', late='outside_c3_stop_rule',
            unselected='c3_failure_not_selected', ineligible='ineligible_under_adjudicated_spec'))

    def test_selection_missing_eligible_score_fails(self):
        with self.assertRaises(ValueError):
            select_rows([], {'ok':dict(row('ok'), eligible=True)}, set(), dict(selected=[], capped=[], after_stop=[]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
