"""Run a sealed unchanged adaptive client; keep primary labels untouched."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import warnings

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('_adaptive_base', HERE.parent / 'V39-consumer-contrast/run_contrast.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
CLIENT = base.SNAP / 'u0015/snapshot/ros2cli/ros2cli/entry_points.py'
OLD_PREPARED = Path('/historical/runs/p5-v39-consumer-contrast-002/prepared.json')
OLD_RESULT = OLD_PREPARED.with_name('result.json')
OLD_RECEIPT = HERE.parent / 'V39-consumer-contrast/receipt.json'
SEAL = ROOT / 'V40-EMSE/audit/science-R1/round-001/manifest.json'
GROUPS = ('console_scripts', 'pytest11')


def verify_pins(pins: dict) -> None:
    for name, expected in pins.items():
        path = Path(name)
        actual = base.pin(path) if path.is_file() else {'exists': False}
        if actual != expected:
            raise RuntimeError(f'Presealed input changed: {name}')


def verify_seal() -> str:
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'V32-EMSE/verify_manifest.py'),
                             'verify', str(SEAL)], capture_output=True, text=True, check=True)
    if result.stdout.strip() != 'VERIFIED 6815 files':
        raise RuntimeError('Unexpected current review seal verification')
    return result.stdout.strip()


def mapping_equal(cells: list[dict]) -> bool:
    if len(cells) != len(base.PROVIDERS) or {c.get('provider') for c in cells} != set(base.PROVIDERS):
        return False
    if not all(c.get('status') == 'complete' and all(c.get('groups', {}).get(g) for g in GROUPS) for c in cells):
        return False
    return all(c['groups'] == cells[0]['groups'] for c in cells)


def valid_receipt(receipt: dict, provider: str, seal: str, exit_code: int) -> bool:
    return (exit_code == 0 and receipt.get('status') == 'complete'
            and receipt.get('provider') == provider and receipt.get('prepared_sha256') == seal)


def reject_existing(paths: list[Path]) -> None:
    if any(p.exists() or p.is_symlink() for p in paths):
        raise RuntimeError('Existing receipt or attempt marker: refuse endpoint retry')


def bind_previous_metadata(current: dict, previous_result: dict, prepared_sha: str) -> None:
    cells = previous_result.get('cells', [])
    pairs = {(c.get('receipt', {}).get('provider'), c.get('receipt', {}).get('workflow')) for c in cells}
    expected = {(p, w) for p in base.PROVIDERS for w in ('rosidl_pytest', 'pip_list')}
    if len(cells) != 6 or pairs != expected or previous_result.get('prepared_sha256') != prepared_sha:
        raise RuntimeError('Prior six-cell provenance differs')
    for cell in cells:
        receipt = cell['receipt']
        if (not cell.get('valid_complete') or receipt.get('prepared_sha256') != prepared_sha
                or receipt.get('metadata_before') != current or receipt.get('metadata_after') != current):
            raise RuntimeError('Prior contrast metadata or completion differs')


def prepare(output: Path) -> None:
    if output.exists() or output.is_relative_to(ROOT):
        raise RuntimeError('Require a new external output directory')
    previous = json.loads(OLD_PREPARED.read_text())
    base.verify_inputs(previous)
    verify_seal()
    pins = dict(previous['inputs'])
    manifest = json.loads((base.PACKAGE / 'snapshots.json').read_text())
    expected = {r['path']: r['sha256'] for r in manifest['u0015']['entries'] if 'sha256' in r}
    relative = str(CLIENT.relative_to(base.SNAP / 'u0015/snapshot'))
    if base.pin(CLIENT)['sha256'] != expected[relative]:
        raise RuntimeError('Original client differs from retained snapshot')
    paths = [CLIENT, HERE / 'protocol.md', HERE / 'test_guards.py', Path(__file__).resolve(),
             OLD_PREPARED, OLD_RESULT, OLD_RECEIPT, SEAL]
    pins.update({str(p): base.pin(p) for p in paths})
    import importlib.metadata as host
    metadata = base.metadata_inputs(host)
    historical = json.loads(OLD_RECEIPT.read_text())
    old_sha = base.pin(OLD_PREPARED)['sha256']
    if old_sha != historical['prepared_sha256'] or base.pin(OLD_RESULT)['sha256'] != historical['result_sha256']:
        raise RuntimeError('Prior contrast outputs differ from frozen review receipt')
    bind_previous_metadata(base.private_inventory(metadata), json.loads(OLD_RESULT.read_text()), old_sha)
    tree = ast.parse(CLIENT.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'get_entry_points')
    sites = [f'{CLIENT}:{n.lineno}-{n.end_lineno}' for n in ast.walk(function)
             if isinstance(n, ast.Call) and ast.unparse(n.func) == 'importlib_metadata.entry_points']
    if not sites:
        raise RuntimeError('No direct entry_points call in full original function')
    token = 'api:importlib.metadata.entry_points'
    description = {'_task_id': 'retained-ros2cli-u0015', 'references': [token],
                   'provenance': {f'references[{token}]': ' || '.join(sites)}}
    assembler = base.load_file('_adaptive_assembler', base.FROZEN / 'assemble.py')
    scoring = base.load_file('_adaptive_scoring', base.FROZEN / 'scoring.py')
    predictions = {}
    for provider in ('u0394', 'cpy312'):
        unit = assembler.upgrade_units({'inventory': []}, previous['provider_descriptions']['u0395'],
                                       previous['provider_descriptions'][provider], description)[0]
        findings, unevaluable = scoring.ecm_findings(unit['encoding'])
        predictions[provider] = {'unit': unit, 'findings': findings, 'unevaluable': unevaluable,
                                 'prediction': 'reject' if findings else 'accept'}
    verify_pins(pins)
    verify_pins(metadata)
    prepared = {'prepared_utc': base.utc(), 'inputs': pins, 'metadata': metadata,
                'python_executable': sys.executable, 'python_version': sys.version,
                'client': str(CLIENT), 'client_snapshot_task': 'u0015', 'direct_calls': sites,
                'predictions': predictions, 'groups': GROUPS,
                'baseline': 'u0395 is a baseline, not an accuracy sample',
                'scope': 'post-outcome unchanged ros2cli source, selected providers on host3.11; discovery only',
                'human_reference': False, 'primary_score_changes': False,
                'expected_mappings': 'nonempty and equal; expectation, not an observed result',
                'get_all_scope': 'empty ROS extension registration is only a smoke observation'}
    prepared['previous_contrast_metadata_bound'] = True
    prepared['previous_contrast_result_sha256'] = historical['result_sha256']
    output.mkdir(parents=True)
    base.write_new(output / 'prepared.json', prepared)
    with (output / 'prepared.sha256').open('x') as stream:
        stream.write(base.pin(output / 'prepared.json')['sha256'] + '\n')
    print(json.dumps({'prepared': True, 'input_count': len(pins), 'metadata_count': len(metadata),
                      'predictions': {k: v['prediction'] for k, v in predictions.items()},
                      'prepared_sha256': base.pin(output / 'prepared.json')['sha256']}))


def cell(output: Path, provider_id: str) -> int:
    reject_existing([output / f'{provider_id}.json', output / f'{provider_id}.started.json'])
    prepared_file = output / 'prepared.json'
    prepared = json.loads(prepared_file.read_text())
    if base.pin(prepared_file)['sha256'] != (output / 'prepared.sha256').read_text().strip():
        raise RuntimeError('Prepared receipt differs from its pre-execution seal')
    base.write_new(output / f'{provider_id}.started.json', {'provider': provider_id, 'utc': base.utc()})
    receipt = {'provider': provider_id, 'prepared_sha256': base.pin(prepared_file)['sha256'],
               'started_utc': base.utc(), 'status': 'incomplete', 'groups': {}}
    counter = Counter()
    stdout, stderr = io.StringIO(), io.StringIO()
    original_profile = sys.getprofile()
    caught = []
    try:
        if sys.executable != prepared['python_executable'] or sys.version != prepared['python_version']:
            raise RuntimeError('Host interpreter differs from preseal')
        verify_pins(prepared['inputs'])
        verify_pins(prepared['metadata'])
        provider = base.load_file(f'_boundary_{provider_id}', base.provider_source(provider_id),
                                  package=provider_id != 'u0395')
        import importlib
        importlib.metadata = provider
        sys.modules['importlib.metadata'] = provider
        sys.meta_path[:] = [base.DistributionOnlyFinder(provider)] + [base.ImportOnlyFinder(f) for f in sys.meta_path]
        metadata_before = base.metadata_inputs(provider)
        if metadata_before != prepared['metadata']:
            raise RuntimeError('Selected provider sees a different metadata inventory')

        def observe(frame, event: str, arg: object) -> None:
            if event != 'call' or not frame.f_globals.get('__name__', '').startswith(provider.__name__):
                return
            function = frame.f_code.co_qualname
            counter[function] += 1
            if function == 'EntryPoint.load':
                raise RuntimeError('Entry-point plugin loading is prohibited')
            if function == 'PathDistribution.read_text':
                path = Path(frame.f_locals['self']._path) / frame.f_locals['filename']
                if str(path) not in metadata_before:
                    raise RuntimeError('Metadata read outside presealed inventory')
                verify_pins({str(path): metadata_before[str(path)]})

        with warnings.catch_warnings(record=True) as caught, redirect_stdout(stdout), redirect_stderr(stderr):
            warnings.simplefilter('always')
            sys.setprofile(observe)
            client = base.load_file('_adaptive_original_client', CLIENT)
            if client.importlib_metadata is not provider:
                raise RuntimeError('Original client bypassed selected provider')
            for group in GROUPS:
                returned = client.get_entry_points(group)
                if not returned:
                    raise RuntimeError(f'Required group is empty: {group}')
                rows = []
                classes = Counter()
                for name, ep in sorted(returned.items()):
                    if not type(ep).__module__.startswith(provider.__name__) or ep.group != group or ep.name != name:
                        raise RuntimeError('Returned entry point identity/provider differs')
                    rows.append({'name': name, 'value': ep.value, 'group': ep.group})
                    classes[f'{type(ep).__module__}.{type(ep).__qualname__}'] += 1
                receipt['groups'][group] = rows
                receipt.setdefault('entrypoint_classes', {})[group] = dict(classes)
            extension = client.get_all_entry_points()
            receipt['get_all_smoke'] = {'group_count': len(extension),
                                        'entry_count': sum(len(v) for v in extension.values()),
                                        'counts_as_nonempty_extension_validation': False}
        sys.setprofile(original_profile)
        metadata_after = base.metadata_inputs(provider)
        verify_pins(prepared['inputs'])
        verify_pins(prepared['metadata'])
        if metadata_after != metadata_before or counter['entry_points'] < 3 or counter['EntryPoint.load']:
            raise RuntimeError('Metadata or original provider-call guards failed')
        receipt.update(status='complete', metadata_inventory=base.private_inventory(metadata_after),
                       source_pins_unchanged=True, metadata_stable=True,
                       selected_provider_module=provider.__name__, provider_path=provider.__file__)
    except Exception as exc:
        receipt.update(exception_type=type(exc).__name__, exception_message=str(exc),
                       traceback=traceback.format_exc())
    finally:
        sys.setprofile(original_profile)
        receipt.update(provider_calls=dict(counter), stdout=stdout.getvalue(), stderr=stderr.getvalue(),
                       warnings=[{'category': w.category.__name__, 'message': str(w.message)} for w in caught],
                       ended_utc=base.utc())
    base.write_new(output / f'{provider_id}.json', receipt)
    print(json.dumps({'provider': provider_id, 'status': receipt['status']}))
    return 0 if receipt['status'] == 'complete' else 1


def _run_cells(output: Path) -> int:
    prepared_file = output / 'prepared.json'
    prepared = json.loads(prepared_file.read_text())
    seal = base.pin(prepared_file)
    verify_pins(prepared['inputs'])
    verify_pins(prepared['metadata'])
    verify_seal()
    cells = []
    for provider in base.PROVIDERS:
        command = [sys.executable, '-B', str(Path(__file__).resolve()), 'cell', '--output', str(output), '--provider', provider]
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS')}
        env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PIP_NO_INDEX='1',
                   PIP_DISABLE_PIP_VERSION_CHECK='1', PIP_CONFIG_FILE=os.devnull)
        try:
            process = subprocess.run(command, cwd=output, env=env, capture_output=True, text=True, timeout=60)
            handle = {'exit_code': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr, 'command': command}
        except subprocess.TimeoutExpired as exc:
            def decode(value):
                return value.decode(errors='replace') if isinstance(value, bytes) else value
            handle = {'timed_out': True, 'command': command,
                      'stdout': decode(exc.stdout), 'stderr': decode(exc.stderr)}
        path = output / f'{provider}.json'
        receipt = json.loads(path.read_text()) if path.exists() else {'provider': provider, 'status': 'missing'}
        receipt['native_handle'] = handle
        receipt['valid_complete'] = valid_receipt(receipt, provider, seal['sha256'], handle.get('exit_code', -1))
        cells.append(receipt)
    verify_pins(prepared['inputs'])
    verify_pins(prepared['metadata'])
    if base.pin(prepared_file) != seal:
        raise RuntimeError('Prepared predictions changed during run')
    verify_seal()
    equal = mapping_equal(cells)
    result = {'closed_utc': base.utc(), 'prepared_sha256': seal['sha256'], 'cells': cells,
              'complete_cells': sum(c['valid_complete'] for c in cells), 'full_nonempty_mappings_equal': equal,
              'human_reference': False, 'primary_scoring_unchanged': True, 'scope': prepared['scope']}
    base.write_new(output / 'result.json', result)
    print(json.dumps({k: result[k] for k in ('complete_cells', 'full_nonempty_mappings_equal', 'prepared_sha256')}))
    return 0 if result['complete_cells'] == 3 and equal else 1


def run(output: Path) -> int:
    names = ['result.json', 'run-failure.json', 'run.started.json']
    names += [p + suffix for p in base.PROVIDERS for suffix in ('.json', '.started.json')]
    reject_existing([output / name for name in names])
    base.write_new(output / 'run.started.json', {'utc': base.utc()})
    try:
        prepared = output / 'prepared.json'
        if base.pin(prepared)['sha256'] != (output / 'prepared.sha256').read_text().strip():
            raise RuntimeError('Prepared receipt differs from its pre-execution seal')
        return _run_cells(output)
    except Exception as exc:
        base.write_new(output / 'run-failure.json', {'utc': base.utc(), 'status': 'incomplete',
                       'exception_type': type(exc).__name__, 'message': str(exc),
                       'traceback': traceback.format_exc(), 'partial_cell_receipts_preserved': True})
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'run', 'cell'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--provider', choices=base.PROVIDERS)
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.is_relative_to(ROOT):
        parser.error('Output must be outside the paper project')
    if args.mode == 'prepare':
        prepare(output)
    elif args.mode == 'run':
        sys.exit(run(output))
    else:
        if not args.provider:
            parser.error('Cell requires provider')
        sys.exit(cell(output, args.provider))
