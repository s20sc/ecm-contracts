"""Preseal source-derived predictions, then run six isolated real workflows."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import traceback
import sys
import warnings

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
import public_integrity as public
PACKAGE = public.roots()['package']
FROZEN = PACKAGE / 'experiments/pathb_v2'
SNAP = public.roots()['retained']
PROVIDERS = {
    'u0395': ('Lib/importlib/metadata.py', '3.9.0'),
    'u0394': ('Lib/importlib/metadata/__init__.py', '3.10.0'),
    'cpy312': ('__init__.py', '3.12.0'),
}
REVIEW_SEAL = ROOT / 'public-inputs.json'
# Historical private review-tree guards are replaced by the public input guard.


INTAKE = public.roots()['intake']
COMMIT312 = '0fb18b02c8ad56299d6a2910be0bab8ad601ef24'


def provider_source(task: str) -> Path:
    relative, _ = PROVIDERS[task]
    return (INTAKE / 'provider3.12' / relative if task == 'cpy312'
            else SNAP / task / 'snapshot' / relative)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pin(path: Path) -> dict:
    before = path.stat()
    result = {'sha256': digest(path.read_bytes()), 'size': before.st_size}
    after = path.stat()
    # Reading can update atime without changing input identity or content.
    stable = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if any(getattr(before, key) != getattr(after, key) for key in stable):
        raise RuntimeError(f'Input changed while hashing: {path}')
    return result


def write_new(path: Path, value: dict) -> None:
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def load_file(name: str, path: Path, package: bool = False):
    spec = importlib.util.spec_from_file_location(
        name, path, submodule_search_locations=[str(path.parent)] if package else None)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def declarations(task: str) -> dict:
    relative, version = PROVIDERS[task]
    path = provider_source(task)
    tree = ast.parse(path.read_text())
    result: dict = {'_task_id': task, 'manifest_version': version,
                    'declares': {}, 'provenance': {}, 'references': []}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ('entry_points', 'distributions'):
            token = f'api:importlib.metadata.{node.name}'
            result['declares'][token] = json.dumps({
                'args': ast.dump(node.args, include_attributes=False),
                'returns': ast.dump(node.returns, include_attributes=False) if node.returns else None,
            }, sort_keys=True)
            result['provenance'][f'declares[{token}]'] = f'{path}:{node.lineno}-{node.end_lineno}'
    if len(result['declares']) != 2:
        raise RuntimeError('Required declared two-function surface is missing')
    result['provenance']['manifest_version'] = (f'CPython tag v{version}; commit {COMMIT312}'
        if task == 'cpy312' else f'CPython retained tag v{version}; V32 snapshot pin')
    return result


def verify_inputs(prepared: dict) -> None:
    for name, expected in prepared['inputs'].items():
        if pin(Path(name)) != expected:
            raise RuntimeError(f'Presealed source changed: {name}')


def verify_review_seal() -> dict:
    return public.verify()


def prepare(output: Path) -> None:
    if output.exists() or output.is_relative_to(ROOT):
        raise RuntimeError('Require a new external output directory')
    if any(os.environ.get(name) for name in ('PYTHONPATH', 'PYTHONHOME')):
        raise RuntimeError('Prepare requires unset PYTHONPATH/PYTHONHOME')
    output.mkdir(parents=True)
    review_seal_before = verify_review_seal()
    import pip
    import pytest
    import pluggy
    import _pytest
    pins = json.loads((PACKAGE / 'snapshots.json').read_text())
    paths = {Path(__file__).resolve(), HERE / 'protocol.md', Path(sys.executable).resolve(),
             REVIEW_SEAL, public.config_path(), Path(public.__file__), PACKAGE / 'snapshots.json', FROZEN / 'FREEZE.json'}
    intake = json.loads((INTAKE / 'source-intake.json').read_text())
    helpers = json.loads((INTAKE / 'helper-source-intake.json').read_text())
    if intake['commit'] != COMMIT312 or helpers['commit'] != COMMIT312 or helpers['failures'] or helpers['unresolved_helpers']:
        raise RuntimeError('Unresolved or mismatched pinned 3.12 source intake')
    expected312 = {'__init__.py': intake['requests'][1]['sha256']}
    expected312.update({r['name'] + '.py': r['sha256'] for r in helpers['fetched']})
    if set(expected312) != {p.name for p in (INTAKE / 'provider3.12').glob('*.py')}:
        raise RuntimeError('3.12 helper inventory differs from intake')
    paths.update([INTAKE / 'source-intake.json', INTAKE / 'helper-source-intake.json'])
    for task, (relative, _) in PROVIDERS.items():
        source = provider_source(task)
        targets = sorted(source.parent.glob('*.py')) if task != 'u0395' else [source]
        expected = expected312 if task == 'cpy312' else {
            row['path']: row['sha256'] for row in pins[task]['entries'] if 'sha256' in row}
        for target in targets:
            key = target.name if task == 'cpy312' else str(target.relative_to(SNAP / task / 'snapshot'))
            if pin(target)['sha256'] != expected[key]:
                raise RuntimeError(f'Pinned provider source mismatch: {target}')
            paths.add(target)
    consumer = SNAP / 'u0396/snapshot/rosidl_cli/rosidl_cli/entry_points.py'
    expected = {row['path']: row['sha256'] for row in pins['u0396']['entries'] if 'sha256' in row}
    if pin(consumer)['sha256'] != expected['rosidl_cli/rosidl_cli/entry_points.py']:
        raise RuntimeError('Consumer snapshot mismatch')
    paths.add(consumer)
    for task in ('u0394', 'u0395', 'u0396'):
        external = SNAP / task / 'recon' / f'{task}.json'
        frozen = FROZEN / 's2_work/tasks' / task / 'recon' / f'{task}.json'
        if pin(external) != pin(frozen):
            raise RuntimeError(f'External reconstruction differs from frozen version: {task}')
        paths.add(external)
    for module in (pip, pytest, pluggy, _pytest):
        paths.update(Path(module.__file__).parent.rglob('*.py'))
    paths.update(FROZEN.glob('*.py'))
    paths.update((PACKAGE / 'experiments/pathb/checker').glob('*.py'))
    input_pins = {str(p): pin(p) for p in sorted(paths)}
    assembler = load_file('_boundary_assembler', FROZEN / 'assemble.py')
    scoring = load_file('_boundary_scoring', FROZEN / 'scoring.py')
    old = declarations('u0395')
    new_versions = {task: declarations(task) for task in ('u0394', 'cpy312')}
    consumers = {}
    for workflow, token, source_path in [
        ('rosidl_pytest', 'api:importlib.metadata.entry_points', consumer),
        ('pip_list', 'api:importlib.metadata.distributions', Path(pip.__file__).parent /
         '_internal/metadata/importlib/_envs.py'),
    ]:
        function_name = token.rsplit('.', 1)[-1]
        sites = []
        tree = ast.parse(source_path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called = ast.unparse(node.func)
            if called in (f'importlib_metadata.{function_name}', f'importlib.metadata.{function_name}'):
                sites.append(f'{source_path}:{node.lineno}-{node.end_lineno}')
        if not sites:
            raise RuntimeError(f'Missing direct consumer call: {workflow}')
        description = {'_task_id': f'host-source-{workflow}', 'references': [token],
                       'provenance': {f'references[{token}]': ' || '.join(sites)}}
        comparisons = {}
        for task, new in new_versions.items():
            unit = assembler.upgrade_units({'inventory': []}, old, new, description)[0]
            findings, unevaluable = scoring.ecm_findings(unit['encoding'])
            comparisons[task] = {'upgrade_unit': unit, 'findings': findings, 'unevaluable': unevaluable,
                                 'prediction': 'reject' if findings else 'accept'}
        consumers[workflow] = {'source_direct_calls': sites, 'surface_description': description,
                               'comparisons': comparisons}
    original = [json.loads((SNAP / t / 'recon' / f'{t}.json').read_text())
                for t in ('u0395', 'u0394', 'u0396')]
    original_unit = assembler.upgrade_units({'inventory': []}, *original)[0]
    original_findings, original_unevaluable = scoring.ecm_findings(original_unit['encoding'])
    prepared = {'prepared_utc': utc(), 'script': str(Path(__file__).resolve()),
                'python_executable': sys.executable, 'python_version': sys.version,
                'scope': 'source-selected post-outcome three-provider two-client contrast on host3.11; no primary scoring',
                'versions': {'pip': pip.__version__, 'pytest': pytest.__version__, 'pluggy': pluggy.__version__},
                'delivery_replay': True, 'historical_counts_expected': False,
                'inputs': input_pins, 'review_seal_before': review_seal_before,
                'provider_descriptions': {'u0395': old, **new_versions}, 'consumers': consumers,
                'original_rosidl_prediction': {'unit': original_unit, 'findings': original_findings,
                                               'unevaluable': original_unevaluable},
                'matrix': [{'provider': provider, 'workflow': workflow}
                           for provider in PROVIDERS for workflow in consumers]}
    verify_inputs(prepared)
    write_new(output / 'prepared.json', prepared)
    public.seal_prepared(output)
    print(json.dumps({'prepared': True, 'inputs': len(paths),
                      'predictions': {k: {t: c['prediction'] for t,c in v['comparisons'].items()} for k,v in consumers.items()},
                      'prepared_sha256': pin(output / 'prepared.json')['sha256']}))


class ImportOnlyFinder:
    def __init__(self, finder: object) -> None:
        self.finder = finder

    def __getattr__(self, key: str) -> object:
        if key == 'find_distributions':
            raise AttributeError(key)
        return getattr(self.finder, key)


class DistributionOnlyFinder:
    """Delegate retained distribution discovery without intercepting imports."""
    def __init__(self, provider) -> None:
        self.provider = provider

    def find_spec(self, fullname: str, path=None, target=None):
        return None

    def find_distributions(self, context):
        return self.provider.MetadataPathFinder.find_distributions(context)


def metadata_inputs(provider) -> dict[str, dict]:
    result = {}
    for distribution in provider.Distribution.discover():
        if not type(distribution).__module__.startswith(provider.__name__):
            raise RuntimeError('Distribution discovery bypassed selected provider')
        base = Path(distribution._path)
        paths = {base / filename for filename in ('entry_points.txt', 'METADATA', 'PKG-INFO',
                                                   'direct_url.json', 'INSTALLER', 'WHEEL',
                                                   'requires.txt')}
        if base.is_dir():
            paths.update(p for p in base.rglob('*') if p.is_file())
        for path in sorted(paths):
            result[str(path)] = pin(path) if path.is_file() else {'exists': False}
    return result


def private_inventory(inputs: dict) -> dict:
    rows = [(digest(path.encode()), value) for path, value in sorted(inputs.items())]
    return {'candidate_count': len(rows), 'sha256': digest(json.dumps(rows, sort_keys=True).encode())}


def cell(output: Path, provider_id: str, workflow: str) -> int:
    public.verify_prepared(output)
    public.claim_attempt(output, f'{provider_id}-{workflow}', [f'{provider_id}-{workflow}.json'])
    prepared_path = output / 'prepared.json'
    prepared = json.loads(prepared_path.read_text())
    result: dict = {'provider': provider_id, 'workflow': workflow, 'started_utc': utc(),
                    'prepared_sha256': pin(prepared_path)['sha256'], 'command': sys.orig_argv,
                    'predicted': (None if provider_id == 'u0395' else
                        prepared['consumers'][workflow]['comparisons'][provider_id]['prediction']),
                    'provider_calls': {}, 'status': 'incomplete'}
    stdout, stderr = io.StringIO(), io.StringIO()
    counter: Counter[str] = Counter()
    pip_distribution_classes: Counter[str] = Counter()
    original_profile = sys.getprofile()
    caught: list = []
    try:
        if sys.executable != prepared['python_executable'] or sys.version != prepared['python_version']:
            raise RuntimeError('Runtime differs from presealed environment')
        if os.environ.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD') != '1':
            raise RuntimeError('Required plugin-autoload disabling is missing')
        if any(os.environ.get(name) for name in ('PYTEST_ADDOPTS', 'PYTEST_PLUGINS', 'PYTHONPATH', 'PYTHONHOME')):
            raise RuntimeError('Workflow environment has undeclared import or pytest options')
        if os.environ.get('PIP_CONFIG_FILE') != os.devnull:
            raise RuntimeError('pip configuration must be disabled')
        verify_inputs(prepared)
        relative, _ = PROVIDERS[provider_id]
        provider = load_file(f'_boundary_{provider_id}', provider_source(provider_id),
                             package=provider_id != 'u0395')
        # Process-local explicit binding; no source implementation is modified.
        import importlib
        importlib.metadata = provider
        sys.modules['importlib.metadata'] = provider
        sys.meta_path[:] = [DistributionOnlyFinder(provider)] + [ImportOnlyFinder(f) for f in sys.meta_path]
        result['binding'] = {'stdlib_module': 'importlib.metadata', 'selected_module': provider.__name__,
                             'provider_path': provider.__file__}
        metadata_before = metadata_inputs(provider)
        result['metadata_before'] = private_inventory(metadata_before)

        def observe(frame, event: str, arg: object) -> None:
            module = frame.f_globals.get('__name__', '')
            function = frame.f_code.co_qualname
            if event == 'call' and module.startswith(provider.__name__):
                counter[frame.f_code.co_qualname] += 1
                if function == 'PathDistribution.read_text':
                    path = Path(frame.f_locals['self']._path) / frame.f_locals['filename']
                    if str(path) not in metadata_before:
                        raise RuntimeError('Provider read metadata outside preinventoried host inputs')
                    actual = pin(path) if path.is_file() else {'exists': False}
                    if actual != metadata_before[str(path)]:
                        raise RuntimeError('Metadata changed before actual provider read')
            if (workflow == 'pip_list' and event == 'return' and arg is not None
                    and module == 'pip._internal.metadata.importlib._envs'
                    and function == 'Environment._iter_distributions'):
                underlying = getattr(arg, '_dist', None)
                cls = type(underlying)
                key = f'{cls.__module__}.{cls.__qualname__}'
                pip_distribution_classes[key] += 1
                if not (cls.__module__ == provider.__name__
                        or cls.__module__.startswith(provider.__name__ + '.')):
                    raise RuntimeError('pip yielded a distribution from a legacy or undeclared provider')

        with warnings.catch_warnings(record=True) as caught, redirect_stdout(stdout), redirect_stderr(stderr):
            warnings.simplefilter('always')
            sys.setprofile(observe)
            if workflow == 'rosidl_pytest':
                consumer = load_file('_boundary_rosidl', SNAP /
                                     'u0396/snapshot/rosidl_cli/rosidl_cli/entry_points.py')
                mapping = consumer.get_entry_points('console_scripts', specs=['pytest'], strict=True)
                if set(mapping) != {'pytest'} or not type(mapping['pytest']).__module__.startswith(provider.__name__):
                    raise RuntimeError('Selected retained EntryPoint was not verified')
                result['entry_point'] = {'name': 'pytest', 'value': mapping['pytest'].value,
                                         'class': f'{type(mapping["pytest"]).__module__}.{type(mapping["pytest"]).__name__}'}
                if mapping['pytest'].value != 'pytest:console_main':
                    raise RuntimeError('Predeclared pytest entry point differs')
                loaded = consumer.load_entry_points('console_scripts', specs=['pytest'], strict=True)
                temporary = output / f'{provider_id}-pytest-temp'
                temporary.mkdir()
                sys.argv = ['pytest', '-q', '-c', '/dev/null', '-p', 'no:cacheprovider', '--confcutdir', str(FROZEN),
                            '--basetemp', str(temporary / 'run'),
                            str(FROZEN / 'test_scoring.py'), str(FROZEN / 'test_adjudication_guard.py')]
                result['workflow_argv'] = sys.argv[:]
                exit_code = int(loaded['pytest']())
            else:
                from pip._internal.cli.main import main
                from pip._internal.metadata import select_backend
                backend = select_backend()
                if backend.NAME != 'importlib':
                    raise RuntimeError('pip did not select importlib backend')
                result['pip_backend'] = backend.NAME
                result['workflow_argv'] = ['pip', '--isolated', 'list', '--format=json', '--disable-pip-version-check']
                exit_code = int(main(result['workflow_argv'][1:]))
            sys.setprofile(original_profile)
        result['warnings'] = [{'category': w.category.__name__, 'message': str(w.message),
                               'filename': w.filename, 'line': w.lineno} for w in caught]
        result['exit_code'] = exit_code
        if workflow == 'pip_list':
            packages = json.loads(stdout.getvalue())
            canonical = json.dumps(sorted(packages, key=lambda p: p['name'].casefold()),
                                   sort_keys=True, separators=(',', ':'))
            result['output'] = {'package_count': len(packages), 'canonical_sha256': digest(canonical.encode())}
            result['pip_distribution_classes'] = dict(pip_distribution_classes)
            result['endpoint_success'] = (exit_code == 0 and bool(packages) and counter['distributions'] > 0
                                          and sum(pip_distribution_classes.values()) >= len(packages))
        else:
            result['stdout'] = stdout.getvalue()
            import re
            matched = re.search(r'\b(\d+) passed\b', stdout.getvalue())
            result['passed_count'] = int(matched.group(1)) if matched else None
            result['endpoint_success'] = (exit_code == 0 and result['passed_count'] == 81
                                          and not re.search(r'\b\d+ (skipped|deselected|xfailed|xpassed)\b', stdout.getvalue())
                                          and counter['EntryPoint.load'] >= 1 and counter['entry_points'] >= 1)
        result['stderr'] = stderr.getvalue()
        result['provider_calls'] = dict(counter)
        metadata_after = metadata_inputs(provider)
        result['metadata_after'] = private_inventory(metadata_after)
        result['metadata_stable'] = metadata_before == metadata_after
        verify_inputs(prepared)
        result['source_pins_unchanged'] = True
        result['observed_outcome'] = 'success' if result['endpoint_success'] else 'endpoint_non_success'
        result['status'] = 'complete' if result['endpoint_success'] and result['metadata_stable'] else 'incomplete'
    except Exception as exc:
        sys.setprofile(original_profile)
        frames = [{'filename': f.filename, 'line': f.lineno, 'function': f.name}
                  for f in traceback.extract_tb(exc.__traceback__)]
        failed_object = getattr(exc, 'obj', None)
        cls = type(failed_object)
        result.update(exception_type=type(exc).__name__, exception_message=str(exc),
                      exception_frames=frames, exception_attribute=getattr(exc, 'name', None),
                      exception_object_type=f'{cls.__module__}.{cls.__qualname__}',
                      stdout=stdout.getvalue() if workflow == 'rosidl_pytest' else '[private pip inventory omitted]',
                      stderr=stderr.getvalue(), provider_calls=dict(counter))
        # A real consumer failure is an observed endpoint outcome, not a harness success claim.
        direct_failure = (workflow == 'rosidl_pytest' and isinstance(exc, AttributeError)
            and getattr(exc, 'name', None) == 'get' and cls.__name__ == 'EntryPoints'
            and cls.__module__ == f'_boundary_{provider_id}'
            and frames[-1]['filename'] == str(SNAP / 'u0396/snapshot/rosidl_cli/rosidl_cli/entry_points.py')
            and frames[-1]['function'] == 'get_entry_points'
            and counter['entry_points'] >= 1 and counter['EntryPoint.load'] == 0)
        if direct_failure:
            try:
                metadata_after = metadata_inputs(provider)
                result['metadata_after'] = private_inventory(metadata_after)
                result['metadata_stable'] = metadata_before == metadata_after
                verify_inputs(prepared)
                result['source_pins_unchanged'] = True
                result['endpoint_success'] = False
                result['observed_outcome'] = 'consumer_attribute_failure'
                if result['metadata_stable']:
                    result['status'] = 'complete'
            except Exception as guard_error:
                result['post_failure_guard_error'] = str(guard_error)
    finally:
        sys.setprofile(original_profile)
        result['warnings'] = [{'category': w.category.__name__, 'message': str(w.message),
                               'filename': w.filename, 'line': w.lineno} for w in caught]
        result['finished_utc'] = utc()
    write_new(output / f'{provider_id}-{workflow}.json', result)
    print(json.dumps({'cell': f'{provider_id}-{workflow}', 'status': result['status']}))
    return 0 if result['status'] == 'complete' else 1


def run(output: Path) -> int:
    public.verify_prepared(output)
    public.claim_attempt(output, 'run', ['result.json'])
    prepared_path = output / 'prepared.json'
    prepared = json.loads(prepared_path.read_text())
    verify_inputs(prepared)
    expected_outputs = [output / 'result.json'] + [
        output / f'{row["provider"]}-{row["workflow"]}.json' for row in prepared['matrix']]
    if any(path.exists() or path.is_symlink() for path in expected_outputs):
        raise RuntimeError('Existing outcome receipt: refuse to rerun or reuse old cells')
    review_seal_before = verify_review_seal()
    seal = pin(prepared_path)
    cells = []
    for row in prepared['matrix']:
        command = [sys.executable, '-B', str(Path(__file__).resolve()), 'cell', '--output', str(output),
                   '--provider', row['provider'], '--workflow', row['workflow']]
        env = {k: v for k, v in os.environ.items()
               if k not in ('PYTEST_ADDOPTS', 'PYTEST_PLUGINS', 'PYTHONPATH', 'PYTHONHOME')
               and not k.startswith('PIP_')}
        env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                   PIP_NO_INDEX='1', PIP_DISABLE_PIP_VERSION_CHECK='1', PIP_CONFIG_FILE=os.devnull)
        try:
            process = subprocess.run(command, env=env, cwd=output, text=True, capture_output=True,
                                     timeout=90, check=False)
            handle = {'command': command, 'exit_code': process.returncode,
                      'stdout': process.stdout, 'stderr': process.stderr}
        except subprocess.TimeoutExpired:
            handle = {'command': command, 'timed_out': True}
        path = output / f'{row["provider"]}-{row["workflow"]}.json'
        receipt = json.loads(path.read_text()) if path.exists() else {'status': 'missing', **row}
        valid = (handle.get('exit_code') == 0 and receipt['status'] == 'complete'
                 and receipt.get('provider') == row['provider'] and receipt.get('workflow') == row['workflow']
                 and receipt.get('prepared_sha256') == seal['sha256'])
        cells.append({'handle': handle, 'receipt': receipt, 'valid_complete': valid})
    verify_inputs(prepared)
    review_seal_after = verify_review_seal()
    if pin(prepared_path) != seal:
        raise RuntimeError('Prepared predictions changed during workflow run')
    pip_cells = [cell['receipt'] for cell in cells if cell['receipt']['workflow'] == 'pip_list']
    aggregate = {'closed_utc': utc(), 'prepared_sha256': seal['sha256'], 'cells': cells,
                 'complete_cells': sum(c['valid_complete'] for c in cells),
                 'pip_output_equal': (len(pip_cells) == 3 and all('output' in c for c in pip_cells)
                                      and all(c['output'] == pip_cells[0]['output'] for c in pip_cells)),
                 'all_source_pins_unchanged': True, 'primary_scoring_not_invoked': True,
                 'review_seal_before': review_seal_before, 'review_seal_after': review_seal_after,
                 'human_reference': False, 'differential_failure_validation': 'endpoint-only; inspect actual outcomes',
                 'scope': prepared['scope']}
    write_new(output / 'result.json', aggregate)
    print(json.dumps({k: aggregate[k] for k in ('complete_cells', 'pip_output_equal', 'prepared_sha256')}))
    return 0 if aggregate['complete_cells'] == 6 and aggregate['pip_output_equal'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare', 'run', 'cell'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--provider', choices=PROVIDERS)
    parser.add_argument('--workflow', choices=('rosidl_pytest', 'pip_list'))
    args = parser.parse_args()
    output_dir = args.output.expanduser().resolve()
    public.check_output(output_dir)
    if output_dir.is_relative_to(ROOT):
        parser.error('Outputs must be outside the P5 project root')
    if args.mode == 'prepare':
        prepare(output_dir)
    elif args.mode == 'run':
        sys.exit(run(output_dir))
    else:
        if not args.provider or not args.workflow:
            parser.error('Cell requires provider and workflow')
        sys.exit(cell(output_dir, args.provider, args.workflow))
