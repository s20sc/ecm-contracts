"""V22: affirmative active-A2 coverage for adjudicated cause-correct credit.

Reads existing immutable packets and final records; never generates labels. A
missing, superseded, incomplete, or unresolved record cannot confer credit.
Pre-adjudication scoring deliberately does not call this gate.
"""
from pathlib import Path
import json
import re


MISSING = object()


def trigger_value(encoding, path):
    """Resolve trigger paths, retaining token membership and explicit absence states."""
    token = re.fullmatch(r'(ver_delta\.(?:changed_fields|consumer_reads)|(?:producer|consumer)\.(?:exclusive|perm_requires|perm_limits))\[(.*)\]', path)
    if token:
        base, key = token.groups()
        values = trigger_value(encoding, base)
        if isinstance(values, list):
            return {'member': key in values}
        return values.get(key, MISSING) if isinstance(values, dict) else MISSING
    current = encoding
    for segment in path.split('.'):
        part = re.fullmatch(r'(\w+)(?:\[(\d+)\])?', segment)
        if part is None or not isinstance(current, dict):
            return MISSING
        current = current.get(part[1], MISSING)
        if part[2] is not None:
            index = int(part[2])
            if not isinstance(current, list) or index >= len(current):
                return MISSING
            current = current[index]
    if path.endswith('.perm_grants'):
        state = (encoding.get(path.split('.')[0], {}).get('_states') or {}).get('perm_grants')
        return (current, state) if current is not MISSING else MISSING
    return current


def load_coverage(root, fold='adjudicated'):
    root = Path(root)
    roles = json.loads((root / 'ledger/adjudicators.json').read_text())
    labels = json.loads((root / 'ledger/method_labels.json').read_text())
    strict = fold == 'adjudicated_adj1only'
    active = {x['item']: x for x in json.loads((root / fold / 'fold_log.json').read_text())
              if x['item'].startswith('A2-')}
    superseded = set(json.loads((root / 'ledger/a2_r3_supersedes.json').read_text()).values())
    packets = {}
    for path in sorted((root / 'adjudication/packets').glob('A2_*.json')):
        for item in json.loads(path.read_text()):
            iid = item['item_id']
            if iid in packets and packets[iid] != item:
                raise ValueError('Conflicting packet identity: ' + iid)
            packets[iid] = item
    by_case = {}
    for iid, status in sorted(active.items()):
        if iid in superseded or status['decision'] != 'provenance_folded' or status.get('splits'):
            continue
        item = packets.get(iid)
        if item is None:
            continue
        records = []
        for role in ('ADJ1', 'ADJ2', 'ADJ3'):
            path = root / 'adjudication' / roles[role] / (iid + '.json')
            record = json.loads(path.read_text()) if path.exists() else None
            if record is not None:
                for key in ('item_id', 'case_id', 'composition', 'method_label', 'rule'):
                    if record.get(key) != item.get(key):
                        raise ValueError(f'{iid}: record/packet mismatch in {key}')
            records.append(record)
        a, b, c = records
        if strict:
            b, c = a, None
        if a is None or b is None:
            continue
        def decision(getter):
            x, y = getter(a), getter(b)
            if x is None or y is None:
                return None
            return x if x == y else getter(c) if c is not None else None
        op = decision(lambda rec: (rec.get('operation_edge') or {}).get('verdict'))
        paths = (item.get('evidence') or {}).get('trigger_paths') or []
        values = {}
        for path in paths:
            def value(rec):
                hits = [x.get('verdict') for x in rec.get('values', []) if x.get('path') == path]
                return hits[0] if len(hits) == 1 else None
            values[path] = decision(value)
        method = next((m for m, label in labels.items() if label == item['method_label']), None)
        if method is None:
            raise ValueError('Unknown neutral method: ' + item['method_label'])
        entry = {'item_id': iid, 'method': method, 'rule': item['rule'],
                 'covers': [{'element': item.get('element'), 'token': item.get('token')}] + item.get('also_covers', []),
                 'unit_kind': (item.get('evidence') or {}).get('unit_kind'),
                 'provenance': (item.get('evidence') or {}).get('provenance') or {},
                 'encoding': (item.get('evidence') or {}).get('encoding') or {},
                 'operation_edge': op, 'values': values}
        by_case.setdefault(item['case_id'], {}).setdefault(item['composition'], []).append(entry)
    return by_case


def finding_covered(entries, method, finding, unit, paths):
    """Require an explicit agreed operation/edge and verified triggering values."""
    if not paths:
        return False
    wanted = {'element': finding.get('element'), 'token': finding.get('token')}
    for item in entries:
        if item['method'] != method or item['rule'] != finding['rule']:
            continue
        if wanted not in item['covers'] or item['unit_kind'] != unit['kind']:
            continue
        if item['operation_edge'] != 'agree':
            continue
        if any(item['values'].get(path) != 'verified' for path in paths):
            continue
        # The coverage must refer to the evidence currently being scored.
        if any(item['provenance'].get(path) != unit['provenance'].get(path) for path in paths):
            continue
        if item['encoding'].get('type') != unit['encoding'].get('type'):
            continue
        values = [(trigger_value(item['encoding'], path), trigger_value(unit['encoding'], path))
                  for path in paths]
        if any(old is MISSING or new is MISSING or old != new for old, new in values):
            continue
        return True
    return False
