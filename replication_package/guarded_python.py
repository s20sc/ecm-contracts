"""Run packaged deterministic Python with author-home reads/network disabled."""
import os
from pathlib import Path
import runpy
import sys

sys.dont_write_bytecode = True
root = Path(sys.argv[1]).resolve()
script = Path(sys.argv[2]).resolve()
args = sys.argv[3:]
if not script.is_relative_to(root):
    raise SystemExit('Script must be inside the reproduction output tree')
blocked = []

def audit(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system'}:
        raise PermissionError('Offline reproduction forbids ' + event)
    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).resolve()
        # No author's home can supply missing data, code, or secret configuration.
        # The only allowed home path is the explicitly selected work output tree.
        if (str(path).startswith('/Users/') or str(path).startswith('/home/')) and not path.is_relative_to(root):
            blocked.append(str(path))
            raise PermissionError('Author-home dependency forbidden: ' + str(path))

sys.addaudithook(audit)
os.chdir(script.parent)
sys.path.insert(0, str(script.parent))
sys.argv = [str(script)] + args
runpy.run_path(str(script), run_name='__main__')
