"""Regression tests for Codex V21-R1 N2 using archived real cases."""
import copy
import json
from pathlib import Path
import shutil

import adjudication_guard as G
import scoring as S

ROOT = Path(__file__).resolve().parent


def sample():
    cid = 'C3-099'
    comp = json.loads((ROOT / 'assembled' / (cid + '.json')).read_text())['compositions']['broken']
    spec = S.load_specs(True)[cid]
    verdicts = json.loads((ROOT / 'adjudicated/provenance_verdicts.json').read_text()).get(cid, {}).get('broken', {})
    entries = G.load_coverage(ROOT)[cid]['broken']
    return comp, spec, verdicts, entries


def score(verdicts=None, entries='real'):
    comp, spec, original, real = sample()
    kwargs = {} if entries is None else {'a2_entries': real if entries == 'real' else entries}
    return S.score_composition(comp, spec['failed_conditions'], spec['operation'],
                               original if verdicts is None else verdicts, **kwargs)['ECM']


def test_existing_affirmative_evidence_preserves_detection():
    assert score()['state'] == 'right_reason'


def test_negative_operation_edge_is_not_ignored():
    before = score(entries=None)
    after = score(verdicts={'_operation_edge': 'disagree'}, entries=None)
    assert before['state'] == 'right_reason'
    assert after['state'] == 'unverified'
    assert after['reject'] is True
    assert [(f['rule'], f.get('token')) for f in before['findings']] == [(f['rule'], f.get('token')) for f in after['findings']]


def test_missing_a2_coverage_cannot_confer_credit():
    assert score(entries=[])['state'] == 'unverified'
    assert score(entries=None)['state'] == 'right_reason'  # Explicit pre-adjudication behavior.


def test_missing_trigger_verdict_cannot_confer_credit():
    entries = copy.deepcopy(sample()[3])
    for item in entries:
        item['values'] = {}
    assert score(entries=entries)['state'] == 'unverified'


def test_changed_evidence_cannot_borrow_old_coverage():
    entries = copy.deepcopy(sample()[3])
    for item in entries:
        item['provenance'] = {k: 'different evidence' for k in item['provenance']}
    assert score(entries=entries)['state'] == 'unverified'


def test_changed_trigger_values_cannot_borrow_unchanged_citations():
    comp, spec, verdicts, entries = sample()
    before = S.score_composition(comp, spec['failed_conditions'], spec['operation'], verdicts,
                                 a2_entries=entries)['DI']
    assert before['state'] == 'right_reason'
    for unit in comp['units']:
        if unit['kind'] != 'pair_view' or unit['status'] != 'done':
            continue
        for side, ports, digest in [('producer', 'outputs', 'a' * 64), ('consumer', 'inputs', 'b' * 64)]:
            unit['encoding'][side][ports][0]['definition_id']['value'] = digest
    after = S.score_composition(comp, spec['failed_conditions'], spec['operation'], verdicts,
                                a2_entries=entries)['DI']
    assert after['state'] == 'unverified'
    assert after['reject'] is True


def test_trigger_resolution_preserves_token_granularity_and_absence():
    token = 'api:Module.Class.operator[]'
    a = {'ver_delta': {'changed_fields': [token, 'other']}}
    b = {'ver_delta': {'changed_fields': [token]}}
    path = 'ver_delta.changed_fields[' + token + ']'
    assert G.trigger_value(a, path) == G.trigger_value(b, path) == {'member': True}
    assert G.trigger_value({}, path) is G.MISSING
    assert G.trigger_value({'producer': {'perm_grants': [], '_states': {'perm_grants': 'absent'}}}, 'producer.perm_grants') != G.trigger_value({'producer': {'perm_grants': []}}, 'producer.perm_grants')


def test_missing_packet_encoding_cannot_confer_credit():
    entries = copy.deepcopy(sample()[3])
    for item in entries:
        item['encoding'] = {}
    assert score(entries=entries)['state'] == 'unverified'


def test_operation_requires_affirmative_agreement():
    entries = copy.deepcopy(sample()[3])
    for item in entries:
        item['operation_edge'] = None
    assert score(entries=entries)['state'] == 'unverified'


def small_copy(tmp_path):
    # Only final adjudication records and packets; no source snapshots or execution.
    for folder in ('adjudication', 'ledger', 'adjudicated', 'adjudicated_adj1only'):
        source = ROOT / folder
        target = tmp_path / folder
        target.mkdir()
        # Preserve fixture bytes, not the frozen input's read-only metadata.
        for path in sorted(source.rglob('*')):
            dest = target / path.relative_to(source)
            if path.is_symlink():
                raise ValueError('Unexpected fixture symlink: ' + str(path))
            if path.is_dir():
                dest.mkdir()
            else:
                shutil.copyfile(path, dest)
    return tmp_path


def test_missing_second_record_drops_primary_but_not_strict_coverage(tmp_path):
    root = small_copy(tmp_path)
    cov = G.load_coverage(root)
    item = next(x for x in cov['C3-099']['broken'] if x['method'] == 'ECM')
    (root / 'adjudication/adj2' / (item['item_id'] + '.json')).unlink()
    assert item['item_id'] not in {x['item_id'] for x in G.load_coverage(root).get('C3-099', {}).get('broken', [])}
    assert item['item_id'] in {x['item_id'] for x in G.load_coverage(root, 'adjudicated_adj1only').get('C3-099', {}).get('broken', [])}


def test_superseded_records_never_confer_active_coverage():
    old = set(json.loads((ROOT / 'ledger/a2_r3_supersedes.json').read_text()).values())
    cov = G.load_coverage(ROOT)
    active = {x['item_id'] for case in cov.values() for entries in case.values() for x in entries}
    assert not old & active
    assert len(active) == 48


def test_unresolved_operation_split_is_not_agreement(tmp_path):
    root = small_copy(tmp_path)
    item = next(x for x in G.load_coverage(root)['C3-099']['broken'] if x['method'] == 'ECM')
    path = root / 'adjudication/adj2' / (item['item_id'] + '.json')
    record = json.loads(path.read_text());record['operation_edge']['verdict'] = 'disagree';path.write_text(json.dumps(record))
    third = root / 'adjudication/adj3' / (item['item_id'] + '.json')
    if third.exists():
        record = json.loads(third.read_text());record.pop('operation_edge', None);third.write_text(json.dumps(record))
    altered = next(x for x in G.load_coverage(root)['C3-099']['broken'] if x['item_id'] == item['item_id'])
    assert altered['operation_edge'] is None


def test_finding_specific_disagreement_does_not_invalidate_other_confirmed_findings():
    cid = 'robust_55e84a6'
    comp = json.loads((ROOT / 'assembled' / (cid + '.json')).read_text())['compositions']['broken']
    spec = S.load_specs(True, 'adjudicated_adj1only')[cid]
    verdicts = json.loads((ROOT / 'adjudicated_adj1only/provenance_verdicts.json').read_text())[cid]['broken']
    assert verdicts['_operation_edge'] == 'disagree'
    entries = G.load_coverage(ROOT, 'adjudicated_adj1only')[cid]['broken']
    assert {e['operation_edge'] for e in entries} == {'agree', 'disagree'}
    result = S.score_composition(comp, spec['failed_conditions'], spec['operation'], verdicts, a2_entries=entries)['ECM']
    assert result['state'] == 'right_reason'
    assert all(not str(m.get('token', '')).endswith('.redraw') for m in result['matched'])
    # Removing the affirmative entries leaves only the rejected edge, which cannot grant credit.
    bad_only = [e for e in entries if e['operation_edge'] == 'disagree']
    denied = S.score_composition(comp, spec['failed_conditions'], spec['operation'], verdicts, a2_entries=bad_only)['ECM']
    assert denied['state'] == 'unverified'
