"""Portable entry point for fresh local replay; never rewrites historical receipts."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import subprocess
import sys

import public_integrity as public

SCRIPTS = {'boundary': 'V38-workflow-boundary/run_boundary.py',
           'contrast': 'V39-consumer-contrast/run_contrast.py',
           'adaptive': 'V41-original-adaptive-client/run_adaptive.py'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workflow', choices=(*SCRIPTS, 'verify'))
    parser.add_argument('mode', choices=('prepare', 'run'), nargs='?')
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    os.environ['ECM_REPLAY_CONFIG'] = str(args.config.expanduser().resolve(strict=True))
    if args.workflow == 'verify':
        import json
        print(json.dumps(public.verify()))
        return 0
    if args.mode is None or args.output is None:
        parser.error('Replay needs prepare/run and --output')
    output = args.output.expanduser().resolve()
    public.check_output(output)
    public.check_environment()
    public.verify()
    env = {k: v for k, v in os.environ.items()
           if k not in ('PYTHONPATH', 'PYTHONHOME', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS')}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    script = Path(__file__).resolve().parent / 'successor-evidence' / SCRIPTS[args.workflow]
    return subprocess.run([sys.executable, '-B', str(script), args.mode, '--output', str(output)],
                          env=env, check=False).returncode


if __name__ == '__main__':
    sys.exit(main())
