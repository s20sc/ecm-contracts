"""Public input binding for retained-source compatible-change replay."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

RUNTIME = Path(__file__).resolve().parent
MANIFEST = RUNTIME / 'inputs.json'


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_config(path: Path, raw: bytes | None = None) -> dict[str, Path]:
    path = path.expanduser().resolve(strict=True)
    value = json.loads(path.read_bytes() if raw is None else raw)
    if value.get('schema') != 1:
        raise ValueError('Unsupported configuration schema')
    locations = {'runtime': RUNTIME}
    for key in ('package', 'retained', 'supplement'):
        location = Path(value[key]).expanduser()
        location = (location if location.is_absolute() else path.parent / location).resolve(strict=True)
        if not location.is_dir():
            raise ValueError(f'Input root is not a directory: {key}')
        locations[key] = location
    return locations


def child(root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or '..' in pure.parts or '\\' in relative:
        raise ValueError(f'Unsafe input path: {relative}')
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Input path escapes configured root: {relative}')
    return path


def check_output(path: Path, locations: dict[str, Path]) -> Path:
    if path.is_symlink() or path.exists():
        raise FileExistsError('Use a new output directory; retain prior attempts')
    resolved = path.expanduser().resolve()
    if not resolved.parent.is_dir():
        raise ValueError('Output parent must already exist')
    if any(resolved.is_relative_to(root.resolve()) for root in locations.values()):
        raise ValueError('Output must be outside every input root')
    return resolved


def verify(locations: dict[str, Path]) -> dict:
    raw = MANIFEST.read_bytes()
    manifest = json.loads(raw)
    if manifest.get('schema') != 1 or not manifest.get('files'):
        raise ValueError('Empty or unsupported public manifest')
    seen = set()
    for row in manifest['files']:
        key = (row['root'], row['relative'])
        if key in seen:
            raise ValueError('Duplicate input binding')
        seen.add(key)
        path = child(locations[row['root']], row['relative'])
        if not path.is_file() or digest(path) != row['sha256']:
            raise ValueError(f'Input missing or changed: {key}')
    for tree in manifest.get('exact_python_trees', []):
        root = locations[tree['root']]
        base = root if tree['relative'] == '.' else child(root, tree['relative'])
        actual = {p.relative_to(root).as_posix() for p in base.rglob('*.py')}
        if actual != set(tree['paths']):
            raise ValueError(f'Python inventory changed: {tree["relative"]}')
        # Import machinery can prefer a native extension over a sealed .py file.
        # Neither native code nor sourceless bytecode belongs to this source replay.
        forbidden = {'.pyc', '.pyo', '.so', '.pyd', '.dylib', '.dll'}
        if any(p.is_file() and p.suffix.lower() in forbidden for p in base.rglob('*')):
            raise ValueError(f'Unexpected import binary in sealed source tree: {tree["relative"]}')
    if raw != MANIFEST.read_bytes():
        raise ValueError('Public manifest changed during verification')
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'files': len(seen)}
