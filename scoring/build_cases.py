"""Convert blind per-case composition specs into frozen-checker cases and score.

Honest funnel reporting: 221 ROBUST bugs -> 92 integration (crosswalk) -> N assessable
(blind agents) -> of those, INTERFACE-PROPERTY-scoreable (frame/units/qos/rate/version/
lock groundable from published interfaces) vs WIRING/UNGROUNDABLE (topic-name/namespace/
remap rooted in launch config, not module interface -> outside contract-property scope).
We score recall only on the interface-property subset and report the scope boundary.

Usage: python3 build_cases.py <wf_output.json> <robust_cases.json>
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "checker"))
from contract_checker import ALL_METHODS, ECM_FULL, SCHEMA_ONLY, SCHEMA_QOS, SEMVER_ONLY, Severity, all_findings, method_findings


def endpoints(side):
    """Pull a normalized list of endpoints from a spec's producer/consumer dict."""
    if not isinstance(side, dict):
        return []
    eps = []
    for key in ("outputs", "inputs"):
        for e in side.get(key, []) or []:
            if isinstance(e, dict):
                eps.append({
                    "role": e.get("role") or "edge",
                    "msg_type": e.get("msg_type") or e.get("type"),
                    "frame": e.get("frame"),
                    "units": e.get("units"),
                    "qos": e.get("qos") if isinstance(e.get("qos"), dict) else None,
                    "rate_hz": e.get("rate_hz"),
                    "min_rate_hz": e.get("min_rate_hz"),
                })
    return eps


def contract(side):
    c = {"outputs": [], "inputs": []}
    if not isinstance(side, dict):
        return c
    c["outputs"] = endpoints({"outputs": side.get("outputs", [])})
    c["inputs"] = endpoints({"inputs": side.get("inputs", [])})
    exc = side.get("exclusive")
    c["exclusive"] = exc if isinstance(exc, list) else ([exc] if exc else [])
    pr = side.get("perm_requires")
    c["perm_requires"] = pr if isinstance(pr, list) else ([pr] if pr else [])
    return c


WIRING_RE = re.compile(r"topic[- ]?name|namespace|remap|no publisher|advertis|connection", re.I)
INTERFACE_RE = re.compile(r"frame|unit|qos|durability|reliab|deadline|rate|hz|version|semver|md5|interface|api|exclusive|lock|claim|resource", re.I)


def classify(spec):
    """interface | wiring | unground."""
    fault = (spec.get("interaction_fault", "") + " " + spec.get("title", "")).lower()
    prod, cons = contract(spec.get("producer")), contract(spec.get("consumer"))
    has_iface = any(
        e.get("frame") or e.get("units") or e.get("qos") or e.get("rate_hz") or e.get("min_rate_hz")
        for e in prod["outputs"] + cons["inputs"]
    ) or prod["exclusive"] or cons["exclusive"] or cons["perm_requires"] or spec.get("ver_delta")
    if spec.get("composition_type") == "UPGRADE" and spec.get("ver_delta"):
        return "interface"
    if WIRING_RE.search(fault) and not has_iface:
        return "wiring"
    if has_iface:
        return "interface"
    return "unground"


def to_case(spec, gold):
    ct = spec.get("composition_type", "PAIR")
    if ct == "UPGRADE" and spec.get("ver_delta"):
        vd = spec["ver_delta"]
        return {
            "type": "UPGRADE", "gold_dimension": gold,
            "old": {"interface_hash": vd.get("interface_hash_old", "old"), "semver": vd.get("semver_old", "1.0.0")},
            "new": {"interface_hash": vd.get("interface_hash_new", "new"), "semver": vd.get("semver_new", "1.0.1"),
                    "changed_fields": vd.get("changed_fields", []) or []},
            "consumer_reads": vd.get("consumer_reads", []) or [],
        }
    prod, cons = contract(spec.get("producer")), contract(spec.get("consumer"))
    ctype = "CONCURRENT" if (prod["exclusive"] and cons["exclusive"]) else "PAIR"
    return {"type": ctype, "gold_dimension": gold, "producer": prod, "consumer": cons, "edge": {}}


def main():
    wf = json.load(open(sys.argv[1]))
    goldmap = {c["case_id"]: c["gold_dimension"] for c in json.load(open(sys.argv[2]))}

    funnel = collections.Counter()
    scoreable = []   # (case_id, case, gold, system)
    for S in wf["result"]["systems"]:
        for spec in S.get("specs", []) or []:
            if not spec.get("assessable"):
                funnel["non_assessable"] += 1
                continue
            funnel["assessable"] += 1
            cls = classify(spec)
            funnel[f"class_{cls}"] += 1
            if cls != "interface":
                continue
            cid = spec.get("case_id", "?")
            gold = goldmap.get(cid)  # independent crosswalk gold; may be None if not in the 92
            case = to_case(spec, gold)
            scoreable.append((cid, case, gold, S["system"][:14]))

    print("=== HONEST FUNNEL ===")
    print(f"  221 ROBUST bugs -> 92 integration (crosswalk) -> {funnel['assessable']} assessable (blind agents)")
    print(f"  of assessable: interface-property-scoreable={funnel['class_interface']}  "
          f"wiring/launch-config={funnel['class_wiring']}  ungroundable={funnel['class_unground']}")
    print(f"  (non-assessable build/logic/firmware skipped: {funnel['non_assessable']})")

    # score interface subset
    with_gold = [(c, ca, g, s) for (c, ca, g, s) in scoreable if g]
    print(f"\n=== scoring {len(with_gold)} interface cases that also have a crosswalk gold dimension ===")
    per_method_hit = {m.name: 0 for m in ALL_METHODS}
    per_dim = collections.defaultdict(lambda: collections.Counter())  # dim -> method -> hits
    per_dim_total = collections.Counter()
    for cid, case, gold, sysn in with_gold:
        goldset = set(gold) if isinstance(gold, list) else {gold}
        for d in goldset:
            per_dim_total[d] += 1
        f_all = all_findings(case)
        f_crit = [x for x in f_all if x.severity == Severity.CRITICAL]
        for m in ALL_METHODS:
            mf = method_findings(f_crit, m)
            dims_hit = {x.dimension for x in mf}
            if dims_hit & goldset:        # predicted AND correctly attributed
                per_method_hit[m.name] += 1
                if m is ECM_FULL:
                    for d in (dims_hit & goldset):
                        per_dim[d][m.name] += 1

    n = len(with_gold)
    print(f"\n=== per-method recall (predicted+attributed / {n}) ===")
    for m in ALL_METHODS:
        r = per_method_hit[m.name] / n if n else 0
        print(f"  {m.name:12s}: {per_method_hit[m.name]}/{n}  ({r:.0%})")
    print(f"\n=== ECM per-dimension recall ===")
    for d in ("Sig", "Beh", "Res", "Ver", "Perm", "Rec"):
        tot = per_dim_total.get(d, 0)
        hit = per_dim[d].get(ECM_FULL.name, 0)
        if tot:
            print(f"  {d}: {hit}/{tot}")
    # dump the scoreable cases for inspection
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    json.dump([{"case_id": c, "gold": g, "system": s, "case": ca} for (c, ca, g, s) in scoreable],
              open(os.path.join(data_dir, "scoreable_cases.json"), "w"), indent=2)
    print(f"\nwrote scoreable_cases.json ({len(scoreable)} interface cases)")


if __name__ == "__main__":
    main()
