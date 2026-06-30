"""Score the BLIND contract library with the FROZEN checker.

Honest design: compositions are discovered from the library's OWN topic/resource
sharing structure (never tailored to a bug). For every plausible cross-module edge
and every shared-exclusive concurrent pair, run all four methods. The HEADLINE
falsification number is ECM-full's marginal over the strong schema+QoS baseline,
broken down by check_type — i.e. what do ECM's extra dimensions detect, using
contracts that were written blind, that the strongest free baseline cannot?

Usage: python3 score_pathb.py ../data/contract_library.json
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "checker"))

from contract_checker import (
    ALL_METHODS, ECM_FULL, SCHEMA_ONLY, SCHEMA_QOS, SEMVER_ONLY,
    all_findings, method_findings)


def role_kw(s):
    s = (s or "").lower()
    return set(w for w in s.replace("/", " ").replace("_", " ").split() if len(w) > 2)


def edge_match(out, inp):
    """Plausible producer.output -> consumer.input edge (not bug-tailored)."""
    if out.get("msg_type") and inp.get("msg_type") and out["msg_type"] != inp["msg_type"]:
        # different types only count as an edge if topics are literally identical
        return out.get("topic") and out.get("topic") == inp.get("topic")
    # same/compatible msg_type: connect if topic identical OR roles share a keyword
    if out.get("topic") and out.get("topic") == inp.get("topic"):
        return True
    return bool(role_kw(out.get("role")) & role_kw(inp.get("role")) & role_kw(out.get("msg_type")))


def main():
    lib = json.load(open(sys.argv[1]))
    mods = list(lib.items())
    by_sys = collections.defaultdict(list)
    for mid, c in mods:
        by_sys[c.get("_system", "?")].append((mid, c))

    pair_cases, conc_cases = [], []
    for sysname, comps in by_sys.items():
        for i, (na, ca) in enumerate(comps):
            for j, (nb, cb) in enumerate(comps):
                if i == j:
                    continue
                # directed edges A.output -> B.input
                for out in ca.get("outputs", []) or []:
                    for inp in cb.get("inputs", []) or []:
                        if out and inp and edge_match(out, inp):
                            pair_cases.append({
                                "type": "PAIR", "system": sysname,
                                "producer": ca, "consumer": cb,
                                "edge": {"out_role": out.get("role"), "in_role": inp.get("role")},
                                "pair": f"{na} -> {nb}",
                            })
                # concurrent shared-exclusive (unordered, i<j)
                if i < j:
                    shared = set(ca.get("exclusive", []) or []) & set(cb.get("exclusive", []) or [])
                    if shared:
                        conc_cases.append({
                            "type": "CONCURRENT", "system": sysname,
                            "producer": ca, "consumer": cb,
                            "edge": {}, "pair": f"{na} || {nb}", "shared": sorted(shared),
                        })

    cases = pair_cases + conc_cases
    print(f"natural compositions discovered: {len(pair_cases)} edges + {len(conc_cases)} concurrent = {len(cases)}")

    # Run all methods; collect findings.
    per_method = {m.name: collections.Counter() for m in ALL_METHODS}     # dimension -> #flagged comps
    per_method_ct = {m.name: collections.Counter() for m in ALL_METHODS}  # check_type -> count
    flagged_by = {m.name: set() for m in ALL_METHODS}
    for idx, case in enumerate(cases):
        f = all_findings(case)
        for m in ALL_METHODS:
            mf = method_findings(f, m)
            if mf:
                flagged_by[m.name].add(idx)
                for x in mf:
                    per_method[m.name][x.dimension] += 1
                    per_method_ct[m.name][x.check_type] += 1

    print("\n=== compositions FLAGGED per method (unique compositions) ===")
    for m in ALL_METHODS:
        print(f"  {m.name:12s}: {len(flagged_by[m.name])}/{len(cases)}  dims={dict(per_method[m.name])}")

    print("\n=== ECM-full check_type breakdown (what ECM detects) ===")
    for ct, n in per_method_ct[ECM_FULL.name].most_common():
        print(f"  {ct}: {n}")

    # HEADLINE: ECM marginal over the strong schema+QoS baseline.
    ecm_only = flagged_by[ECM_FULL.name] - flagged_by[SCHEMA_QOS.name]
    ecm_only_so = flagged_by[ECM_FULL.name] - flagged_by[SCHEMA_ONLY.name]
    print(f"\n=== HEADLINE marginal ===")
    print(f"  compositions ECM flags that schema+QoS MISSES: {len(ecm_only)}")
    print(f"  compositions ECM flags that schema-only MISSES: {len(ecm_only_so)}")
    # what check_types drive the ECM-vs-schema+QoS marginal
    marg_ct = collections.Counter()
    marg_dim = collections.Counter()
    for idx in ecm_only:
        for x in method_findings(all_findings(cases[idx]), ECM_FULL):
            if x.check_type not in SCHEMA_QOS.checks:
                marg_ct[x.check_type] += 1
                marg_dim[x.dimension] += 1
    print(f"  marginal driven by dimensions: {dict(marg_dim)}")
    print(f"  marginal driven by check_types: {dict(marg_ct)}")
    print("\n  (Honest reading: QoS findings are co-detected by schema+QoS -> NOT in ECM marginal.")
    print("   ECM's real marginal is frame/units (Sig), rate/precondition (non-QoS Beh), lock (Res).)")

    # sample a few ECM-only compositions for the paper's worked examples
    print("\n=== sample ECM-only compositions (blind contracts) ===")
    for idx in list(ecm_only)[:8]:
        c = cases[idx]
        cts = sorted({x.check_type for x in method_findings(all_findings(c), ECM_FULL)
                      if x.check_type not in SCHEMA_QOS.checks})
        print(f"  [{c['system'][:14]}] {c['pair']}  -> {cts}")

    # ---- CRITICAL-only (predict-fail = >=1 CRITICAL finding; precondition/rec are WARNING) ----
    from contract_checker import Severity
    crit_flagged = {m.name: set() for m in ALL_METHODS}
    crit_ct = {m.name: collections.Counter() for m in ALL_METHODS}
    for idx, case in enumerate(cases):
        f = [x for x in all_findings(case) if x.severity == Severity.CRITICAL]
        for m in ALL_METHODS:
            mf = method_findings(f, m)
            if mf:
                crit_flagged[m.name].add(idx)
                for x in mf:
                    crit_ct[m.name][x.check_type] += 1
    print("\n=== CRITICAL-only predict-fail per method ===")
    for m in ALL_METHODS:
        print(f"  {m.name:12s}: {len(crit_flagged[m.name])}/{len(cases)}  checks={dict(crit_ct[m.name])}")
    cm = crit_flagged[ECM_FULL.name] - crit_flagged[SCHEMA_QOS.name]
    print(f"  ECM critical marginal over schema+QoS: {len(cm)} compositions")

    # ---- sanity: are the unit/frame mismatches real or mis-paired-edge artifacts? ----
    print("\n=== sanity: unit/frame mismatch edge details (verify not artifacts) ===")
    shown = 0
    from contract_checker import _pick
    for case in cases:
        if case["type"] != "PAIR":
            continue
        for x in all_findings(case):
            if x.check_type in ("unit_mismatch", "frame_mismatch") and shown < 12:
                print(f"  {case['pair'][:50]} [{x.check_type}] {x.detail}")
                shown += 1


if __name__ == "__main__":
    main()
