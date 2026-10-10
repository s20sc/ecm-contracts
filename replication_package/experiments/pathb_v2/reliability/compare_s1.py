"""Inter-model agreement on S1 case specification (DEVIATIONS.md, 2026-09-27 model amendment).
Compares the claude-fable-5-1 specs in specs/ with the independent claude-opus-5-5 specs in
reliability/s1_opus/specs/ for the seeded sample in reliability/s1_opus/SAMPLE.json.
  python3 reliability/compare_s1.py   -> reliability/s1_intermodel.json (+ printed table)
"""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(HERE, "reliability", "s1_opus")


def e2_code(s):
    e2 = (s.get("eligibility") or {}).get("E2") or {}
    return e2.get("reason_code") or s.get("ineligible_reason")


def main():
    sample = json.load(open(os.path.join(R, "SAMPLE.json")))["sample"]
    rows, agree = [], {k: [0, 0] for k in ("eligible", "operation", "outcome_class", "loudness", "classes", "implicated", "resolution")}
    for cid in sample:
        a = json.load(open(os.path.join(HERE, "specs", f"{cid}.json")))
        b = json.load(open(os.path.join(R, "specs", f"{cid}.json")))
        r = {"case_id": cid, "fable_eligible": bool(a.get("eligible")), "opus_eligible": bool(b.get("eligible")),
             "fable_exit": None if a.get("eligible") else e2_code(a), "opus_exit": None if b.get("eligible") else e2_code(b)}
        agree["eligible"][1] += 1
        agree["eligible"][0] += r["fable_eligible"] == r["opus_eligible"]
        if a.get("eligible") and b.get("eligible"):
            ca = sorted({c["class"] for c in a.get("failed_conditions", [])})
            cb = sorted({c["class"] for c in b.get("failed_conditions", [])})
            ia = sorted({e for c in a.get("failed_conditions", []) for e in c.get("implicated_elements", [])})
            ib = sorted({e for c in b.get("failed_conditions", []) for e in c.get("implicated_elements", [])})
            pairs = {"operation": (a.get("operation"), b.get("operation")),
                     "outcome_class": (a.get("outcome_class"), b.get("outcome_class")),
                     "loudness": (a.get("loudness"), b.get("loudness")),
                     "classes": (ca, cb), "implicated": (ia, ib),
                     "resolution": ((a.get("resolution") or {}).get("status"), (b.get("resolution") or {}).get("status"))}
            for k, (x, y) in pairs.items():
                agree[k][1] += 1
                agree[k][0] += x == y
                r[k] = {"fable": x, "opus": y, "agree": x == y}
        rows.append(r)
    out = {"sample": sample, "per_dimension": {k: {"agree": v[0], "n": v[1]} for k, v in agree.items()}, "cases": rows}
    json.dump(out, open(os.path.join(HERE, "reliability", "s1_intermodel.json"), "w"), indent=1)
    for k, v in agree.items():
        print(f"{k:14s} {v[0]}/{v[1]}")
    for r in rows:
        print(r["case_id"], "elig", r["fable_eligible"], r["opus_eligible"], r["fable_exit"], r["opus_exit"],
              {k: (r[k]["fable"], r[k]["opus"]) for k in ("operation", "outcome_class", "loudness", "classes", "resolution") if k in r and not r[k]["agree"]})


if __name__ == "__main__":
    main()
