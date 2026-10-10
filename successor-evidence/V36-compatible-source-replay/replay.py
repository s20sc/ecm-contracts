"""Read-only retained-source replay; require a new external output file."""
from __future__ import annotations

from collections import Counter
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Iterator
import warnings

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SNAP = Path('/historical/runs/p5-v30-author-reproduction-001/'
            'work/experiments/pathb_v2/s2_work/tasks')
PROTOCOL_SHA = 'f56eb6ee782e05148c267c1c17c11cbbc22805029859f9efcba1a87bb4155ba4'
PROVIDERS = {'u0395': 'Lib/importlib/metadata.py',
             'u0394': 'Lib/importlib/metadata/__init__.py'}
CONSUMERS = {task: 'rosidl_cli/rosidl_cli/entry_points.py'
             for task in ('u0396', 'u0397')}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(path: Path) -> dict:
    if not path.is_file():
        return {'exists': False}
    before = path.stat()
    digest = sha(path.read_bytes())
    after = path.stat()
    if before != after:
        raise RuntimeError('Input changed while hashing')
    return {'exists': True, 'sha256': digest, 'device': after.st_dev,
            'inode': after.st_ino, 'size': after.st_size,
            'mtime_ns': after.st_mtime_ns}


def inventory_summary(items: dict[Path, dict]) -> dict:
    private_rows = sorted((sha(str(path).encode()), value)
                          for path, value in items.items())
    return {'file_count': sum(item.get('exists', False) for item in items.values()),
            'path_count': len(items),
            'path_identity_and_content_sha256': sha(json.dumps(
                private_rows, sort_keys=True, separators=(',', ':')).encode())}


def module_name(obj: object) -> str:
    cls = obj if isinstance(obj, type) else type(obj)
    return f'{cls.__module__}.{cls.__qualname__}'


class ImportOnlyFinder:
    """Delegate original imports while excluding its distribution resolver."""
    def __init__(self, finder: object) -> None:
        self.finder = finder

    def __getattr__(self, key: str) -> object:
        if key == 'find_distributions':
            raise AttributeError(key)
        return getattr(self.finder, key)


@contextmanager
def provider_discovery(provider: ModuleType) -> Iterator[None]:
    original = sys.meta_path[:]
    try:
        sys.meta_path[:] = [provider.MetadataPathFinder] + [
            ImportOnlyFinder(finder) for finder in original]
        yield
    finally:
        sys.meta_path[:] = original


def load(task: str, relative: str, package: bool = False) -> ModuleType:
    path = SNAP / task / 'snapshot' / relative
    name = f'_v36_retained_{task}'
    locations = [str(path.parent)] if package else None
    spec = importlib.util.spec_from_file_location(
        name, path, submodule_search_locations=locations)
    if spec is None or spec.loader is None:
        raise ImportError(f'No loader for {task}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main(output_path: Path) -> int:
    # Reject unsafe outputs before reading protocol, source pins or metadata.
    output_path = output_path.expanduser()
    if (not output_path.parent.is_dir() or output_path.exists()
            or output_path.is_symlink()):
        print('Output requires an existing parent and nonexistent target.', file=sys.stderr)
        return 1
    output_path = output_path.resolve()
    if output_path.is_relative_to(ROOT):
        print('Output must be outside the P5 project root.', file=sys.stderr)
        return 1
    result: dict = {
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'retained source on host3.11; real host metadata; same consumer two revisions',
        'python_executable': sys.executable, 'python_version': sys.version,
        'dont_write_bytecode': sys.dont_write_bytecode, 'sys_path_before': sys.path[:],
        'run_kind': 'external_output_provenance_hardened_rerun',
        'output_path': str(output_path),
        'process_command': list(sys.orig_argv),
        'first_run_receipt_sha256': sha((HERE / 'first-run-result.json').read_bytes()),
        'protocol_sha256': sha((HERE / 'protocol.md').read_bytes()),
        'script_sha256': sha(Path(__file__).read_bytes()),
        'group': 'console_scripts', 'plugins_executed': 0,
        'bindings': 'unchanged consumer module importlib_metadata explicitly rebound to retained provider',
        'source_verification': [], 'cells': [],
        'independent_clients': False, 'checker_executed': False,
        'host_dependencies': ['host stdlib import machinery, configparser, pathlib, email, zipfile, typing',
                              'real current sys.path distribution metadata'],
    }
    mappings: dict[str, str] = {}
    source_paths: dict[Path, dict] = {}
    metadata_before: dict[Path, dict] = {}
    actual_read_before: dict[Path, dict] = {}
    metadata_directories: dict[Path, tuple[int, int]] = {}
    read_calls: Counter[str] = Counter()
    original_profile = sys.getprofile()
    try:
        if result['protocol_sha256'] != PROTOCOL_SHA:
            raise RuntimeError('Predeclared protocol changed')
        pins = json.loads((ROOT / 'V32-EMSE/replication_package/snapshots.json').read_text())
        targets = dict(PROVIDERS, **CONSUMERS)
        for task, relative in targets.items():
            source = SNAP / task / 'snapshot' / relative
            sources = sorted(source.parent.glob('*.py')) if task == 'u0394' else [source]
            entries = {item['path']: item for item in pins[task]['entries']}
            for path in sources:
                rel = str(path.relative_to(SNAP / task / 'snapshot'))
                actual = sha(path.read_bytes())
                expected = entries[rel]['sha256']
                source_paths[path] = fingerprint(path)
                result['source_verification'].append({
                    'task': task, 'relative_path': rel, 'sha256': actual,
                    'matches_pin': actual == expected,
                    'before': source_paths[path]})
                if actual != expected:
                    raise RuntimeError(f'Source pin mismatch: {task}/{rel}')
        providers = {task: load(task, path, task == 'u0394')
                     for task, path in PROVIDERS.items()}
        consumers = {task: load(task, path) for task, path in CONSUMERS.items()}
        # Inventory candidate metadata files and directory identity before cells.
        # Read-call monitoring below distinguishes actually read files from this inventory.
        for provider in providers.values():
            with provider_discovery(provider):
                for dist in provider.Distribution.discover():
                    base = Path(dist._path)
                    stat = base.stat()
                    metadata_directories[base] = (stat.st_dev, stat.st_ino)
                    for filename in ('entry_points.txt', 'METADATA', 'PKG-INFO'):
                        path = base / filename
                        metadata_before[path] = fingerprint(path)
        result['metadata_inventory_before'] = inventory_summary(metadata_before)
        result['distribution_directory_count'] = len(metadata_directories)
        read_codes = {provider.PathDistribution.read_text.__code__
                      for provider in providers.values()}

        def observe_reads(frame: object, event: str, arg: object) -> None:
            if event != 'call' or frame.f_code not in read_codes:
                return
            local = frame.f_locals
            filename = local['filename']
            read_calls[filename] += 1
            path = Path(local['self']._path) / filename
            if path not in actual_read_before:
                actual_read_before[path] = fingerprint(path)
                if path not in metadata_before:
                    # Unexpected files cannot claim a full-run preinventory pin.
                    raise RuntimeError('Provider read metadata outside preinventoried inputs')
            if actual_read_before[path] != metadata_before[path]:
                raise RuntimeError('Metadata changed before provider read')

        result['loaded_provider_module_paths'] = {
            name: mod.__file__ for name, mod in sys.modules.items()
            if name.startswith(('_v36_retained_u0394', '_v36_retained_u0395'))
            and getattr(mod, '__file__', None)}
        result['default_discovery_provenance'] = {}
        for task, provider in providers.items():
            try:
                counts = Counter(module_name(dist) for dist in provider.Distribution.discover())
                result['default_discovery_provenance'][task] = dict(counts)
            except Exception as exc:
                result['default_discovery_provenance'][task] = {'exception_type': type(exc).__name__}
        for ptask, provider in providers.items():
            for ctask, consumer in consumers.items():
                cell: dict = {'id': f'{ptask}x{ctask}', 'provider': ptask, 'consumer': ctask}
                consumer.importlib_metadata = provider
                cell['binding_module'] = provider.__name__
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always')
                    try:
                        with provider_discovery(provider):
                            dist_classes = Counter(module_name(dist)
                                                   for dist in provider.Distribution.discover())
                            cell['distribution_classes'] = dict(dist_classes)
                            if not dist_classes or any(
                                not name.startswith(provider.__name__ + '.') for name in dist_classes):
                                raise RuntimeError('Discovery did not use retained provider distributions')
                            resolver_names = [f'{fn.__module__}.{fn.__qualname__}'
                                              for fn in provider.Distribution._discover_resolvers()]
                            cell['distribution_resolvers'] = resolver_names
                            sys.setprofile(observe_reads)
                            api_result = provider.entry_points()
                            cell['entry_points_result_class'] = module_name(api_result)
                            cell['get_available'] = hasattr(api_result, 'get')
                            cell['select_available'] = hasattr(api_result, 'select')
                            mapping = consumer.get_entry_points('console_scripts')
                            ep_classes = Counter(module_name(ep) for ep in mapping.values())
                            cell['entry_point_classes'] = dict(ep_classes)
                            if any(not name.startswith(provider.__name__ + '.') for name in ep_classes):
                                raise RuntimeError('Consumer returned non-retained EntryPoint objects')
                            canonical = json.dumps(
                                {name: {'group': ep.group, 'value': ep.value}
                                 for name, ep in sorted(mapping.items())},
                                sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                            mappings[cell['id']] = canonical
                            cell.update(status='ok', mapping_count=len(mapping),
                                        mapping_sha256=sha(canonical.encode()), nonempty=bool(mapping))
                    except Exception as exc:
                        cell.update(status='exception', exception_type=type(exc).__name__,
                                    exception_message=str(exc)[:240])
                    finally:
                        sys.setprofile(original_profile)
                    cell['warnings'] = [
                        {'category': item.category.__name__, 'message': str(item.message),
                         'filename': item.filename, 'lineno': item.lineno}
                        for item in caught]
                result['cells'].append(cell)
        result['full_mapping_pairwise_equality'] = {
            f'{left}=={right}': mappings[left] == mappings[right]
            for left, right in itertools.combinations(mappings, 2)}
        result['all_four_successful_nonempty'] = len(mappings) == 4 and all(
            cell.get('nonempty', False) for cell in result['cells'])
        metadata_after = {path: fingerprint(path) for path in metadata_before}
        actual_read_after = {path: fingerprint(path) for path in actual_read_before}
        result['metadata_inventory_after'] = inventory_summary(metadata_after)
        result['metadata_inventory_stable'] = metadata_before == metadata_after
        result['actual_read_inputs_before'] = inventory_summary(actual_read_before)
        result['actual_read_inputs_after'] = inventory_summary(actual_read_after)
        result['actual_read_inputs_stable'] = actual_read_before == actual_read_after
        result['provider_read_text_calls_by_filename'] = dict(read_calls)
        result['distribution_directories_stable'] = all(
            (path.stat().st_dev, path.stat().st_ino) == identity
            for path, identity in metadata_directories.items())
        for item in result['source_verification']:
            path = SNAP / item['task'] / 'snapshot' / item['relative_path']
            item['after'] = fingerprint(path)
            item['after_matches_pin'] = item['after']['sha256'] == item['sha256']
            item['stable'] = item['before'] == item['after']
        result['sys_path_after'] = sys.path[:]
        result['sys_path_stable'] = result['sys_path_before'] == result['sys_path_after']
        result['source_inputs_stable'] = all(item['stable'] and item['after_matches_pin']
                                              for item in result['source_verification'])
        stable = all(result[name] for name in (
            'metadata_inventory_stable', 'actual_read_inputs_stable',
            'distribution_directories_stable', 'sys_path_stable', 'source_inputs_stable'))
        result['status'] = 'source_replay_complete' if result['all_four_successful_nonempty'] and stable else 'partial'
    except Exception as exc:
        result.update(status='partial', setup_exception_type=type(exc).__name__,
                      setup_exception_message=str(exc)[:240])
    finally:
        sys.setprofile(original_profile)
    result['finished_utc'] = datetime.now(timezone.utc).isoformat()
    # Exclusive creation also protects against a target appearing after preflight.
    with output_path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': result['status'], 'cells': len(result['cells'])}))
    return 0 if result['status'] == 'source_replay_complete' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='New JSON path outside P5 project; parent must already exist')
    args = parser.parse_args()
    raise SystemExit(main(args.output))
