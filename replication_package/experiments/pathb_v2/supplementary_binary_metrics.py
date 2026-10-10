"""Post-hoc binary case-control analysis; never changes the frozen primary scorer.

Run: python3 supplementary_binary_metrics.py --tex /absolute/path/binary_casecontrol.tex
The unit is a composition, identified as case_id:broken or case_id:resolved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
METHODS = ('ECM', 'NT', 'DI', 'DQ', 'SV')
CORPORA = ('C1', 'C2', 'C3', 'C3N')
REJECTION_STATES = {'right_reason', 'wrong_reason', 'unverified', 'reject'}
KNOWN_STATES = REJECTION_STATES | {'accept', 'not_supported', 'unassessable'}


def prediction(score):
    """None is abstention. Any actual rejection is positive, regardless of its cause."""
    state = score['state']
    if state not in KNOWN_STATES:
        raise ValueError(f'Unknown state: {state}')
    if state == 'unassessable':
        return None
    if 'reject' in score:
        if not isinstance(score['reject'], bool):
            raise ValueError('reject must be a boolean')
        rejected = score['reject']
        if state in REJECTION_STATES and not rejected:
            raise ValueError('Rejection state contradicts reject=false')
        if 'findings' in score and bool(score['findings']) != rejected:
            raise ValueError('Findings contradict rejection flag')
        return rejected
    if state in REJECTION_STATES:
        return True
    # not_supported is a negative prediction only when no finding exists;
    # SWITCH can retain findings despite being labelled not_supported.
    return bool(score.get('findings'))


def select_rows(scores, specs, pilot, selection):
    """Match scorer eligibility/stop rule, then report_extra's selected-failure restriction."""
    selected = set(selection['selected'])
    stopped = set(selection['capped']) | set(selection['after_stop'])
    expected = {
        cid for cid, s in specs.items()
        if s.get('eligible') and cid not in pilot and s['corpus'] in CORPORA
        and not (s['corpus'] == 'C3' and cid in stopped)
        and not (s['corpus'] == 'C3' and s['outcome_class'] == 'failure' and cid not in selected)
    }
    included, excluded, seen = [], {}, set()
    for r in scores:
        cid = r['case_id']
        if cid in seen:
            raise ValueError(f'Duplicate score: {cid}')
        seen.add(cid)
        if cid in pilot:
            reason = 'quarantined_pilot'
        elif cid not in specs:
            raise ValueError(f'Score has no specification: {cid}')
        elif not specs[cid].get('eligible'):
            reason = 'ineligible_under_adjudicated_spec'
        elif specs[cid]['corpus'] == 'C3' and cid in stopped:
            reason = 'outside_c3_stop_rule'
        elif specs[cid]['corpus'] == 'C3' and specs[cid]['outcome_class'] == 'failure' and cid not in selected:
            reason = 'c3_failure_not_selected'
        elif specs[cid]['corpus'] not in CORPORA:
            reason = 'outside_reported_corpora'
        else:
            spec = specs[cid]
            for key in ('corpus', 'outcome_class'):
                if r[key] != spec[key]:
                    raise ValueError(f'Stale {key} in score: {cid}')
            if r.get('c3_selected') != (cid in selected):
                raise ValueError(f'Stale selection flag: {cid}')
            included.append(r)
            continue
        excluded[cid] = reason
    got = {r['case_id'] for r in included}
    if got != expected:
        raise ValueError(f'Population mismatch: missing={sorted(expected-got)}, extra={sorted(got-expected)}')
    return sorted(included, key=lambda r: r['case_id']), excluded


def calculate(rows):
    result = {}
    for corpus in CORPORA:
        candidates, excluded, observations = [], [], []
        for r in rows:
            if r['corpus'] != corpus:
                continue
            units = []
            if r['outcome_class'] == 'failure':
                units.append(('broken', True, 'documented_failure'))
            elif r['outcome_class'] == 'warning_only':
                units.append(('broken', False, 'warning_only'))
            if r.get('resolved') and r['resolution_status'] == 'observed':
                units.append(('resolved', False, 'observed_fixed'))
            for composition, truth, source in units:
                scores = r[composition]
                if any(m not in scores for m in METHODS):
                    raise ValueError(f'Missing method in {r["case_id"]}:{composition}')
                obs = dict(id=f'{r["case_id"]}:{composition}', case_id=r['case_id'],
                           composition=composition, positive=truth, source=source,
                           states={m: scores[m]['state'] for m in METHODS},
                           predictions={m: prediction(scores[m]) for m in METHODS})
                candidates.append(obs)
                abstaining = [m for m in METHODS if obs['predictions'][m] is None]
                if abstaining:
                    excluded.append(dict(obs, abstaining_methods=abstaining))
                else:
                    observations.append(obs)
        count = lambda pool, positive: sum(o['positive'] == positive for o in pool)
        data = dict(candidate_n=len(candidates), candidate_positive_n=count(candidates, True),
                    candidate_negative_n=count(candidates, False), complete_case_n=len(observations),
                    positive_n=count(observations, True), negative_n=count(observations, False),
                    excluded_unassessable_n=len(excluded), excluded_unassessable=excluded,
                    negative_sources={s: sum(o['source'] == s for o in observations)
                                      for s in ('observed_fixed', 'warning_only')},
                    observations=observations, methods={})
        for method in METHODS:
            cells = {k: [] for k in ('TP', 'FP', 'FN', 'TN')}
            for o in observations:
                key = ('TP' if o['predictions'][method] else 'FN') if o['positive'] else (
                    'FP' if o['predictions'][method] else 'TN')
                cells[key].append(o['id'])
            tp, fp, fn, tn = (len(cells[k]) for k in ('TP', 'FP', 'FN', 'TN'))
            ratio = lambda n, d: n / d if d else None
            data['methods'][method] = dict(
                TP=tp, FP=fp, FN=fn, TN=tn,
                precision=ratio(tp, tp+fp), recall=ratio(tp, tp+fn), f1=ratio(2*tp, 2*tp+fp+fn),
                denominators=dict(precision=tp+fp, recall=tp+fn, f1=2*tp+fp+fn), cells=cells,
                positive_rejections_by_state={state: [o['id'] for o in observations if o['positive']
                    and o['predictions'][method] and o['states'][method] == state]
                    for state in sorted(REJECTION_STATES | {'not_supported'})},
                no_finding_not_supported=[o['id'] for o in observations
                    if o['states'][method] == 'not_supported' and not o['predictions'][method]])
        result[corpus] = data
    return result


def latex_table(report):
    lines = [r'\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}llrrrrrrr@{}}', r'\toprule',
             r'Corpus & Method & TP & FP & FN & TN & P & R & F1 \\', r'\midrule']
    fmt = lambda v: '--' if v is None else f'{v:.3f}'
    for i, corpus in enumerate(CORPORA):
        if i:
            lines.append(r'\addlinespace')
        for method in METHODS:
            v = report['by_corpus'][corpus]['methods'][method]
            lines.append(' & '.join([corpus, method] + [str(v[k]) for k in ('TP','FP','FN','TN')]
                                    + [fmt(v[k]) for k in ('precision','recall','f1')]) + r' \\')
    return '\n'.join(lines + [r'\bottomrule', r'\end{tabular*}', ''])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tex', type=Path, required=True)
    args = parser.parse_args()
    import scoring as S  # read-only calls; never invoke checker or main/write
    results_path = HERE / 'results_adjudicated.json'
    results = json.loads(results_path.read_text())
    pilot_path = HERE / 'pilot/PILOT_CASES.json'
    pilot = set(json.loads(pilot_path.read_text())['quarantined_pilot_cases'])
    specs = S.load_specs(True)
    selection = S.c3_selection(S.load_specs(False))
    if selection != results['c3_selection']:
        raise ValueError('Current frozen selection disagrees with results_adjudicated.json')
    paths = sorted((HERE / 'scores_adjudicated').glob('*.json'))
    rows, excluded = select_rows([json.loads(p.read_text()) for p in paths], specs, pilot, selection)
    if S.by_corpus(rows) != results['by_corpus']:
        raise ValueError('Selected score population does not reproduce primary and complete-case aggregates')
    source_paths = paths + [results_path, pilot_path, HERE / 'adjudicated/overrides.json']
    source_paths += sorted((HERE / 'specs').glob('*.json'))
    report = dict(analysis='post-hoc supplementary binary case-control; not primary right-reason analysis',
        definitions=dict(unit='composition; case_id:broken or case_id:resolved',
            positive='documented-failure broken composition',
            negative='observed-fixed resolved composition plus warning-only broken composition',
            prediction='actual reject flag, otherwise rejection state or nonempty findings; cause irrelevant',
            not_supported='no finding means negative prediction, not an abstention; retained rejection/finding means positive',
            complete_case='exclude a composition from every method if any method is unassessable',
            undefined='null iff the corresponding ratio denominator is zero',
            inference='artificial case-control prevalence, not deployed precision; compositions from one case may be dependent'),
        population_verification=dict(aggregate_reproduced=True, included_cases=[r['case_id'] for r in rows],
            excluded_score_files=excluded, quarantined_pilot=sorted(pilot)),
        source_sha256={str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
        by_corpus=calculate(rows))
    dest = HERE / 'report/binary_metrics.json'
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    args.tex.parent.mkdir(parents=True, exist_ok=True)
    args.tex.write_text(latex_table(report))
    for c, data in report['by_corpus'].items():
        print(c, f'complete={data["complete_case_n"]}, positive={data["positive_n"]}, negative={data["negative_n"]}, excluded={data["excluded_unassessable_n"]}')
        for m, v in data['methods'].items():
            print(' ', m, {k:v[k] for k in ('TP','FP','FN','TN','precision','recall','f1')})
    print(f'Excluded score files: {excluded}')
    print(f'Wrote {dest}\nWrote {args.tex}')


if __name__ == '__main__':
    main()
