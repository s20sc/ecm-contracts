"""Steward: build the next C3 S1 packet in the frozen order (PROTOCOL.md Section 3).

  python3 c3_next.py [--n 8]      -> packets/S1_C3_<k>.json + .prompt.md, or "stop"

Takes the next candidates in C3_order that are neither specified nor already dispatched and
whose repository has not reached its cap (from the specs written so far), records them in
ledger/c3_dispatch.json, and fills the S1 prompt. Prints "stop" once c3_selection reports the
planned number reached or the order exhausted. The selection itself is scoring.c3_selection,
which refuses to skip any unspecified candidate outside a capped repository.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_packets as K  # noqa: E402
import scoring as S  # noqa: E402


def main():
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 8
    specs = {}
    for f in glob.glob(os.path.join(HERE, "specs", "C3-*.json")):
        try:
            s = json.load(open(f))
            specs[s["case_id"]] = s
        except (ValueError, KeyError):
            pass  # a spec being written right now
    sel = S.c3_selection(specs)
    if sel["status"] in ("reached", "exhausted"):
        print("stop", sel["status"], len(sel["selected"]), "selected")
        return
    disp_p = os.path.join(HERE, "ledger", "c3_dispatch.json")
    disp = json.load(open(disp_p)) if os.path.exists(disp_p) else {"packets": {}}
    dispatched = {c for v in disp["packets"].values() for c in v}
    capped_repos = {r for r, k in sel["per_repo"].items() if k >= S.C3_PER_REPO_CAP} if sel.get("per_repo") else set()
    hits = json.load(open(os.path.join(HERE, "candidates", "C3_ledger.json")))["hits"]
    batch = []
    for it in K.items("C3"):
        cid = it["case_id"]
        if cid in specs or cid in dispatched or hits[it["issue_url"]]["repo"] in capped_repos:
            continue
        batch.append(it)
        if len(batch) == n:
            break
    if not batch:
        print("nothing to dispatch (all remaining candidates specified or in flight)")
        return
    k = len(disp["packets"])
    name = f"S1_C3_{k:02d}"
    path = os.path.join(HERE, "packets", f"{name}.json")
    json.dump(batch, open(path, "w"), indent=1)
    prompt = open(os.path.join(HERE, "prompts", "S1_specify.md")).read().replace("{PB2}", HERE).replace("{INPUT}", path)
    open(os.path.join(HERE, "packets", f"{name}.prompt.md"), "w").write(prompt)
    disp["packets"][name] = [b["case_id"] for b in batch]
    json.dump(disp, open(disp_p, "w"), indent=1)
    print(name, [b["case_id"] for b in batch], "| selected so far", len(sel["selected"]), "| status", sel["status"])


if __name__ == "__main__":
    main()
