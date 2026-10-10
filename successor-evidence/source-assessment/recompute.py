"""Verify the dated evidence supplement and recompute its exclusion reading.

No source judgment is inferred from agreement or successful computation.
Run with --package /path/to/replication_package --out /new/result.json.
The primary scores and every historical finding remain read-only.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    base = args.package.resolve() / 'experiments/pathb_v2'
    out = args.out.resolve()
    if out.exists() or out.is_relative_to(args.package.resolve()) or out.is_relative_to(here):
        raise ValueError('Output must be a new file outside the package and evidence trees')
    pins = {}

    def portable(path):
        path = path.resolve()
        if path.is_relative_to(here):
            return 'evidence/' + path.relative_to(here).as_posix()
        if path.is_relative_to(args.package.resolve()):
            return 'package/' + path.relative_to(args.package.resolve()).as_posix()
        raise ValueError('Unrecognized input root')

    # This inventory is the current publication representation, not a historical freeze.
    inventory_path = here / 'EVIDENCE_FILES.json'
    inventory = json.loads(inventory_path.read_text())
    expected = inventory['files']
    actual = {p.relative_to(here).as_posix() for p in here.rglob('*') if p.is_file()}
    if actual != set(expected) | {'EVIDENCE_FILES.json'}:
        raise ValueError('Evidence inventory mismatch')
    pins[str(inventory_path)] = hashlib.sha256(inventory_path.read_bytes()).hexdigest()
    for relative, digest in expected.items():
        path = (here / relative).resolve(strict=True)
        if not path.is_relative_to(here) or not path.is_file():
            raise ValueError('Evidence inventory path escapes input root')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Evidence inventory hash mismatch: ' + relative)
        pins[str(path)] = digest

    def read(path):
        path = path.resolve(strict=True)
        data = path.read_bytes()
        pins[str(path)] = hashlib.sha256(data).hexdigest()
        return json.loads(data)

    review = read(here / 'control-source-review.json')
    census = read(here / 'control-census.json')
    source_map = read(here / 'source-map.json')
    for relative, source in source_map.items():
        path = (here / relative).resolve(strict=True)
        if not path.is_relative_to(here):
            raise ValueError('Source path escapes the evidence directory')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != source['sha256']:
            raise ValueError('Source hash mismatch: ' + relative)
        pins[str(path)] = digest
    gaps = {(x['case_id'], x['element']) for x in census['gaps']}
    items = review['items']
    if len(items) != 7 or len({x['item_id'] for x in items}) != 7:
        raise ValueError('Expected exactly seven unique supplementary items')
    if {(x['case_id'], x['element']) for x in items} != gaps:
        raise ValueError('Supplementary items do not match the census gaps')
    for item in items:
        expected_paths = {f"ver_delta.changed_fields[{item['element']}]",
                          f"ver_delta.consumer_reads[{item['element']}]"}
        if (not item['review_complete'] or not item['evidence']
                or len(item['trigger_paths']) != 2
                or set(item['trigger_paths']) != expected_paths):
            raise ValueError('Incomplete review record')
        for anchor in item['evidence']:
            path = (here / anchor['path']).resolve(strict=True)
            if not path.is_relative_to(here):
                raise ValueError('Quote source escapes evidence directory')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != anchor['sha256']:
                raise ValueError('Quote-source hash mismatch')
            lines = path.read_text().splitlines()
            lo, hi = anchor['start_line'], anchor['end_line']
            if not 1 <= lo <= hi <= len(lines):
                raise ValueError('Invalid source line range')
            if '\n'.join(lines[lo - 1:hi]) != anchor['quote']:
                raise ValueError('Nonverbatim quote: ' + item['item_id'])

    late = read(here / 'retained-boundary-replay.json')
    late_rows = late['rows']
    ids = [x['case_id'] for x in late_rows]
    if len(ids) != 7 or len(set(ids)) != 7:
        raise ValueError('Expected seven unique boundary candidates')
    failures = [x for x in late_rows if x['outcome_class'] == 'failure']
    undocumented = [x for x in late_rows if x['outcome_class'] == 'undocumented']
    states = {}
    for row in late_rows:
        methods = row['broken']
        expected_methods = {'ECM', 'NT', 'DI', 'DQ', 'SV'}
        legal_states = {'accept', 'right_reason', 'wrong_reason', 'unverified',
                        'unassessable', 'not_supported'}
        if set(methods) != expected_methods or any(
                v.get('state') not in legal_states for v in methods.values()):
            raise ValueError('Incomplete or invalid boundary method states')
        states[row['case_id']] = {k: v['state'] for k, v in methods.items()}

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(base))
    scoring = importlib.import_module('scoring')
    if Path(scoring.__file__).resolve() != (base / 'scoring.py').resolve():
        raise ValueError('Unexpected scoring module')
    module_pins = {}
    for module in list(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename and Path(filename).resolve().is_relative_to(args.package.resolve()):
            path = Path(filename).resolve()
            if path.is_file():
                module_pins[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    scores = [read(p) for p in sorted((base / 'scores_adjudicated').glob('*.json'))]
    if len(scores) != 126 or len({x['case_id'] for x in scores}) != 126:
        raise ValueError('Unexpected original cohort')
    original = read(base / 'results_adjudicated.json')
    if scoring.by_corpus(scores) != original['by_corpus'] or scoring.h1_record(scores) != original['H1']:
        raise ValueError('Original aggregate reproduction failed')
    decision = read(here / 'joint-eligibility.json')
    if decision['record_ids'] != ['C3-057', 'C3N-001'] or decision['eligibility'] != 'unconfirmed':
        raise ValueError('Unexpected joint eligibility decision')
    if sum(x['case_id'] == 'C3-057' for x in scores) != 1 or any(x['case_id'] == 'C3N-001' for x in scores):
        raise ValueError('Unexpected source-group counting')
    reduced = [x for x in scores if x['case_id'] != 'C3-057']
    result = {
        'scope': 'Post hoc evidence completion and common eligibility-uncertainty exclusion; not a replacement of historical primary inputs',
        'control_review': {'original_covered': census['coverage_summary']['covered_findings'],
                           'original_findings': census['total_actual_findings'],
                           'supplementary_reviewed': len(items),
                           'semantic_indeterminate': sum(x['substance'] == 'indeterminate' for x in items),
                           'all_actual_rejections_retained': True},
        'boundary': {'candidate_ids': ids, 'source_reported_failures': [x['case_id'] for x in failures],
                     'undocumented_outcomes': [x['case_id'] for x in undocumented], 'retained_method_states': states,
                     'performance_fully_identified': False},
        'original_reaggregation_matches': True,
        'exclusion': {'excluded': ['C3-057'], 'replacement': False, 'rows': len(reduced),
                      'all': scoring.aggregate(reduced), 'by_corpus': scoring.by_corpus(reduced),
                      'H1': scoring.h1_record(reduced)},
        'input_sha256': {portable(Path(k)): v for k, v in pins.items()},
        'loaded_scientific_modules_sha256': {portable(Path(k)): v for k, v in module_pins.items()},
    }
    for path, digest in {**pins, **module_pins}.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError('Input changed during analysis: ' + path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print('Verified quotes, seven control reviews, seven boundary records and unchanged primary reaggregation.')
    print('Exclusion reading:', result['exclusion']['all']['methods']['ECM']['right_reason'])


if __name__ == '__main__':
    main()
