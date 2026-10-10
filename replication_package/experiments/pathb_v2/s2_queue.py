"""Steward: order undispatched S2 tasks by the value of the cases they serve (scheduling only).

  python3 s2_queue.py [--n 4]     -> prints the next n task ids to dispatch, with their tier

Tier 1: tasks of C3 selected failures with at least one class some method can match (these
        are the only cases on which H1's discordant pairs can arise).
Tier 2: tasks of the other eligible C3 cases (controls, warning-only, binary rejection).
Tier 3: tasks of C1/C2/C3N eligible cases with a matchable class.
Tier 4: all remaining tasks.
Ordering changes no method; tasks never run because a budget ran out are reported as
budget_exhausted (PROTOCOL.md Section 13) with their tier.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MATCHABLE = {"nominal_type_mismatch", "definition_mismatch", "frame_mismatch", "unit_mismatch", "qos_reliability",
             "qos_durability", "qos_deadline", "rate_shortfall", "exclusive_resource_conflict", "permission_missing",
             "element_removed_or_renamed", "element_retyped"}


def tier_of_case(cid, spec, selected):
    matchable = any(c.get("class") in MATCHABLE for c in spec.get("failed_conditions") or [])
    if spec.get("corpus") == "C3":
        return 1 if (cid in selected and matchable) else 2
    return 3 if matchable else 4


def queue():
    L = json.load(open(os.path.join(HERE, "ledger", "tasks.json")))
    sel_p = os.path.join(HERE, "candidates", "C3_selection.json")
    selected = set(json.load(open(sel_p))["selected"]) if os.path.exists(sel_p) else set()
    pilot = set(json.load(open(os.path.join(HERE, "pilot", "PILOT_CASES.json")))["quarantined_pilot_cases"])
    out = []
    for tid, e in L["tasks"].items():
        if e["status"] not in ("done", "excerpt"):
            continue
        d = os.path.join(HERE, "s2_work", "tasks", tid)
        if os.path.exists(os.path.join(d, "DISPATCHED")) or os.path.exists(os.path.join(d, "recon", f"{tid}.json")):
            continue
        cases = [c for c in e.get("cases", []) if c not in pilot]
        if not cases:
            continue
        tiers = []
        for c in cases:
            p = os.path.join(HERE, "specs", f"{c}.json")
            if os.path.exists(p):
                tiers.append(tier_of_case(c, json.load(open(p)), selected))
        if tiers:
            out.append((min(tiers), tid, e["unit"], cases))
    return sorted(out)


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 4
    q = queue()
    from collections import Counter
    print("pending by tier:", dict(sorted(Counter(t for t, *_ in q).items())))
    for t, tid, unit, cases in q[:n]:
        print(t, tid, unit, cases)
