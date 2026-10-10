"""Materialise S2 tasks and source snapshots (PROTOCOL.md Section 6). Steward script.

  python3 materialize.py [--only case_a,case_b]
  python3 materialize.py --dispatch u0004,u0005   (mark tasks handed to S2; their workspaces are then frozen)

For every eligible spec, every unit@revision that a composition needs becomes one task
with an opaque id. The unit's repository is cloned into a scratch directory and
`git archive <revision>` is exported into s2_work/tasks/<task_id>/snapshot/ with no `.git`;
CHANGELOG*, NEWS*, RELEASE* and .github/ are removed. Every task gets its own isolated
workspace s2_work/tasks/<task_id>/ holding only packet.json, S2_PROMPT.md, the snapshot
(or artifact.txt), definition_hash.py and an empty recon/ directory: one S2 run per task,
so no run can compare two revisions or two units. The case <-> task mapping, snapshot
hashes, the commit each revision resolved to, and dispatch status go to ledger/tasks.json,
outside every S2 workspace. A unit is excerpt-described when its spec entry says so (or,
for older specs, when it has no repository); undispatched excerpt tasks follow the artifact.
"""
import glob
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
S2 = os.path.join(HERE, "s2_work")
LEDGER = os.path.join(HERE, "ledger")
STRIP = ("CHANGELOG", "NEWS", "RELEASE")


def seed():
    f = os.path.join(HERE, "FREEZE.json")
    return json.load(open(f))["seed"] if os.path.exists(f) else 20260925


SHA_METHOD = "sha256(relpath + content; symlink -> 'L' + link target, never followed)"


def sha_dir(path):
    """Content hash of a snapshot. A symbolic link is hashed by its target string and never
    followed: a dangling link would otherwise crash the export, and a link that points outside
    the snapshot would make the hash depend on the host."""
    h = hashlib.sha256()
    for root, dirs, files in sorted(os.walk(path)):
        dirs.sort()
        entries = sorted(files + [d for d in dirs if os.path.islink(os.path.join(root, d))])
        for fn in entries:
            p = os.path.join(root, fn)
            h.update(os.path.relpath(p, path).encode())
            if os.path.islink(p):
                h.update(b"L" + os.readlink(p).encode())
            else:
                h.update(open(p, "rb").read())
    return h.hexdigest()


def export(repo, revision, dest):
    """git archive at `revision` into dest; returns (status, resolved commit or None)."""
    tmp = tempfile.mkdtemp(prefix="pbv2_")
    try:
        r = subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", repo, tmp], capture_output=True, text=True)
        if r.returncode != 0:
            return "source_unavailable", None
        r = subprocess.run(["git", "-C", tmp, "rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            r = subprocess.run(["git", "-C", tmp, "rev-parse", "--verify", "--quiet", f"origin/{revision}^{{commit}}"],
                               capture_output=True, text=True)
        if r.returncode != 0:
            return "revision_unresolved", None
        commit = r.stdout.strip()
        os.makedirs(dest, exist_ok=True)
        r = subprocess.run(f"git -C '{tmp}' archive --format=tar '{commit}' | tar -x -C '{dest}'",
                           shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            shutil.rmtree(dest, ignore_errors=True)
            return "revision_unresolved", None
        for root, dirs, files in os.walk(dest):
            for d in list(dirs):
                if d == ".github" or d == ".git":
                    shutil.rmtree(os.path.join(root, d)); dirs.remove(d)
            for fn in files:
                if fn.upper().startswith(STRIP):
                    os.remove(os.path.join(root, fn))
        return "done", commit
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def is_excerpt(unit):
    """Per-unit: described from quoted artifacts (no repository) rather than a snapshot."""
    return bool(unit.get("excerpt")) if unit.get("excerpt") is not None else unit.get("repo") is None


def unit_revisions(spec):
    """(unit, repo, revision, pinned, excerpt) tuples a case needs."""
    need = []
    for u in spec["units"]:
        for which in ("broken", "resolved"):
            rev = u.get(f"{which}_rev")
            if rev and (which == "broken" or (spec.get("resolution") or {}).get("status") in ("observed", "recommended")):
                need.append((u["name"], u.get("repo"), rev, u.get("pinned", False), is_excerpt(u)))
    cba = spec.get("consumer_built_against") or {}
    prov = next((u for u in spec["units"] if u.get("role") == "provider"), None)
    if spec.get("operation") == "UPGRADE" and prov:
        for which in ("broken", "resolved"):
            if cba.get(which):
                need.append((prov["name"], prov.get("repo"), cba[which], True, is_excerpt(prov)))
    return sorted(set(need))


def main():
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    os.makedirs(os.path.join(S2, "tasks"), exist_ok=True)
    os.makedirs(LEDGER, exist_ok=True)
    ledger_path = os.path.join(LEDGER, "tasks.json")
    ledger = json.load(open(ledger_path)) if os.path.exists(ledger_path) else {"tasks": {}, "by_key": {}}
    # Task ids are never reused: a monotone counter, initialised from the highest id present.
    ledger.setdefault("next_id", 1 + max([int(t[1:]) for t in ledger["tasks"]] or [0]))
    tasks = []
    needed = set()
    for f in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        spec = json.load(open(f))
        if not spec.get("eligible") or (only and spec["case_id"] not in only):
            continue
        for unit, repo, rev, pinned, excerpt in unit_revisions(spec):
            key = f"{unit}@{rev}"
            needed.add(key)
            art = os.path.join(HERE, "artifacts", f"{spec['case_id']}.txt")
            if key not in ledger["by_key"]:
                tid = f"u{ledger['next_id']:04d}"
                ledger["next_id"] += 1
                tdir = os.path.join(S2, "tasks", tid)
                os.makedirs(os.path.join(tdir, "recon"), exist_ok=True)
                shutil.copy(os.path.join(HERE, "definition_hash.py"), os.path.join(tdir, "definition_hash.py"))
                dest = os.path.join(tdir, "snapshot")
                status, commit = ("excerpt", None) if excerpt else export(repo, rev, dest)
                entry = {"task_id": tid, "unit": unit, "repo": repo, "revision": rev, "resolved_commit": commit,
                         "pinned": pinned, "status": status,
                         "snapshot_sha256": sha_dir(dest) if status == "done" else None,
                         "sha_method": SHA_METHOD if status == "done" else None, "cases": []}
                ledger["tasks"][tid] = entry
                ledger["by_key"][key] = tid
            tid = ledger["by_key"][key]
            e = ledger["tasks"][tid]
            if e["status"] in ("excerpt", "evidence_inadequate") and not _dispatched(tid):
                # Excerpt tasks follow the current artifact until S2 has run on them.
                sect = _section(open(art).read(), unit, rev) if os.path.exists(art) else None
                path = os.path.join(S2, "tasks", tid, "artifact.txt")
                if sect:
                    open(path, "w").write(sect)
                    e["status"], e["artifact_sha256"] = "excerpt", hashlib.sha256(sect.encode()).hexdigest()
                else:
                    if os.path.exists(path):
                        os.remove(path)
                    e["status"], e["artifact_sha256"] = "evidence_inadequate", None
            if spec["case_id"] not in e["cases"]:
                e["cases"].append(spec["case_id"])
            # Every unit is asked about every inventory element: the side S1 recorded, else the
            # default for its role, so a provider is asked at each revision whether it declares an
            # element the consumer references (an UPGRADE delta needs the absent side too).
            role = next((u.get("role") for u in spec["units"] if u["name"] == unit), None)
            default = {"provider": "provides", "producer": "provides", "consumer": "consumes"}.get(role)
            sides = {}
            for inv in spec.get("inventory", []):
                side = (inv.get("sides") or {}).get(unit) or default
                if side:
                    sides[inv["element"]] = side
            e.setdefault("elements", {}).update(sides)
            e.setdefault("ros_generation", spec.get("ros_generation"))
            e.setdefault("ros_distro", next((u.get("ros_distro") for u in spec["units"] if u["name"] == unit), None))
    # A task no current spec needs, never handed to S2, is withdrawn: workspace removed, ledger entry kept.
    for key, tid in list(ledger["by_key"].items()):
        e = ledger["tasks"][tid]
        if key not in needed and e["status"] not in ("withdrawn", "superseded") and not only:
            if _dispatched(tid):
                # Already handed to S2 (or described): keep everything, mark it as no longer needed.
                e["status"], e["superseded_reason"] = "superseded", "no current spec needs this unit@revision"
            else:
                e["status"], e["withdrawn_reason"] = "withdrawn", "no current spec needs this unit@revision"
                shutil.rmtree(os.path.join(S2, "tasks", tid), ignore_errors=True)
            del ledger["by_key"][key]
    for tid, e in ledger["tasks"].items():
        if e["status"] in ("done", "excerpt"):
            t = {"task_id": tid, "package": e["unit"], "ros_generation": e.get("ros_generation"),
                 "ros_distro": e.get("ros_distro"),
                 "elements": [{"element": k, "side": v} for k, v in sorted(e.get("elements", {}).items())]}
            if e["status"] == "done":
                t["snapshot"] = "snapshot"
            else:
                t["artifact_file"] = "artifact.txt"
            tdir = os.path.join(S2, "tasks", tid)
            json.dump(t, open(os.path.join(tdir, "packet.json"), "w"), indent=1)
            if not _dispatched(tid):
                prompt = open(os.path.join(HERE, "prompts", "S2_describe.md")).read().replace("{S2WORK}", tdir)
                open(os.path.join(tdir, "S2_PROMPT.md"), "w").write(prompt)
            if not e.get("packet"):
                tasks.append(t)
                e["packet"] = f"tasks/{tid}/packet.json"
    json.dump(ledger, open(ledger_path, "w"), indent=1)
    order = [t["task_id"] for t in tasks]
    random.Random(f"{seed()}:tasks:{len(ledger['tasks'])}").shuffle(order)
    if order:
        json.dump(order, open(os.path.join(LEDGER, f"dispatch_{len(ledger['tasks']):04d}.json"), "w"), indent=1)
    print(len(ledger["tasks"]), "tasks;", sum(1 for e in ledger["tasks"].values() if e["status"] == "done"),
          "snapshots exported;", len(tasks), "new task workspaces")


def _dispatched(tid):
    """True once the task was handed to an S2 run (marker) or S2 wrote its description.
    A dispatched workspace is never rewritten, even if the prompt or artifact changed."""
    d = os.path.join(S2, "tasks", tid)
    return os.path.exists(os.path.join(d, "DISPATCHED")) or os.path.exists(os.path.join(d, "recon", f"{tid}.json"))


def dispatch(tids):
    """Steward: mark tasks as handed to S2 (write the marker with a UTC timestamp)."""
    import datetime
    for tid in tids:
        d = os.path.join(S2, "tasks", tid)
        if not os.path.isdir(d):
            raise SystemExit(f"no workspace for {tid}")
        with open(os.path.join(d, "DISPATCHED"), "a") as f:
            f.write(datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ") + "\n")
        print("dispatched", tid)


def _section(text, unit, rev):
    tag, cur, out = f"[[{unit}@{rev}]]", None, []
    for line in text.splitlines():
        if line.strip().startswith("[[") and line.strip().endswith("]]"):
            cur = line.strip()
            continue
        if cur == tag:
            out.append(line)
    body = "\n".join(out).strip()
    return body + "\n" if body else None  # an empty section is no evidence


if __name__ == "__main__":
    if "--dispatch" in sys.argv:
        dispatch(sys.argv[sys.argv.index("--dispatch") + 1].split(","))
    else:
        main()
