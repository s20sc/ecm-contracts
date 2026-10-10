"""Portable, guarded entry to original seven-case late replay; no original main call."""
from __future__ import annotations

import argparse
import copy
import dataclasses
import enum
import glob
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
import sysconfig
import traceback
from datetime import datetime, timezone
from types import ModuleType
from typing import Any

HELPERS = ('baselines_v2', 'contract_checker', 'canonical', 'qos_literal',
           'frame_literal', 'adjudication_guard')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def differences(a: Any, b: Any, path: str = '') -> list[dict]:
    if isinstance(a, dict) and isinstance(b, dict):
        changes = []
        for key in sorted(a.keys() | b.keys()):
            sub = path + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in a or key not in b:
                changes.append({'path': sub, 'before_present': key in a,
                                'after_present': key in b, 'before': a.get(key), 'after': b.get(key)})
            else:
                changes.extend(differences(a[key], b[key], sub))
        return changes
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b))
                for d in differences(x, y, path + '/' + str(i))]
    return [] if type(a) is type(b) and a == b else [{'path': path, 'before': a, 'after': b}]


def contained_file(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError('Seal path must be a clean relative path: ' + relative)
    path = (root / rel).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Input escapes public root or is not a file: ' + relative)
    return path


class LogicalProject:
    """Map only explicitly sealed old logical paths. Never spoof source filenames."""
    def __init__(self, aliases: dict[str, Path]):
        self.aliases = aliases

    def __truediv__(self, relative: str) -> Path:
        if relative not in self.aliases:
            raise RuntimeError('Unmapped original project read: ' + relative)
        return self.aliases[relative]


class ReadOnlyGuard:
    def __init__(self, allowed: set[Path]):
        self.enabled = False
        self.allowed = allowed
        self.stdlib = Path(sysconfig.get_path('stdlib')).resolve()
        self.package_dirs = {Path(sysconfig.get_path(k)).resolve() for k in ('purelib', 'platlib')}
        self.reads: set[str] = set()

    def __call__(self, event: str, args: tuple) -> None:
        if not self.enabled:
            return
        if event == 'open':
            filename, mode, flags = args
            if ((isinstance(mode, str) and any(c in mode for c in 'wax+')) or
                    (isinstance(flags, int) and flags &
                     (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))):
                raise RuntimeError('Write denied during guarded replay')
            if isinstance(filename, (str, bytes, os.PathLike)):
                path = Path(os.fsdecode(filename)).resolve()
                runtime = path.is_relative_to(self.stdlib) and not any(
                    path.is_relative_to(p) for p in self.package_dirs)
                if path not in self.allowed and not runtime:
                    raise RuntimeError('Unsealed read denied: ' + str(path))
                self.reads.add(str(path))
        if event.startswith(('socket.', 'subprocess.', 'ctypes.')) or (
                event.startswith('os.') and event not in {'os.listdir', 'os.scandir', 'os.walk'}):
            raise RuntimeError('External execution, network or mutation denied: ' + event)


class Identity:
    def __init__(self, expected: dict[Path, str], public_root: Path):
        self.expected = expected
        self.public_root = public_root
        self.records: dict[str, dict] = {}

    def observe(self, path: Path, module: str, function: str | None) -> None:
        path = path.resolve()
        if path not in self.expected or sha(path) != self.expected[path]:
            raise RuntimeError('Runtime source identity mismatch: ' + str(path))
        key = str(path)
        if key not in self.records:
            self.records[key] = {'actual_file': key, 'actual_sha256': sha(path),
                                 'expected_sha256': self.expected[path], 'module_names': [],
                                 'loaded': True, 'function_calls': {}}
        rec = self.records[key]
        if module not in rec['module_names']:
            rec['module_names'].append(module)
        if function:
            rec['function_calls'][function] = rec['function_calls'].get(function, 0) + 1

    def profile(self, frame: Any, event: str, arg: Any) -> None:
        if event != 'call' or frame.f_code.co_filename.startswith('<'):
            return
        path = Path(frame.f_code.co_filename).resolve()
        if path not in self.expected:
            if path.is_relative_to(self.public_root):
                raise RuntimeError('Unsealed runtime module: ' + str(path))
            return
        actual = frame.f_globals.get('__file__')
        if actual is None or Path(actual).resolve() != path:
            raise RuntimeError('Code filename and actual module __file__ disagree')
        self.observe(path, frame.f_globals.get('__name__', 'unknown'),
                     None if frame.f_code.co_name == '<module>' else frame.f_code.co_name)

    def report(self) -> list[dict]:
        return [{**v, 'function_execution_observed': bool(v['function_calls']),
                 'status': 'function_execution_observed' if v['function_calls'] else 'loaded_only'}
                for v in self.records.values()]


class SourceOnlyLoader:
    def __init__(self, path: Path, expected: str):
        self.path, self.expected = path, expected

    def create_module(self, spec: Any) -> None:
        return None

    def exec_module(self, module: ModuleType) -> None:
        data = self.path.read_bytes()
        if hashlib.sha256(data).hexdigest() != self.expected:
            raise RuntimeError('Source changed immediately before compilation')
        module.__file__ = str(self.path)
        exec(compile(data, str(self.path), 'exec'), module.__dict__)


class SourceOnlyFinder:
    def __init__(self, paths: dict[str, Path], expected: dict[Path, str]):
        self.paths, self.expected = paths, expected

    def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> Any:
        if fullname not in self.paths:
            return None
        source = self.paths[fullname]
        return importlib.util.spec_from_loader(fullname, SourceOnlyLoader(source, self.expected[source]),
                                              origin=str(source))


def load_module(name: str, path: Path, expected: str) -> ModuleType:
    if name in sys.modules:
        raise RuntimeError('Fresh interpreter required: ' + name)
    spec = importlib.util.spec_from_loader(name, SourceOnlyLoader(path, expected), origin=str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def dump_new(path: Path, value: Any) -> None:
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def run(args: argparse.Namespace) -> dict:
    root = args.public_root.resolve(strict=True)
    output = args.output_dir.resolve()
    source_root = Path(__file__).resolve().parent
    if any(output.is_relative_to(p) for p in (root, source_root)):
        raise ValueError('Output must be external to public inputs and delivery source')
    if not output.parent.is_dir():
        raise ValueError('Output parent must already exist')
    output.mkdir(exist_ok=False)
    identity = None
    guard = None
    try:
        seal_path = args.seal.resolve(strict=True)
        seal_raw = seal_path.read_bytes()
        if hashlib.sha256(seal_raw).hexdigest() != args.seal_sha256:
            raise ValueError('Public input seal hash differs from explicitly trusted digest')
        seal = json.loads(seal_raw)
        if seal['schema'] != 1:
            raise ValueError('Unsupported seal schema')
        files = {rel: contained_file(root, rel) for rel in seal['files']}
        before = {rel: sha(path) for rel, path in files.items()}
        if before != seal['files']:
            raise ValueError('Public input hash mismatch')
        mode = seal['modes'][args.mode]
        paths = {rel: files[p] for rel, p in mode['modules'].items()}
        freeze_path = files[mode['freeze']]
        freeze = read(freeze_path)
        expected = {}
        binding = {}
        for rel, path in paths.items():
            digest = freeze['files'].get(rel) or freeze['ledgers'][rel]['sha256']
            if sha(path) != digest:
                raise ValueError('Mode-specific freeze binding mismatch: ' + rel)
            expected[path] = digest
            if rel != 'adjudication_guard.py':
                binding[rel] = digest
        binding['FREEZE.json'] = sha(freeze_path)
        replay_path = files[seal['replay']]
        expected[replay_path] = seal['files'][seal['replay']]
        if any(name in sys.modules for name in HELPERS):
            raise RuntimeError('Fresh interpreter required; helper already loaded')
        aliases = {rel: files[target] for rel, target in seal['project_aliases'].items()}
        data = read(files[seal['inputs']])
        reference = read(files[mode['reference']])
        runner = Path(__file__).resolve()
        runner_hash = sha(runner)
        expected[runner] = runner_hash
        allowed = set(files.values()) | {runner, seal_path}
        guard = ReadOnlyGuard(allowed)
        sys.addaudithook(guard)
        identity = Identity(expected, root)
        finder = SourceOnlyFinder({p.stem: p for p in paths.values() if p.stem in HELPERS}, expected)
        sys.dont_write_bytecode = True
        sys.meta_path.insert(0, finder)
        old_path = sys.path[:]
        guard.enabled = True
        try:
            sys.setprofile(identity.profile)
            original = load_module('delivery_original_late', replay_path, expected[replay_path])
            original.ROOT = LogicalProject(aliases)
            def selected_modules() -> tuple[ModuleType, ModuleType, dict]:
                assembler = load_module('delivery_late_assemble', paths['assemble.py'], expected[paths['assemble.py']])
                scorer = load_module('delivery_late_scoring', paths['scoring.py'], expected[paths['scoring.py']])
                return assembler, scorer, binding.copy()
            original.frozen_modules = selected_modules
            result = original.evaluate(data)
            for name in HELPERS:
                module = sys.modules.get(name)
                if module is not None:
                    identity.observe(Path(module.__file__), name, None)
            after = {rel: sha(path) for rel, path in files.items()}
            if after != before or sha(runner) != runner_hash or sha(seal_path) != args.seal_sha256:
                raise RuntimeError('Protected input or delivery code changed')
        finally:
            sys.setprofile(None)
            guard.enabled = False
            sys.meta_path.remove(finder)
            sys.path[:] = old_path
        changes = differences(reference, result)
        receipt = {'status': 'matched' if not changes else 'mismatch', 'mode': args.mode,
                   'observed_utc': datetime.now(timezone.utc).isoformat(), 'runtime': sys.version,
                   'runner_sha256': runner_hash, 'public_seal_sha256': args.seal_sha256,
                   'seal_parsed_from_same_hashed_bytes': True,
                   'resolved_roots': {'public_inputs': str(root), 'delivery_source': str(source_root),
                                      'external_output': str(output), 'seal': str(seal_path)},
                   'original_replay_source_sha256': expected[replay_path],
                   'declared_adaptations': ['ROOT replaced by exact public logical-path aliases',
                                            'frozen_modules selects mode-specific original byte sources',
                                            'public input seal replaces private manifest receipt authentication',
                                            'new external result; original main not called'],
                   'original_main_called': False, 'target_bytecode_used': False,
                   'inputs_before': before, 'inputs_after': after, 'inputs_unchanged': before == after,
                   'runtime_identity': identity.report(), 'guarded_reads': sorted(guard.reads),
                   'reference': mode['reference'], 'reference_sha256': sha(files[mode['reference']]),
                   'comparison': {'whole_json_equal': not changes, 'rows_equal': result['rows'] == reference['rows'],
                                  'census_equal': result['outcome_census'] == reference['outcome_census'],
                                  'aggregate_equal': result['aggregate_source_reported_failures'] == reference['aggregate_source_reported_failures'],
                                  'changed_fields': changes},
                   'case_comparisons': [{'case_id': row['case_id'], 'equal': row == reference['rows'][i]}
                                        for i, row in enumerate(result['rows'])],
                   'scope': 'Coordinator-built post-outcome source-slice replay; not original S2, new runtime evidence, independent human validation or expanded H1.'}
        dump_new(output/'results.json', result)
        dump_new(output/'receipt.json', receipt)
        if changes:
            raise RuntimeError('Scientific output differs from mode-specific retained result')
        return receipt
    except Exception as exc:
        if guard:
            guard.enabled = False
        dump_new(output/'failure.json', {'status': 'incomplete', 'exception_type': type(exc).__name__,
                                        'message': str(exc), 'traceback': traceback.format_exc(),
                                        'partial_runtime_identity': identity.report() if identity else []})
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-root', type=Path, required=True)
    parser.add_argument('--seal', type=Path, default=Path(__file__).with_name('public-input-seal.json'))
    parser.add_argument('--seal-sha256', required=True, help='Trusted digest from reviewed delivery, not silently recomputed')
    parser.add_argument('--mode', choices=('historical', 'current'), required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    receipt = run(args)
    print(json.dumps({'status': receipt['status'], 'mode': args.mode,
                      'cases': len(receipt['case_comparisons']), 'output': str(args.output_dir)}))


if __name__ == '__main__':
    main()
