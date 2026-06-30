"""Score the screened ROS2 corpus (cases.json; 16 scored cases after exclusions) with the frozen checker.

This is the ROS2 substrate where Beh(QoS)/Res(/cmd_vel) are validated — the dims
ROBUST (ROS1) could not exercise. Includes the honest Beh-vs-schema+QoS falsification
and matched-good NEGATIVE CONTROLS (over-rejection / precision).

Usage: python3 score_corpus.py cases.json
"""
import collections
import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "checker"))
from contract_checker import (ALL_METHODS, ECM_FULL, SCHEMA_ONLY, SCHEMA_QOS,
                              SEMVER_ONLY, Severity, all_findings, method_findings)


def adapt(case):
    """Map the encoder's schema to the checker's case schema."""
    c = dict(case)
    if c.get("type") == "UPGRADE":
        vd = c.get("ver_delta", {}) or {}
        c["old"] = {"interface_hash": vd.get("interface_hash_old", "old"), "semver": vd.get("semver_old", "1.0.0")}
        c["new"] = {"interface_hash": vd.get("interface_hash_new", "new"),
                    "semver": vd.get("semver_new", "1.0.1"),
                    "changed_fields": vd.get("changed_fields", []) or []}
        c["consumer_reads"] = vd.get("consumer_reads", []) or []
    c.setdefault("edge", {})
    return c


def goldset(case):
    g = case.get("gold_dimension")
    return set(g) if isinstance(g, list) else {g}


def crit(case, method):
    f = [x for x in all_findings(case) if x.severity == Severity.CRITICAL]
    return method_findings(f, method)


def make_good(case):
    """Negative control: neutralize the documented mismatch -> must be ACCEPTED."""
    g = copy.deepcopy(case)
    if g.get("type") == "UPGRADE":
        g["new"]["interface_hash"] = g["old"]["interface_hash"]
        g["new"]["changed_fields"] = []
        g["new"]["semver"] = g["old"]["semver"]
        g["consumer_reads"] = []
        return g
    prod, cons = g.get("producer", {}), g.get("consumer", {})
    # remove shared exclusive (fixes Res), match consumer endpoints to producer (fixes Sig/Beh)
    pe = set(prod.get("exclusive", []) or [])
    cons["exclusive"] = [x for x in (cons.get("exclusive", []) or []) if x not in pe]
    outs = prod.get("outputs", []) or []
    if outs and cons.get("inputs"):
        o = outs[0]
        for inp in cons["inputs"]:
            inp["msg_type"] = o.get("msg_type")
            inp["frame"] = o.get("frame")
            inp["units"] = o.get("units")
            inp["qos"] = copy.deepcopy(o.get("qos"))
            inp["min_rate_hz"] = None
    cons["perm_requires"] = []
    return g


def main():
    cases = [adapt(c) for c in json.load(open(sys.argv[1] if len(sys.argv)>1 else __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'cases.json'))) if c.get("gold_dimension") and not c.get("excluded")]
    n = len(cases)
    print(f"=== ROS2 corpus: {n} cases ===")
    typedist = collections.Counter(c.get("type") for c in cases)
    print(f"  types: {dict(typedist)}")

    # recall (predicted + attributed)
    hit = {m.name: 0 for m in ALL_METHODS}
    dimtot = collections.Counter()
    ecm_dim = collections.Counter()
    for c in cases:
        gs = goldset(c)
        for d in gs:
            dimtot[d] += 1
        for m in ALL_METHODS:
            dims = {x.dimension for x in crit(c, m)}
            if dims & gs:
                hit[m.name] += 1
                if m is ECM_FULL:
                    for d in dims & gs:
                        ecm_dim[d] += 1
    print(f"\n=== per-method recall (predicted+attributed / {n}) ===")
    for m in ALL_METHODS:
        print(f"  {m.name:12s}: {hit[m.name]}/{n}  ({hit[m.name]/n:.0%})")
    print(f"\n=== ECM per-dimension recall ===")
    for d in ("Sig", "Beh", "Res", "Ver", "Perm", "Rec"):
        if dimtot.get(d):
            print(f"  {d}: {ecm_dim.get(d,0)}/{dimtot[d]}")

    # Beh falsification: on Beh-gold cases, ECM vs schema+QoS (QoS is co-detected!)
    beh = [c for c in cases if "Beh" in goldset(c)]
    ecm_beh = sum(1 for c in beh if {x.dimension for x in crit(c, ECM_FULL)} & {"Beh"})
    sq_beh = sum(1 for c in beh if {x.dimension for x in crit(c, SCHEMA_QOS)} & {"Beh", "Sig"})
    # ECM Beh marginal over schema+QoS = Beh cases ECM catches that schema+QoS does NOT
    beh_marg = sum(1 for c in beh
                   if ({x.dimension for x in crit(c, ECM_FULL)} & {"Beh"})
                   and not crit(c, SCHEMA_QOS))
    print(f"\n=== Beh falsification (the adversarial test) ===")
    print(f"  Beh cases: {len(beh)}; ECM catches {ecm_beh}; schema+QoS catches {sq_beh}")
    print(f"  ECM Beh marginal over schema+QoS (the honest number): {beh_marg}")
    print(f"  -> shows whether Beh earns its place BEYOND the free QoS the baseline already has")

    # Ver vs semver-only
    ver = [c for c in cases if "Ver" in goldset(c)]
    ecm_ver = sum(1 for c in ver if {x.dimension for x in crit(c, ECM_FULL)} & {"Ver"})
    sv_ver = sum(1 for c in ver if crit(c, SEMVER_ONLY))
    print(f"\n=== Ver vs semver-only ===  Ver cases {len(ver)}: ECM {ecm_ver}, semver-only {sv_ver}")

    # negative controls (over-rejection / precision)
    fp = sum(1 for c in cases if crit(make_good(c), ECM_FULL))
    print(f"\n=== negative controls (matched-good twins) ===")
    print(f"  ECM false-positive on {fp}/{n} fixed compositions  (precision = {(n-fp)/n:.0%} on controls)")
    print(f"  -> over-rejection check: ECM should ACCEPT the fixed versions")


if __name__ == "__main__":
    main()
