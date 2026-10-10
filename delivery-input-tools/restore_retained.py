"""Restore only the retained files pinned by the public replay manifest."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def validate_relative(value: str) -> PurePosixPath:
    p = PurePosixPath(value)
    if p.is_absolute() or len(p.parts) < 3 or '..' in p.parts or '\\' in value:
        raise ValueError('Invalid retained relative path')
    if not re.fullmatch(r'u\d{4}', p.parts[0]) or p.parts[1] not in ('snapshot', 'recon'):
        raise ValueError('Unexpected retained source layout')
    return p


def restore(manifest_path: Path, archive: Path, package: Path, output: Path) -> dict:
    manifest_path = manifest_path.resolve(strict=True); archive = archive.resolve(strict=True)
    package = package.resolve(strict=True)
    if output.exists() or output.is_symlink(): raise FileExistsError('Use a new output directory')
    output = output.resolve()
    if output.is_relative_to(package) or output.is_relative_to(manifest_path.parent):
        raise ValueError('Output must be outside input directories')
    raw = manifest_path.read_bytes(); manifest = json.loads(raw)
    if manifest.get('schema') != 1: raise ValueError('Unsupported manifest schema')
    rows = [row for row in manifest['files'] if row['root'] == 'retained']
    if not rows: raise ValueError('No retained inputs in public manifest')
    seen = set()
    for row in rows:
        rel = validate_relative(row['relative']).as_posix()
        if rel in seen or not re.fullmatch(r'[0-9a-f]{64}', row['sha256']):
            raise ValueError('Duplicate path or invalid SHA256')
        seen.add(rel)
    expected_archive = manifest['archive_sha256']
    if digest(archive) != expected_archive: raise ValueError('Snapshot archive hash mismatch')
    output.mkdir(parents=True, exist_ok=False)
    written = []
    try:
        with zipfile.ZipFile(archive) as z:
            for row in rows:
                rel = validate_relative(row['relative']); target = output / str(rel)
                if rel.parts[1] == 'snapshot':
                    data = z.read('blobs/' + row['sha256'])
                    origin = 'snapshot archive blob'
                else:
                    source = package / 'experiments/pathb_v2/s2_work/tasks' / str(rel)
                    if not source.resolve().is_relative_to(package): raise ValueError('Reconstruction escapes package')
                    data = source.read_bytes(); origin = 'scientific package reconstruction'
                if hashlib.sha256(data).hexdigest() != row['sha256']:
                    raise ValueError(f'Retained content mismatch: {rel}')
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as stream: stream.write(data)
                written.append({'relative': str(rel), 'sha256': row['sha256'], 'bytes': len(data), 'origin': origin})
        if manifest_path.read_bytes() != raw or digest(archive) != expected_archive:
            raise ValueError('Inputs changed during restore')
        result = {'complete': True, 'scope': 'selected replay inputs only, not full snapshot materialization',
                  'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'archive_sha256': expected_archive,
                  'file_count': len(written), 'bytes': sum(row['bytes'] for row in written), 'files': written}
        with (output / 'restore-receipt.json').open('x') as stream: json.dump(result, stream, indent=2)
        return result
    except Exception as exc:
        with (output / 'restore-failure.json').open('x') as stream:
            json.dump({'complete': False, 'error': str(exc), 'partial_files': written}, stream, indent=2)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = restore(args.manifest, args.archive, args.package, args.out)
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}))


if __name__ == '__main__': main()
