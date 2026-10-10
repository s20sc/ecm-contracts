"""Content-bound public replay inputs; no private review-tree dependencies."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'public-inputs.json'


def config_path() -> Path:
    raw = os.environ.get('ECM_REPLAY_CONFIG')
    if not raw:
        raise RuntimeError('Set ECM_REPLAY_CONFIG to the replay configuration JSON')
    return Path(raw).expanduser().resolve(strict=True)


def configuration() -> dict:
    value = json.loads(config_path().read_text())
    if value.get('schema') != 1:
        raise ValueError('Unsupported replay configuration schema')
    return value


def configured_path(name: str) -> Path:
    raw = configuration()[name]
    p = Path(raw).expanduser()
    return (p if p.is_absolute() else config_path().parent / p).resolve()


def roots() -> dict[str, Path]:
    return {'runtime': HERE, **{k: configured_path(k) for k in ('package', 'retained', 'intake')}}


def previous_contrast() -> Path:
    return configured_path('previous_contrast')


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def safe_child(root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or '..' in pure.parts or '\\' in relative:
        raise ValueError(f'Unsafe manifest path: {relative}')
    p = root / relative
    if not p.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Manifest path escapes input root: {relative}')
    return p


def check_output(output: Path) -> None:
    resolved = output.resolve()
    for root in roots().values():
        if resolved == root or resolved.is_relative_to(root):
            raise ValueError('Output must be outside every input root')


def verify() -> dict:
    raw = MANIFEST.read_bytes()
    manifest = json.loads(raw)
    if manifest.get('schema') != 1 or not manifest.get('files'):
        raise ValueError('Empty or unsupported public input manifest')
    locations = roots()
    seen = set()
    for row in manifest['files']:
        key = (row['root'], row['relative'])
        if key in seen:
            raise ValueError('Duplicate input manifest row')
        seen.add(key)
        path = safe_child(locations[row['root']], row['relative'])
        if not path.is_file() or digest(path) != row['sha256']:
            raise RuntimeError(f'Public input missing or changed: {key}')
    for scope in manifest.get('exact_python_trees', []):
        root = (locations[scope['root']] if scope['relative'] == '.'
                else safe_child(locations[scope['root']], scope['relative']))
        actual = {p.relative_to(locations[scope['root']]).as_posix()
                  for p in root.rglob('*.py') if '__pycache__' not in p.parts}
        expected = set(scope['paths'])
        if actual != expected:
            raise RuntimeError(f'Python source inventory changed: {scope["relative"]}')
    if MANIFEST.read_bytes() != raw:
        raise RuntimeError('Public manifest changed during verification')
    return {'manifest': str(MANIFEST), 'sha256': hashlib.sha256(raw).hexdigest(),
            'verified_files': len(seen), 'guard_scope': 'public inputs, not private review tree',
            'historical_reproduction_claim': False}


def check_environment() -> None:
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError('Replay requires Python 3.11; records retain exact patch version')
    import importlib.metadata
    for name, expected in {'pip': '25.0.1', 'pytest': '9.0.3', 'pluggy': '1.6.0'}.items():
        if importlib.metadata.version(name) != expected:
            raise RuntimeError(f'Replay requires {name}=={expected}; no installation performed')


def seal_prepared(output: Path) -> None:
    with (output / 'prepared.sha256').open('x') as stream:
        stream.write(digest(output / 'prepared.json') + '\n')


def verify_prepared(output: Path) -> None:
    if digest(output / 'prepared.json') != (output / 'prepared.sha256').read_text().strip():
        raise RuntimeError('Prepared receipt changed after pre-execution seal')


def claim_attempt(output: Path, name: str, outcomes: list[str]) -> None:
    check_output(output)
    if any((output / item).exists() or (output / item).is_symlink() for item in outcomes):
        raise RuntimeError('Existing outcome receipt: refuse endpoint retry')
    with (output / (name + '.started.json')).open('x') as stream:
        json.dump({'scope': 'delivery replay attempt; preserve even if interrupted'}, stream)
        stream.write('\n')
