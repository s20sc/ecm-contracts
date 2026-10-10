#!/usr/bin/env python3
"""V24 derived analysis; no scoring, relabelling, or source writes.

Default: read and validate only. --write requires --out, confined to this module
directory. Source files are existing frozen scores/specs; no scorer is imported.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE.parent / 'experiments/pathb_v2'
METHODS = ('ECM', 'NT', 'DI', 'DQ', 'SV')
CORPORA = ('C1', 'C2', 'C3', 'C3N')
SCENARIOS = ('retained', 'single_case_post_outcome', 'all_seven_stage_only_post_outcome')
EXPECTED_SEVEN = frozenset(('robust_bdda1fa', 'robust_fc95a19', 'C3-026', 'C3-048', 'C3-124', 'C3-133', 'C3-143'))
STATES = frozenset(('accept', 'not_supported', 'right_reason', 'unassessable', 'unverified', 'wrong_reason'))
METADATA = {
    'corpus': set(CORPORA), 'operation': {'PAIR', 'UPGRADE', 'CONCURRENT', 'SWITCH'},
    'outcome_class': {'failure', 'warning_only', 'undocumented'},
    'loudness': {'loud_documented', 'silent_documented', 'unknown'},
    'detection_stage': {'build', 'connect', 'activate', 'run', 'unknown'},
}


class Invalid(ValueError):
    """Invalid source, incomplete derived schema, or changed historical outcomes."""


def require(condition, message):
    if not condition:
        raise Invalid(message)


def strict_equal(a, b):
    # JSON serialisation distinguishes True from 1 (unlike Python equality).
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def read_json(path):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            require(k not in result, f'duplicate JSON key: {k}')
            result[k] = v
        return result
    def reject_constant(value):
        raise Invalid(f'non-finite JSON constant: {value}')
    try:
        return json.loads(path.read_bytes(), object_pairs_hook=unique, parse_constant=reject_constant)
    except (OSError, json.JSONDecodeError) as e:
        raise Invalid(f'cannot read JSON {path}: {e}') from e


def validate_records(records):
    require(type(records) is list and len(records) == 126, 'expected exactly 126 score/spec pairs')
    require(sum(r['score'].get('outcome_class') == 'failure' for r in records) == 93,
            'expected exactly 93 scored failures')
    seen = set()
    for pair in records:
        s, p = pair['score'], pair['spec']
        cid = s.get('case_id')
        require(type(cid) is str and cid and cid not in seen, 'missing or duplicate case_id')
        seen.add(cid)
        require(p.get('case_id') == cid, f'{cid}: spec/score case_id mismatch')
        for k, choices in METADATA.items():
            require(type(s.get(k)) is str and s[k] in choices, f'{cid}: invalid or missing {k}')
            require(k in p and strict_equal(s[k], p[k]), f'{cid}: spec/score {k} mismatch')
        require(s.get('assembled_status') in {'done', 'unassessable'}, f'{cid}: invalid assembled status')
        require(s.get('resolution_status') in {'recommended', 'observed', 'none'}, f'{cid}: invalid resolution status')
        require(type(s.get('broken')) is dict and set(s['broken']) == set(METHODS), f'{cid}: missing or novel method')
        require('resolved' in s, f'{cid}: missing resolved outcome field')
        if s['resolved'] is not None:
            require(type(s['resolved']) is dict and set(s['resolved']) == set(METHODS), f'{cid}: invalid resolved methods')
            for m, v in s['resolved'].items():
                require(type(v) is dict and v.get('state') in {'accept', 'reject', 'unassessable'}, f'{cid}/{m}: invalid resolved state')
        for m in METHODS:
            v = s['broken'][m]
            require(type(v) is dict and v.get('state') in STATES, f'{cid}/{m}: invalid state')
            require(type(v.get('findings')) is list, f'{cid}/{m}: missing findings')
            if v['state'] == 'unassessable':
                require(type(v.get('reason')) is str, f'{cid}/{m}: missing unassessable reason')
                require('reject' not in v or type(v['reject']) is bool, f'{cid}/{m}: reject must be boolean')
            else:
                require(type(v.get('reject')) is bool, f'{cid}/{m}: reject must be boolean')
                require(type(v.get('matched')) is list and type(v.get('unevaluable')) is list,
                        f'{cid}/{m}: incomplete score')
        if s['outcome_class'] == 'failure':
            require(type(p.get('loudness_evidence')) is str and p['loudness_evidence'], f'{cid}: missing stored loudness evidence')
    seven = {r['score']['case_id'] for r in records if r['score']['outcome_class'] == 'failure'
             and r['score']['loudness'] == 'loud_documented' and r['score']['detection_stage'] == 'run'}
    require(seven == EXPECTED_SEVEN, 'runtime-loud set must equal all seven expected cases')
    require({r['score']['corpus'] for r in records if r['score']['outcome_class']=='failure'} == set(CORPORA),
            'failure population must cover all four corpora')


def load_source(source=DEFAULT_SOURCE):
    source = Path(source).resolve()
    pin = read_json(HERE / 'frozen-input-pins.json')
    require(set(pin) == {'source_identity', 'files'}, 'invalid pin schema')
    files = {str(p.relative_to(source)): p for folder in ('scores_adjudicated', 'specs')
             for p in (source / folder).glob('*.json')}
    # Specs include excluded/unscored records. Only the specs paired with the
    # exactly pinned scored population are inputs; every score file is required.
    actual_scores = {p for p in files if p.startswith('scores_adjudicated/')}
    expected_scores = {p for p in pin['files'] if p.startswith('scores_adjudicated/')}
    require(actual_scores == expected_scores, 'score population filenames differ from pinned source')
    require(len(expected_scores) == 126 and len(pin['files']) == 252, 'invalid pin population')
    for name, sha in pin['files'].items():
        require(name in files, f'missing pinned input: {name}')
        require(digest(files[name].read_bytes()) == sha, f'input hash mismatch: {name}')
    records = []
    for name in sorted(expected_scores):
        sp = 'specs/' + Path(name).name
        require(sp in pin['files'], f'missing paired spec pin: {name}')
        records.append({'score': read_json(files[name]), 'spec': read_json(files[sp])})
        require(records[-1]['score'].get('case_id') == Path(name).stem, f'filename/case mismatch: {name}')
    validate_records(records)
    # A second pass catches a source changed during this bounded read.
    require(all(digest(files[n].read_bytes()) == h for n,h in pin['files'].items()), 'source changed during read')
    return {'records': records, 'records_sha256':digest(encoded(records)),
            'source_identity': pin['source_identity'], 'input_sha256': pin['files']}


def build_report(source):
    records = source['records']
    validate_records(records)
    require(digest(encoded(records)) == source['records_sha256'], 'loaded source records or predictions were altered')
    # Computation below contains no expected result numerators/denominators.
    before = encoded(records)
    failures = sorted((r for r in records if r['score']['outcome_class'] == 'failure'), key=lambda r:r['score']['case_id'])
    observed_runtime_loud = {r['score']['case_id'] for r in failures
                             if r['score']['loudness']=='loud_documented' and r['score']['detection_stage']=='run'}
    flips = {SCENARIOS[0]: set(), SCENARIOS[1]: {'robust_bdda1fa'}, SCENARIOS[2]: observed_runtime_loud}
    predictions = [{'case_id':r['score']['case_id'], 'broken':copy.deepcopy(r['score']['broken'])} for r in failures]
    prediction_hash = digest(encoded(predictions))
    scenarios = {}
    for name in SCENARIOS:
        corpora = {}
        for corpus in CORPORA:
            pop = [r['score'] for r in failures if r['score']['corpus'] == corpus]
            silent = [r for r in pop if r['loudness'] == 'silent_documented' or r['case_id'] in flips[name]]
            detections = {}
            for method in METHODS:
                ids = sorted(r['case_id'] for r in silent if r['broken'][method]['state'] == 'right_reason')
                detections[method] = {'count': len(ids), 'case_ids':ids}
            corpora[corpus] = {'failure_count':len(pop), 'silent_count':len(silent),
                'silent_case_ids': sorted(r['case_id'] for r in silent), 'detections':detections}
        scenarios[name] = {'post_outcome_reinterpretation': name != SCENARIOS[0],
            'reclassified_case_ids': sorted(flips[name]), 'unchanged_predictions_sha256': prediction_hash, 'corpora':corpora}
    seven_evidence = [{'case_id':r['score']['case_id'], 'corpus':r['score']['corpus'],
        'loudness':r['score']['loudness'], 'detection_stage':r['score']['detection_stage'],
        'stored_loudness_evidence':r['spec']['loudness_evidence'],
        'spec_path':'specs/'+r['score']['case_id']+'.json'} for r in failures if r['score']['case_id'] in EXPECTED_SEVEN]
    report = {'schema':'p5-loudness-derived-v24/1',
        'status':'INSTALLED_DERIVED_ANALYSIS',
        'interpretation':'Retained historical model/adjudication labels; two post-outcome hypothetical stratifications, not new human labels or source ground truth.',
        'source_identity':copy.deepcopy(source['source_identity']), 'input_sha256':copy.deepcopy(source['input_sha256']),
        'source_records_sha256':source['records_sha256'],
        'score_count':len(records), 'failure_count':len(failures), 'methods':list(METHODS), 'corpora':list(CORPORA),
        'original_failure_predictions':predictions, 'original_predictions_sha256':prediction_hash,
        'runtime_loud_stored_evidence':seven_evidence, 'scenarios':scenarios}
    require(encoded(records) == before, 'analysis mutated original records')
    return report


def validate_report(report, source):
    require(type(report) is dict, 'report must be an object')
    expected = build_report(source)
    # Complete equality is a fail-closed schema and source-derived value check:
    # it rejects omitted/extra keys, altered IDs/states/hashes/counts and bool/int
    # substitution without conflating historical single-case evidence with this schema.
    require(strict_equal(report, expected), 'report schema or source-derived values differ from complete expected report')


def tex_table(report):
    labels = ('Retained labels', 'Single-case sensitivity', 'Stage-only (7 cases)')
    out = ['% V24; derived from retained frozen scores; no label changes.',
           r'\begin{tabular}{llrrrrrr}', r'\toprule',
           r'Reading & Corpus & Silent $n$ & ECM & NT & DI & DQ & SV \\', r'\midrule']
    for scenario, label in zip(SCENARIOS, labels):
        for i,corpus in enumerate(CORPORA):
            d=report['scenarios'][scenario]['corpora'][corpus]
            row=[label if i == 0 else '', corpus, str(d['silent_count'])]+[str(d['detections'][m]['count']) for m in METHODS]
            out.append(' & '.join(row)+r' \\')
    out += [r'\bottomrule', r'\end{tabular}',
            '% Counts are right-reason detections in each silent stratum.',
            '% Both sensitivities are post-outcome reinterpretations, not human ground truth.',
            '% Method outcomes and original labels are unchanged. C3N denotes C3-neutral.']
    return '\n'.join(out)+'\n'


def summary(report):
    return {'schema':report['schema'], 'score_count':report['score_count'], 'failure_count':report['failure_count'],
        'ECM_silent':{s:{c: f"{d['detections']['ECM']['count']}/{d['silent_count']}" for c,d in report['scenarios'][s]['corpora'].items()} for s in SCENARIOS},
        'original_predictions_sha256':report['original_predictions_sha256']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--validate-report', type=Path, help='validate a saved complete report against pinned sources')
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--out', type=Path)
    args=parser.parse_args()
    try:
        require(args.write == (args.out is not None), '--write and --out must be supplied together')
        source=load_source(args.source)
        report=build_report(source)
        validate_report(report, source)
        if args.validate_report:
            validate_report(read_json(args.validate_report), source)
        outputs = {'loudness-analysis.json': encoded(report), 'loudness-sensitivity.tex':tex_table(report).encode(),
                   'summary.json':encoded(summary(report))}
        if args.write:
            out=args.out.resolve()
            require(out != HERE and HERE in out.parents, 'outputs must be in a new child directory of this module directory')
            require(not out.exists(), 'output directory already exists; use a new directory')
            out.mkdir(parents=True)
            for name,data in outputs.items():
                (out/name).write_bytes(data)
            (out/'output-sha256.json').write_bytes(encoded({name:digest(data) for name,data in outputs.items()}))
        print(json.dumps(dict(summary(report), wrote_outputs=args.write), ensure_ascii=False, indent=2))
        return 0
    except (Invalid, KeyError, TypeError, OSError, ValueError) as e:
        print('INVALID: '+str(e))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
