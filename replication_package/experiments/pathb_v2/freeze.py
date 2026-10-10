"""Freeze manifest for Path B v2.1 (PROTOCOL.md Section 16).

  python3 freeze.py write [--seed N] [--model S1=... S2=... ADJ1=... ADJ2=... ADJ3=...]
  python3 freeze.py verify            (exit 1 on any mismatch)
  python3 freeze.py add-ledger <path> (records a retrieval ledger hash with a timestamp)
  python3 freeze.py amend <file> --reason "..." --scope "..."  (post-freeze change, logged in DEVIATIONS.md)
  python3 freeze.py amend-model S1=<model> --reason "..." --scope "..."  (post-freeze model change)

Every stage calls `verify` first and stops on mismatch (fail closed).
"""
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PB = os.path.join(os.path.dirname(HERE), "pathb")
FILES = ['PROTOCOL.md', 'prompts/S1_specify.md', 'prompts/S2_describe.md', 'prompts/A_adjudicate.md', 'collect_c3.py', 'materialize.py', 'build_packets.py', 'assemble.py', 'baselines_v2.py', 'scoring.py', 'adjudicate.py', 'definition_hash.py', 'make_report.py', 'freeze.py', 'test_scoring.py', 'mutation_probe.py', 'ledger/adjudicators.json', 'pilot/PILOT_CASES.json', '../pathb/checker/contract_checker.py', '../pathb/checker/canonical.py']
MANIFEST = os.path.join(HERE, "FREEZE.json")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def write():
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 20260925
    models = {}
    if "--model" in sys.argv:
        for kv in sys.argv[sys.argv.index("--model") + 1:]:
            if "=" in kv:
                k, v = kv.split("=", 1)
                models[k] = v
    m = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(), "seed": seed, "models": models,
         "files": {f: sha(os.path.join(HERE, f)) for f in FILES}, "ledgers": {}}
    json.dump(m, open(MANIFEST, "w"), indent=1)
    audit = os.path.join(os.path.dirname(os.path.dirname(HERE)), "V19-EMSE", "audit",
                         f"FREEZE-{m['frozen_at_utc'][:19].replace(':', '')}.json")
    shutil.copy(MANIFEST, audit)
    print("frozen", m["frozen_at_utc"], "->", audit)


def amend():
    """Record a post-freeze change to one frozen file: old and new hash, time, reason; the
    manifest copy in V19-EMSE/audit/ is refreshed and DEVIATIONS.md gets the entry.
      python3 freeze.py amend <file> --reason "..." [--scope "..."]"""
    f = sys.argv[2]
    reason = sys.argv[sys.argv.index("--reason") + 1] if "--reason" in sys.argv else ""
    scope = sys.argv[sys.argv.index("--scope") + 1] if "--scope" in sys.argv else ""
    m = json.load(open(MANIFEST))
    if f not in m["files"]:
        raise SystemExit(f"{f} is not a frozen file")
    old, new = m["files"][f], sha(os.path.join(HERE, f))
    if old == new:
        raise SystemExit(f"{f} is unchanged")
    at = datetime.now(timezone.utc).isoformat()
    m["files"][f] = new
    m.setdefault("amendments", []).append({"file": f, "old_sha256": old, "new_sha256": new, "at": at, "reason": reason, "scope": scope})
    json.dump(m, open(MANIFEST, "w"), indent=1)
    audit = os.path.join(os.path.dirname(os.path.dirname(HERE)), "V19-EMSE", "audit",
                         f"FREEZE-{m['frozen_at_utc'][:19].replace(':', '')}.json")
    shutil.copy(MANIFEST, audit)
    with open(os.path.join(HERE, "DEVIATIONS.md"), "a") as d:
        d.write(f"\n## {at[:10]} — `{f}`\n\n- **Change:** {reason}\n- **Re-run scope:** {scope}\n- **Hash:** `{old[:12]}` → `{new[:12]}` (FREEZE.json amendment {len(m['amendments'])})\n")
    if "DEVIATIONS.md" in m.get("ledgers", {}):
        # The deviation log is append-only and this entry just changed it; its ledger record tracks the
        # current file, and every earlier record (the one written before unsealing) stays in ledger_history.
        m["ledgers"]["DEVIATIONS.md"] = {"path": "DEVIATIONS.md", "sha256": sha(os.path.join(HERE, "DEVIATIONS.md")), "added_utc": at}
        json.dump(m, open(MANIFEST, "w"), indent=1)
        shutil.copy(MANIFEST, audit)
    print("amended", f, old[:12], "->", new[:12])


def amend_model():
    """Record a post-freeze change of the model pinned for a stage role.
      python3 freeze.py amend-model S1=<model> --reason "..." --scope "..." """
    kv = next(a for a in sys.argv[2:] if "=" in a and not a.startswith("--"))
    role, new = kv.split("=", 1)
    reason = sys.argv[sys.argv.index("--reason") + 1] if "--reason" in sys.argv else ""
    scope = sys.argv[sys.argv.index("--scope") + 1] if "--scope" in sys.argv else ""
    m = json.load(open(MANIFEST))
    old = m["models"].get(role)
    at = datetime.now(timezone.utc).isoformat()
    m["models"][role] = new
    m.setdefault("model_amendments", []).append({"role": role, "old": old, "new": new, "at": at, "reason": reason, "scope": scope})
    json.dump(m, open(MANIFEST, "w"), indent=1)
    audit = os.path.join(os.path.dirname(os.path.dirname(HERE)), "V19-EMSE", "audit",
                         f"FREEZE-{m['frozen_at_utc'][:19].replace(':', '')}.json")
    shutil.copy(MANIFEST, audit)
    with open(os.path.join(HERE, "DEVIATIONS.md"), "a") as d:
        d.write(f"\n## {at[:10]} — model for {role}\n\n- **Change:** `{old}` → `{new}`. {reason}\n- **Re-run scope:** {scope}\n")
    print("model amended", role, old, "->", new)


def verify():
    m = json.load(open(MANIFEST))
    bad = [f for f, h in m["files"].items() if not os.path.exists(os.path.join(HERE, f)) or sha(os.path.join(HERE, f)) != h]
    for name, rec in m.get("ledgers", {}).items():
        p = os.path.join(HERE, rec["path"])
        if not os.path.exists(p) or sha(p) != rec["sha256"]:
            bad.append(name)
    if bad:
        print("FREEZE MISMATCH:", bad)
        sys.exit(1)
    print("freeze verified", m["frozen_at_utc"])


def add_ledger(path):
    """Record a ledger's hash, keyed by its path relative to pathb_v2 (two files with one basename,
    such as calibration/key.json and calibration/v2/key.json, are two records). Re-recording a path
    moves the earlier record to ledger_history instead of erasing it."""
    m = json.load(open(MANIFEST))
    rel = os.path.relpath(path, HERE)
    now = datetime.now(timezone.utc).isoformat()
    rec = {"path": rel, "sha256": sha(path), "added_utc": now}
    for k, old in list(m["ledgers"].items()):
        if old["path"] == rel:
            if old["sha256"] == rec["sha256"]:
                print("ledger unchanged", rel)
                return
            m.setdefault("ledger_history", []).append(dict(old, replaced_utc=now))
            del m["ledgers"][k]
    m["ledgers"][rel] = rec
    json.dump(m, open(MANIFEST, "w"), indent=1)
    print("ledger recorded", rel)


if __name__ == "__main__":
    {"write": write, "verify": verify, "add-ledger": lambda: add_ledger(sys.argv[2]), "amend": amend,
     "amend-model": amend_model}[sys.argv[1]]()
