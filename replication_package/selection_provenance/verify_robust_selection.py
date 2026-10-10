"""Reconstruct C1 selection from pinned upstream records, without changing inputs.

This is a present-day reconstruction, not a certificate of historical blinding.
Supply the exact public upstream tarball with --archive. No network is used.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import runpy
import tarfile

import yaml


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive', type=Path, required=True)
    ap.add_argument('--selected', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    package = here.parent
    lock = json.loads((here / 'selection-lock.json').read_text())
    selector = package / 'experiments/pathb/extract_robust.py'
    if hashlib.sha256(selector.read_bytes()).hexdigest() != lock['selector_sha256']:
        raise SystemExit('FAIL: historical selector hash mismatch')
    blob = args.archive.read_bytes()
    if hashlib.sha256(blob).hexdigest() != lock['archive_sha256']:
        raise SystemExit('FAIL: upstream archive hash mismatch')
    funcs = runpy.run_path(str(selector))
    selected = args.selected or package / 'experiments/pathb/robust_cases.json'
    retained = json.loads(selected.read_text())
    if not isinstance(retained, list):
        raise SystemExit('FAIL: retained input is not a list')
    expected = {r['case_id']: r for r in retained}
    if len(expected) != len(retained):
        raise SystemExit('FAIL: duplicate retained case ID')
    seen, reconstructed, fallbacks = {}, {}, []
    pins = {r['path']: r['sha256'] for r in lock['upstream_records']}
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz') as tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith('.bug'):
                continue
            rel = str(Path(*Path(member.name).parts[1:]))
            if rel in seen or rel not in pins:
                raise SystemExit('FAIL: duplicate or unexpected upstream record')
            raw = tar.extractfile(member).read()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != pins[rel]:
                raise SystemExit('FAIL: upstream record hash mismatch: ' + rel)
            seen[rel] = digest
            data = yaml.safe_load(raw)
            if not isinstance(data, dict):
                raise SystemExit('FAIL: upstream record is not a mapping')
            codes = funcs['fault_codes'](data)
            tags = funcs['class_tags'](data)
            dims = funcs['gold_dims'](codes, tags)
            if not dims:
                continue
            bug, fix = data.get('bug', {}) or {}, data.get('fix', {}) or {}
            case_id = 'robust_' + str(data.get('id') or Path(rel).name).strip()
            if case_id in reconstructed:
                raise SystemExit('FAIL: duplicate reconstructed case ID')
            reconstructed[case_id] = {
                'case_id': case_id, 'system': data.get('system'),
                'title': data.get('title'),
                'description': (data.get('description') or '')[:600],
                'issue_url': bug.get('issue'), 'fix_commits': fix.get('commits'),
                'package': bug.get('package'), 'subsystem': bug.get('subsystem'),
                'fault_codes': codes, 'gold_dimension': dims,
                'source': 'ROBUST (Timperley et al. 2024, arXiv:2404.03629)',
            }
            if not funcs['gold_dims'](codes, []):
                fallbacks.append({'case_id': case_id, 'upstream_path': rel,
                                  'classification': data.get('classification'),
                                  'dimensions': dims})
    if seen != pins:
        raise SystemExit('FAIL: incomplete upstream record inventory')
    # Compare complete records, including description, fix status and legacy labels.
    canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False)
    if canonical(reconstructed) != canonical(expected):
        differences = sorted(k for k in set(reconstructed) | set(expected)
                             if canonical(reconstructed.get(k)) != canonical(expected.get(k)))
        raise SystemExit('FAIL: selected record differences: ' + ', '.join(differences))
    if len(reconstructed) != 92 or len(seen) != 221 or len(fallbacks) != 7:
        raise SystemExit('FAIL: selection count differs from pinned reconstruction')
    result = {'upstream_commit': lock['upstream_commit'],
              'upstream_records': len(seen), 'selected_records': len(reconstructed),
              'complete_records_equal_ignoring_list_order': True,
              'fallback_cases': sorted(fallbacks, key=lambda r: r['case_id']),
              'historical_selection_time_or_blinding_proven': False,
              'scientific_labels_changed': False,
              'retained_input_sha256': hashlib.sha256(selected.read_bytes()).hexdigest()}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('VERIFIED: 221 upstream records -> 92 identical selected records; 7 tag fallbacks')


if __name__ == '__main__':
    main()
