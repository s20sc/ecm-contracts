"""Regenerate every table of Section 4 from the results files (PROTOCOL.md Section 15).

  python3 make_report.py [--out <dir>]

Reads results_adjudicated.json (primary), results.json (pre-adjudication), results_adjudicated_adj1only.json,
results_adjudicated_nosubstance.json and results_frozenasm_adjudicated.json (the three readings of H1 declared in
DEVIATIONS.md on 2026-09-29), adjudicated/kappa.json, specs/, assembled/, candidates/ and scores_adjudicated/.
Writes LaTeX table fragments to <out>/ (default V19-EMSE/paper_source/tables_v2/), report/summary.md, and
report/numbers.json, a flat map of every number the prose may cite. Figures are produced by the standalone
scripts under report/figures/, which read the same files.
"""
from __future__ import annotations

import glob
import collections
import json
import os
import sys
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
V19 = os.path.join(os.path.dirname(os.path.dirname(HERE)), "V19-EMSE")
METHODS = ["ECM", "NT", "DI", "DQ", "SV"]
NAMES = {"ECM": "ECM", "NT": "NT", "DI": "DI", "DQ": "DQ", "SV": "SV"}
CORPORA = ["C1", "C2", "C3", "C3N"]
CORPUS_NAMES = {"C1": "C1 (\\textsc{Robust})", "C2": "C2 (ROS reports)", "C3": "C3 (held-out)", "C3N": "C3-neutral"}
CLASS_NAMES = {"nominal_type_mismatch": "nominal type", "definition_mismatch": "definition", "frame_mismatch": "frame",
               "unit_mismatch": "unit", "qos_reliability": "QoS reliability", "qos_durability": "QoS durability",
               "qos_deadline": "QoS deadline", "rate_shortfall": "rate", "exclusive_resource_conflict": "exclusive resource",
               "permission_missing": "permission", "element_removed_or_renamed": "element removed or renamed",
               "element_retyped": "element retyped", "recovery_conflict": "recovery conflict",
               "representation_convention": "representation convention", "other": "other"}
NUMBERS: Dict[str, object] = {}


def tex(s: str) -> str:
    return str(s).replace("_", "\\_").replace("%", "\\%").replace("#", "\\#")


def load(name):
    p = os.path.join(HERE, name)
    return json.load(open(p)) if os.path.exists(p) else None


def pct(r, ci=True):
    if not r or r.get("n", 0) == 0:
        return "--"
    s = f"{r['k']}/{r['n']} ({100 * r['k'] / r['n']:.0f}\\%"
    if ci and r.get("wilson95"):
        lo, hi = r["wilson95"]
        s += f", [{100 * lo:.0f}, {100 * hi:.0f}]"
    return s + ")"


EXIT_NAMES = {"E2:deployment_wiring": "E2 wiring", "E2:internal": "E2 internal", "E2:build": "E2 build",
              "E2:firmware": "E2 firmware", "E2:units_not_identifiable": "E2 units", "E2:roles_unidentified": "E2 roles"}


def brk(t: str) -> str:
    """Allow a line break after every escaped underscore of an identifier inside a paragraph column."""
    return t.replace("\\_", "\\_\\allowbreak{}")


def kn(r) -> str:
    """k/n, or -- when there is no denominator."""
    return f"{r['k']}/{r['n']}" if r.get("n") else "--"


def kn_ci(r) -> str:
    """k/n with the Wilson 95 % interval in percent."""
    w = r.get("wilson95")
    return (f"{r['k']}/{r['n']} [{100 * w[0]:.0f}, {100 * w[1]:.0f}]" if r.get("n") and w else kn(r))


def frac(k, n):
    return f"{k}/{n}" if n else "--"


def fmt_p(p):
    if p is None:
        return "nested"
    return "1.0" if p >= 1 else (f"{p:.3f}" if p >= 0.001 else "<0.001")


def tabular(cols: str, header: List[str], rows: List[List[str]], full=True) -> str:
    env = "tabular*" if full else "tabular"
    cols = cols.replace("p{", ">{\\raggedright\\arraybackslash}p{")  # no justified rivers in paragraph columns
    width = "{\\linewidth}" if full else ""
    pre = "@{\\extracolsep{\\fill}}" if full else "@{}"
    out = [f"\\begin{{{env}}}{width}{{{pre}{cols}@{{}}}}", "\\toprule",
           " & ".join(f"\\textbf{{{h}}}" for h in header) + " \\\\", "\\midrule"]
    out += [" & ".join(r) + " \\\\" for r in rows]
    out += ["\\bottomrule", f"\\end{{{env}}}"]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- funnel
def funnel(pilot: set) -> str:
    specs = {}
    for f in glob.glob(os.path.join(HERE, "specs", "*.json")):
        s = json.load(open(f))
        specs[s["case_id"]] = s
    cand = {}
    led = load("candidates/C3_ledger.json")
    order = load("candidates/C3_order.json")
    if led and order:
        cand["C3"] = (len(led["hits"]), len(order["ordered"]))
    ledn = load("candidates/C3N_ledger.json")
    if ledn:
        cand["C3N"] = (len(ledn.get("hits") or ledn.get("drawn") or []), None)
    rows = []
    for c in CORPORA:
        ss = [s for s in specs.values() if s["corpus"] == c]
        n_pilot = sum(1 for s in ss if s["case_id"] in pilot)
        elig = [s for s in ss if s.get("eligible")]
        exits: Dict[str, int] = {}
        for s in ss:
            if s.get("eligible"):
                continue
            e = s.get("eligibility") or {}
            failed = [k for k in ("E1", "E2", "E3", "E4") if (e.get(k) or {}).get("pass") is False]
            key = failed[0] if failed else "E?"
            if key == "E2" and (e.get("E2") or {}).get("reason_code"):
                key = "E2:" + e["E2"]["reason_code"]
            exits[key] = exits.get(key, 0) + 1
        oc = {}
        for s in elig:
            oc[s.get("outcome_class")] = oc.get(s.get("outcome_class"), 0) + 1
        asm_done = asm_un = 0
        for s in elig:
            a = load(f"assembled/{s['case_id']}.json")
            if a is None:
                continue
            if a["status"] == "done":
                asm_done += 1
            else:
                asm_un += 1
        NUMBERS[f"funnel.{c}"] = {"specified": len(ss), "pilot": n_pilot, "eligible": len(elig), "outcome": oc,
                                 "exits": exits, "assembled": asm_done, "unassessable": asm_un, "candidates": cand.get(c)}
        src = cand.get(c)
        rows.append([CORPUS_NAMES[c],
                     (f"{src[0]} hits, {src[1]} ordered" if src and src[1] else (f"{src[0]} drawn" if src else "--")),
                     str(len(ss)), str(n_pilot),
                     ", ".join(f"{EXIT_NAMES.get(k, tex(k))} {v}" for k, v in sorted(exits.items())),
                     str(len(elig)),
                     ", ".join(f"{tex(str(k))} {v}" for k, v in sorted(oc.items(), key=lambda x: str(x[0]))),
                     f"{asm_done} / {asm_un}"])
    # one column per corpus, one row per quantity (the wide form overflows the text width)
    labels = ["Candidates", "Specified", "Pilot", "Ineligible (first failed criterion)", "Eligible",
              "Outcome class", "Assembled / unassessable"]
    trows = [[lab] + [r[i + 1] for r in rows] for i, lab in enumerate(labels)]
    return tabular("p{2.4cm}p{2.3cm}p{1.9cm}p{2.5cm}p{2.0cm}", ["Quantity"] + [r[0] for r in rows], trows)


# --------------------------------------------------------------------------- detection
def detection(res, c) -> str:
    p = res["by_corpus"][c]["primary_all_eligible"]
    rows = []
    for m in METHODS:
        mm = p["methods"][m]
        st = mm["states"]
        rows.append([NAMES[m], kn_ci(mm["right_reason"]), kn(mm["right_reason_silent"]),
                     kn(mm["binary_reject"]), str(len(st["wrong_reason"])), str(len(st["unverified"])),
                     kn(mm["false_alarm_fixed_observed"]), kn(mm["false_alarm_fixed_recommended"]),
                     kn(mm["false_alarm_warning_only"])])
        NUMBERS[f"{c}.{m}"] = {"right_reason": mm["right_reason"], "silent": mm["right_reason_silent"],
                               "binary": mm["binary_reject"], "wrong_reason": len(st["wrong_reason"]),
                               "unverified": len(st["unverified"]), "fa_observed": mm["false_alarm_fixed_observed"],
                               "fa_recommended": mm["false_alarm_fixed_recommended"],
                               "fa_warning": mm["false_alarm_warning_only"], "case_control": mm["case_control"],
                               "cases": mm["right_reason"].get("cases")}
    NUMBERS[f"{c}.n"] = {"failures": p["n_failures"], "silent": p["n_silent"], "unassessable": p["n_unassessable_failures"],
                         "controls": p["n_controls"], "union": p["union_detected"]}
    return tabular("lrrrrrrrr", ["Method", "Right reason", "Silent", "Binary rej.", "Wrong reason", "Unverified",
                                  "FA obs.", "FA rec.", "FA warn."], rows)


def by_class(res, c) -> str:
    p = res["by_corpus"][c]["primary_all_eligible"]
    bc = p["by_class"]
    order = sorted(bc, key=lambda k: (-bc[k]["n"], k))
    rows = [[CLASS_NAMES.get(k, tex(k)), str(bc[k]["n"])] + [str(bc[k][m]) for m in METHODS] for k in order]
    NUMBERS[f"{c}.by_class"] = bc
    return tabular("lr" + "r" * len(METHODS), ["Failed-condition class", "n"] + METHODS, rows)


def case_control(res, c) -> str:
    p = res["by_corpus"][c]["primary_all_eligible"]
    rows = []
    for m in METHODS:
        cc = p["methods"][m]["case_control"]
        f = lambda x: "--" if x is None else str(Decimal(repr(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        rows.append([NAMES[m], str(cc["tp"]), str(cc["fp"]), str(cc["fn"]), str(cc["tn"]), f(cc["precision"]),
                     f(cc["recall"]), f(cc["f1"])])
    prev = p["methods"]["ECM"]["case_control"]["prevalence"]
    NUMBERS[f"{c}.prevalence"] = prev
    # "ratio": unassessable controls are false positives under the protocol's bound, so this is not the precision
    # of a binary classifier (pre-R2 audit, 2026-09-30); the by-findings readings are in numbers.json alert_ratios.
    return tabular("lrrrrrrr", ["Method", "TP", "FP", "FN", "TN", "Prec.\\ ratio", "Recall", "$F_1$ (ratio)"], rows)


def pairwise(res, c) -> str:
    p = res["by_corpus"][c]["primary_all_eligible"]["pairwise"]
    rows = []
    for key, v in p.items():
        if not key.startswith("all_failures:"):
            continue
        a, b = key.split(":")[1].split("_vs_")
        rows.append([f"{a} vs {b}", str(v["b_first_only"]), str(v["c_second_only"]), str(v["both"]), str(v["neither"]),
                     "yes" if v["structurally_nested"] else "no", fmt_p(v["mcnemar_exact_p"])])
    NUMBERS[f"{c}.pairwise"] = p
    return tabular("lrrrrrr", ["Pair", "$b$ (first only)", "$c$ (second only)", "both", "neither", "nested", "exact $p$"], rows)


def detection_all(res) -> str:
    """One table of right-reason detection for the four corpora (RQ1), rows grouped by corpus."""
    rows = []
    for c in CORPORA:
        if c not in res["by_corpus"]:
            continue
        p = res["by_corpus"][c]["primary_all_eligible"]
        rows.append([f"\\multicolumn{{6}}{{@{{}}l}}{{\\emph{{{CORPUS_NAMES[c]}: {p['n_failures']} failures, "
                     f"{p['n_silent']} silent, {p['n_unassessable_failures']} unassessable}}}}"])
        for m in METHODS:
            mm = p["methods"][m]
            st = mm["states"]
            rows.append([NAMES[m], kn_ci(mm["right_reason"]), kn(mm["right_reason_silent"]), kn(mm["binary_reject"]),
                         str(len(st["wrong_reason"])), str(len(st["unverified"]))])
    return tabular("lp{2.2cm}rrrr", ["Method", "Right reason", "Silent", "Binary rejection", "Wrong reason", "Unverified"], rows)


def false_alarms_all(res) -> str:
    """One table of false alarms on the three control types for the four corpora (RQ3), rows grouped by corpus."""
    rows = []
    for c in CORPORA:
        if c not in res["by_corpus"]:
            continue
        p = res["by_corpus"][c]["primary_all_eligible"]
        n = p["n_controls"]
        rows.append([f"\\multicolumn{{4}}{{@{{}}l}}{{\\emph{{{CORPUS_NAMES[c]}: {n.get('fixed_observed', 0)} observed-fixed, "
                     f"{n.get('fixed_recommended', 0)} recommended-fixed, {n.get('warning_only', 0)} warning-only controls}}}}"])
        for m in METHODS:
            mm = p["methods"][m]
            rows.append([NAMES[m], kn_ci(mm["false_alarm_fixed_observed"]), kn_ci(mm["false_alarm_fixed_recommended"]),
                         kn_ci(mm["false_alarm_warning_only"])])
    return tabular("lrrr", ["Method", "Observed-fixed", "Recommended-fixed", "Warning-only"], rows)


def overlap(res, c) -> str:
    p = res["by_corpus"][c]["primary_all_eligible"]
    hm = p["hit_matrix"]
    n = len(hm)
    union = sum(1 for v in hm.values() if any(v[m] for m in METHODS))
    inter = sum(1 for v in hm.values() if all(v[m] for m in ("ECM", "DI", "DQ")))
    ecm_only = sum(1 for v in hm.values() if v["ECM"] and not any(v[m] for m in METHODS if m != "ECM"))
    base_only = sum(1 for v in hm.values() if not v["ECM"] and any(v[m] for m in METHODS if m != "ECM"))
    NUMBERS[f"{c}.overlap"] = {"n": n, "union": union, "ecm_only": ecm_only, "baseline_only": base_only, "all_three": inter}
    rows = [[CORPUS_NAMES[c], str(n), pct(p["union_detected"]), str(ecm_only), str(base_only), str(inter)]]
    return tabular("lrrrrr", ["Corpus", "Failures", "Union of five methods", "ECM only", "Baseline only",
                              "ECM, DI and DQ"], rows)


def undetected(res, c) -> str:
    p = res["by_corpus"][c]["primary_all_eligible"]
    u = p["undetected_by_class"]
    rows = [[CLASS_NAMES.get(k, tex(k)), str(len(v)), tex(", ".join(v))] for k, v in sorted(u.items(), key=lambda x: (-len(x[1]), x[0]))]
    NUMBERS[f"{c}.undetected"] = {k: len(v) for k, v in u.items()}
    return tabular("p{3.4cm}rp{6.4cm}", ["Failed-condition class", "n undetected", "Cases"], rows)


# --------------------------------------------------------------------------- H1
def h1_table() -> str:
    files = [("(i) primary: current assembly, declared-role fold", "results_adjudicated.json"),
             ("(ii) current assembly, fold without substance demotion", "results_adjudicated_nosubstance.json"),
             ("(iii) freeze-time assembly, declared-role fold", "results_frozenasm_adjudicated.json"),
             ("strict-adjudicator fold (first adjudicator alone)", "results_adjudicated_adj1only.json"),
             ("before adjudication", "results.json")]
    rows = []
    for label, f in files:
        r = load(f)
        if r is None:
            continue
        h = r["H1"]
        b, c = h["b_ecm_only"], h["c_dq_only"]
        w = h.get("wilson95_b_over_discordant")
        rows.append([label, str(h["n_eligible_failures"]), str(b), str(c), str(h["both"]), str(h["neither"]),
                     str(b - c), fmt_p(h["mcnemar_exact_two_sided_p"]),
                     (f"[{100 * w[0]:.0f}, {100 * w[1]:.0f}]" if w else "--")])
        NUMBERS[f"H1.{f}"] = h
    return tabular("p{3.6cm}rrrrrrrp{1.4cm}", ["Reading", "$n$", "$b$", "$c$", "both", "neither", "$b-c$", "exact $p$",
                                              "Wilson on $b/(b+c)$"], rows)


# --------------------------------------------------------------------------- strata, sensitivities, kappa
def sensitivities(res) -> str:
    import report_extra
    rows, distinct = [], {}
    reason_names = {"no_token": "library default", "named_profile": "named profile", "no_location": "no readable citation"}
    prim_det = {x for c in CORPORA if c in res["by_corpus"]
                for x in res["by_corpus"][c]["primary_all_eligible"]["methods"]["ECM"]["right_reason"]["cases"]}

    def lost_count(bc):
        return len(prim_det - {x for c in CORPORA if c in bc for x in bc[c]["primary_all_eligible"]["methods"]["ECM"]["right_reason"]["cases"]})
    for name, v in res["sensitivity"].items():
        h = v["H1"]
        if v.get("nulled") is not None:
            d = distinct[name] = report_extra.distinct_nulled(v["nulled"])
            what = (f"{d['values']} values on {d['ports']} ports ("
                    + ", ".join(f"{n} {reason_names.get(k, tex(k))}" for k, n in sorted(d["by_reason"].items(), key=lambda kv: -kv[1]))
                    + f"); {d['occurrences']} occurrences")
        else:
            what = f"{len(v.get('excluded') or [])} cases left out" if v.get("excluded") is not None else "--"
        per = "; ".join(f"{c} {v['by_corpus'][c]['primary_all_eligible']['methods']['ECM']['right_reason']['k']}/"
                        f"{v['by_corpus'][c]['primary_all_eligible']['methods']['ECM']['right_reason']['n']}"
                        for c in CORPORA if c in v["by_corpus"])
        rows.append([brk(tex(name)) + ("" if v.get("declared_in_advance") else " (exploratory, not declared in advance)"), what,
                     f"{h['n_eligible_failures']}, {h['b_ecm_only']}, {h['c_dq_only']}, {fmt_p(h['mcnemar_exact_two_sided_p'])}",
                     per, str(lost_count(v["by_corpus"]))])
    # the strict-adjudicator fold as a row of the same table (its per-corpus counts and the cases it moves)
    adj1 = load("results_adjudicated_adj1only.json")
    if adj1 is not None:
        h = adj1["H1"]
        per = "; ".join(f"{c} {adj1['by_corpus'][c]['primary_all_eligible']['methods']['ECM']['right_reason']['k']}/"
                        f"{adj1['by_corpus'][c]['primary_all_eligible']['methods']['ECM']['right_reason']['n']}"
                        for c in CORPORA if c in adj1["by_corpus"])
        ov = load("adjudicated_adj1only/overrides.json") or {}
        admitted = sorted(cid for cid, o in ov.items() if o.get("eligible") is True)
        excluded = sorted(cid for cid, o in ov.items() if o.get("eligible") is False)
        lost = sorted(set(res["by_corpus"][c]["primary_all_eligible"]["methods"]["ECM"]["right_reason"]["cases"][i]
                          for c in CORPORA if c in res["by_corpus"]
                          for i in range(len(res["by_corpus"][c]["primary_all_eligible"]["methods"]["ECM"]["right_reason"]["cases"])))
                      - set(x for c in CORPORA if c in adj1["by_corpus"]
                            for x in adj1["by_corpus"][c]["primary_all_eligible"]["methods"]["ECM"]["right_reason"]["cases"]))
        NUMBERS["adj1only"] = {"admitted_exclusions": admitted, "excluded_eligible": excluded, "detections_lost": lost,
                               "per_corpus": {c: adj1["by_corpus"][c]["primary_all_eligible"]["methods"]["ECM"]["right_reason"]
                                              for c in CORPORA if c in adj1["by_corpus"]}, "H1": h}
        rows.append(["strict-adjudicator fold (first adjudicator alone)",
                     f"{len(excluded)} eligible cases excluded, {len(admitted)} exclusions admitted (never described)",
                     f"{h['n_eligible_failures']}, {h['b_ecm_only']}, {h['c_dq_only']}, {fmt_p(h['mcnemar_exact_two_sided_p'])}",
                     per, str(len(lost))])
    NUMBERS["sensitivity"] = {k: {"H1": v["H1"], "nulled_by_reason": v.get("nulled_by_reason"), "distinct": distinct.get(k),
                                  "excluded": v.get("excluded"), "state_changes": v.get("state_changes"),
                                  "checker_detections_lost": lost_count(v["by_corpus"]),
                                  "declared_in_advance": v.get("declared_in_advance")}
                              for k, v in res["sensitivity"].items()}
    NUMBERS["blinding_guess"] = res["sensitivity"]["excerpt_excluded"].get("s2_blinding_guess_by_task_kind")
    return tabular("p{2.0cm}p{2.4cm}p{1.9cm}p{2.3cm}p{1.3cm}", ["Analysis", "What changes", "H1: $n$, $b$, $c$, $p$",
                                                            "ECM right reason per corpus", "Checker detections lost"], rows)


def kappa() -> str:
    k = load("adjudicated/kappa.json") or {}
    units = {"eligibility": "cases", "class": "failed conditions", "loudness": "cases", "resolution": "cases",
             "provenance": "values (A2)", "substance": "changed fields (A2)"}
    rows = []
    for dom, v in k.items():
        if not isinstance(v, dict) or "kappa" not in v:
            continue
        rows.append([tex(dom), f"{v['n']} {units.get(dom, '')}".strip(), f"{v['observed_agreement']:.2f}", f"{v['kappa']:.2f}"])
    NUMBERS["kappa"] = k
    return tabular("llrr", ["Decision domain", "Judged", "Observed agreement", "Cohen's $\\kappa$"], rows)


# --------------------------------------------------------------------------- in-scope C3 cases
def c3_inscope(res, matchable: set) -> str:
    sel = set(res["c3_selection"]["selected"])
    p = res["by_corpus"]["C3"]["primary_all_eligible"]
    st = {m: {s: cid for s, cids in p["methods"][m]["states"].items() for cid in cids} for m in METHODS}
    rows = []
    for cid in sorted(sel):
        spec = load(f"specs/{cid}.json")
        cls = sorted({x["class"] for x in spec.get("failed_conditions") or []})
        if not any(k in matchable for k in cls):
            continue
        sc = load(f"scores_adjudicated/{cid}.json")
        def state(m):
            if sc is None:
                return "unassessable"
            s = sc["broken"][m]["state"]
            if s == "right_reason":
                rules = sorted({x["rule"] for x in sc["broken"][m]["matched"]})
                return f"right reason ({brk(tex(', '.join(rules)))})"
            return tex(s.replace("_", " "))
        loud = spec.get("loudness") or "?"
        a2_items = [it for f in glob.glob(os.path.join(HERE, "adjudication", "packets", "A2_*.json"))
                    for it in json.load(open(f)) if it.get("case_id") == cid]
        a2_broken = [it for it in a2_items if it.get("composition") == "broken"]
        demoted = ((load("adjudicated/provenance_verdicts.json") or {}).get(cid) or {}).get("broken")
        a2 = "--" if not a2_broken else ("verified" if not demoted else "demoted: " + ", ".join(
            sorted(set(demoted.values()))))
        rows.append([cid, spec["operation"], tex(", ".join(CLASS_NAMES.get(k, k) for k in cls)),
                     tex(str(loud).replace("_documented", "")), tex(spec.get("detection_stage") or "?"),
                     state("ECM"), state("DQ"), a2])
    NUMBERS["c3_inscope"] = rows
    return tabular("llp{1.8cm}llp{1.9cm}p{1.9cm}l", ["Case", "Op.", "Class", "Loudness", "Stage", "ECM", "DQ", "A2"], rows)


# --------------------------------------------------------------------------- derivability, overlap, V18 ledger
FIELDS = ["msg_type", "frame", "units", "qos.reliability", "qos.durability", "qos.deadline_ms", "rate_hz", "min_rate_hz", "definition_id"]


def derivability() -> str:
    """Share of described ports with a non-null value per field, by ROS generation, over every returned
    description that serves a non-pilot case (RQ4)."""
    led = load("ledger/tasks.json")["tasks"]
    pilot_p = load("pilot/PILOT_CASES.json")
    pilot = set(pilot_p["quarantined_pilot_cases"]) if pilot_p else set()
    tot: Dict[str, Dict[str, int]] = {}
    non: Dict[str, Dict[str, int]] = {}
    fk: Dict[str, Dict[str, int]] = {}
    for t, e in led.items():
        if e["status"] not in ("done", "excerpt") or not [c for c in e.get("cases", []) if c not in pilot]:
            continue
        r = load(f"s2_work/tasks/{t}/recon/{t}.json")
        if not r:
            continue
        gen = e.get("ros_generation") or "unknown"
        for port in r.get("ports") or []:
            fv = port.get("frame")
            if fv not in (None, ""):
                fk.setdefault(gen, {"identifier": 0, "per_message": 0, "none": 0})
                fk[gen]["none" if fv == "none" else "per_message" if fv == "per_message" else "identifier"] += 1
            for f in FIELDS:
                v = port
                for k in f.split("."):
                    v = (v or {}).get(k) if isinstance(v, dict) else None
                tot.setdefault(gen, {}).setdefault(f, 0)
                non.setdefault(gen, {}).setdefault(f, 0)
                tot[gen][f] += 1
                if v not in (None, ""):
                    non[gen][f] += 1
    gens = sorted(tot)
    rows = []
    for f in FIELDS:
        rows.append([tex(f)] + [f"{non[g][f]}/{tot[g][f]} ({100 * non[g][f] / tot[g][f]:.0f}\\%)" if tot[g].get(f) else "--" for g in gens])
        if f == "frame":  # the recorded frame values are mostly the literal "none" (no spatial data); show the split
            for kind, label in (("identifier", "frame: identifier"), ("per_message", "frame: per message"), ("none", "frame: none (no spatial data)")):
                rows.append([label] + [f"{fk[g][kind]}/{tot[g][f]} ({100 * fk[g][kind] / tot[g][f]:.0f}\\%)" if tot[g].get(f) else "--" for g in gens])
    NUMBERS["derivability"] = {g: {f: [non[g][f], tot[g][f]] for f in FIELDS} for g in gens}
    NUMBERS["derivability_frame_kinds"] = {g: dict(fk[g]) for g in gens}
    return tabular("l" + "r" * len(gens), ["Field"] + [tex(g) for g in gens], rows)


PORT_GROUPS = [
    ("Message type", lambda r: r["field"] == "msg_type"),
    ("Frame: \\texttt{none} (no spatial data)", lambda r: r["field"] == "frame" and r["value"] == "none"),
    ("Frame: identifier or per message", lambda r: r["field"] == "frame" and r["value"] != "none"),
    ("Unit", lambda r: r["field"] == "units"),
    ("Quality of service", lambda r: r["field"].startswith("qos.")),
    ("Rate", lambda r: r["field"] == "rate_hz"),
    ("Definition identity", lambda r: r["field"] == "definition_id"),
]
LOCATION_KINDS = ("location", "location_other_spelling")


def port_sample(allow_pending: bool = False) -> str:
    """Provenance check of described values on the seeded 15 % port sample (PROTOCOL.md Section 12, RQ4),
    from reliability/port_sample_agreement.json (sample_ports.py fold). Refuses while any value is pending
    the third seat or lacks an initial record."""
    draw = load("reliability/port_sample.json")
    agr = load("reliability/port_sample_agreement.json")
    rows = agr["rows"]
    open_ = [r for r in rows if r["final"] in ("pending", "incomplete")]
    if open_ and not allow_pending:
        raise SystemExit(f"port sample not final: {len(open_)} values pending or incomplete")

    def count(rs):
        c = collections.Counter(r["final"] for r in rs)
        return {"values": len(rs), "verified": c["verified"], "wrong": c["wrong"], "unverifiable": c["unverifiable"],
                "location": sum(r["kind"] in LOCATION_KINDS for r in rs), "initial_agree": sum(r["ADJ1"] == r["ADJ2"] for r in rs),
                "verified_by_ADJ1_alone": sum(r["ADJ1"] == "verified" for r in rs), "verified_by_ADJ2_alone": sum(r["ADJ2"] == "verified" for r in rs),
                "unverifiable_without_location": sum(r["final"] == "unverifiable" and r["kind"] not in LOCATION_KINDS for r in rs)}
    body, groups = [], {}
    for label, pred in PORT_GROUPS + [("All values", lambda r: True)]:
        rs = [r for r in rows if pred(r)]
        if not rs:
            continue
        g = count(rs)
        groups[label] = g
        first = ("\\midrule " if label == "All values" else "") + label
        body.append([first] + [str(g[k]) for k in ("values", "location", "verified", "wrong", "unverifiable")]
                    + [f"{g['initial_agree']}/{g['values']}"])
    unv = [r for r in rows if r["final"] == "unverifiable"]
    NUMBERS["port_sample"] = {
        "seed": draw["seed"], "share": draw["share"], "frame_ports": draw["frame_ports"], "sample_ports": draw["sample_ports"],
        "sample_ports_with_values": draw["sample_ports_with_values"], "sample_values": draw["sample_values"],
        "groups": groups, "initial_agreement": agr["initial_agreement"], "third_seat": agr["third_seat"],
        "unverifiable_by_provenance_kind": dict(collections.Counter(r["kind"] for r in unv)),
        "wrong": [{"item_id": r["item_id"], "field": r["field"], "value": r["value"], "ADJ1": r["ADJ1"], "ADJ2": r["ADJ2"], "ADJ3": r["ADJ3"]}
                  for r in rows if r["final"] == "wrong"],
    }
    # a wrapping first column and stacked headers keep the seven columns inside the text width
    tab = tabular("p{3.0cm}rrrrrr", ["Field", "Values", "\\shortstack[r]{Location\\\\cited}", "Verified", "Wrong",
                                      "\\shortstack[r]{Unveri-\\\\fiable}", "\\shortstack[r]{Seats\\\\agreed}"], body)
    return tab.replace("\\\\\n\\midrule ", "\\\\\n\\midrule\n")


def overlap_all(res) -> str:
    rows = []
    for c in CORPORA:
        if c not in res["by_corpus"]:
            continue
        p = res["by_corpus"][c]["primary_all_eligible"]
        hm = p["hit_matrix"]
        union = sum(1 for v in hm.values() if any(v[m] for m in METHODS))
        inter = sum(1 for v in hm.values() if all(v[m] for m in ("ECM", "DI", "DQ")))
        ecm_only = sum(1 for v in hm.values() if v["ECM"] and not any(v[m] for m in METHODS if m != "ECM"))
        base_only = sum(1 for v in hm.values() if not v["ECM"] and any(v[m] for m in METHODS if m != "ECM"))
        NUMBERS[f"{c}.overlap"] = {"n": len(hm), "union": union, "ecm_only": ecm_only, "baseline_only": base_only, "all_three": inter}
        rows.append([CORPUS_NAMES[c], str(len(hm)), kn_ci(p["union_detected"]), str(ecm_only), str(base_only), str(inter)])
    return tabular("lrp{2.4cm}p{1.3cm}p{1.9cm}p{1.9cm}", ["Corpus", "Failures", "Union of the five methods", "ECM only", "Comparator only", "ECM, DI and DQ"], rows)


DIM_OF_CLASS = {"nominal_type_mismatch": "Sig", "frame_mismatch": "Sig", "unit_mismatch": "Sig",
                "qos_reliability": "Beh", "qos_durability": "Beh", "qos_deadline": "Beh", "rate_shortfall": "Beh",
                "exclusive_resource_conflict": "Res", "permission_missing": "Perm",
                "element_removed_or_renamed": "Ver", "element_retyped": "Ver", "definition_mismatch": "Ver"}
DIM_NAMES = {"Sig": r"$\mathit{Sig}$ (type, frame, unit)", "Beh": r"$\mathit{Beh}$ (quality of service, rate)",
             "Res": r"$\mathit{Res}$ (exclusive claims)", "Perm": r"$\mathit{Perm}$", "Rec": r"$\mathit{Rec}$",
             "Ver": r"$\mathit{Ver}$ (removed, renamed, retyped, definition)"}


def dimensions() -> str:
    """Per contract dimension, over the documented failures of the four corpora (pilot excluded, C3 at the
    pre-specified selection): failures carrying a class the dimension's rules match, how many of those were
    unassessable, and how many the checker detected for the right reason through that dimension (Section 3)."""
    sel = set(load("results_adjudicated.json")["c3_selection"]["selected"])
    cases: Dict[str, set] = {d: set() for d in DIM_NAMES}
    unas: Dict[str, set] = {d: set() for d in DIM_NAMES}
    det: Dict[str, set] = {d: set() for d in DIM_NAMES}
    n_fail = n_match = n_none = 0
    for f in sorted(glob.glob(os.path.join(HERE, "scores_adjudicated", "*.json"))):
        r = load(f)
        cid = r["case_id"]
        if r["outcome_class"] != "failure" or r["corpus"] == "pilot" or (r["corpus"] == "C3" and cid not in sel):
            continue
        n_fail += 1
        dims = {DIM_OF_CLASS[c] for c in r["classes"] if c in DIM_OF_CLASS}
        n_match += bool(dims)
        n_none += not dims
        for d in dims:
            cases[d].add(cid)
            if r["assembled_status"] != "done":
                unas[d].add(cid)
        ecm = (r.get("broken") or {}).get("ECM") or {}
        if ecm.get("state") == "right_reason":
            for m in ecm.get("matched", []):
                if m["class"] in DIM_OF_CLASS:
                    det[DIM_OF_CLASS[m["class"]]].add(cid)
    NUMBERS["dimensions"] = {"n_failures": n_fail, "with_matchable_class": n_match, "without": n_none,
                             **{d: {"matchable": len(cases[d]), "unassessable": len(unas[d]), "ecm_right_reason": len(det[d])}
                                for d in DIM_NAMES}}
    rows = [[DIM_NAMES[d], str(len(cases[d])), str(len(unas[d])), str(len(det[d]))] if d != "Rec" else
            [DIM_NAMES[d] + " (one rule, which only warns)", "--", "--", "--"] for d in ("Sig", "Beh", "Res", "Perm", "Rec", "Ver")]
    rows.append([r"no matching rule (behavioral, timing, memory, representation convention)", str(n_none), "--", "--"])
    return tabular("p{5.6cm}p{1.9cm}p{1.9cm}p{1.9cm}", ["Dimension", "Failures with a matchable class", "Unassessable", "ECM right reason"], rows)


# V18 candidates that cite one defect and were specified once in v2.1 (PROTOCOL.md Section 3: "Two candidates that
# cite one defect (ros2_control#1400) are one candidate").
MERGED_V18 = {"B-Ver-03": "B-Res-05"}


def ledger_v18() -> str:
    """Appendix B: every case the submitted version scored, with its V18 verdict, the audit findings, and the
    v2.1 outcome under the primary analysis."""
    import re
    pb = os.path.join(os.path.dirname(HERE), "pathb")
    aud = json.load(open(os.path.join(pb, "tp_mechanism_audit_results.json")))
    enc = json.load(open(os.path.join(pb, "encoding_audit", "score_audit_results.json")))
    # the 48 cases the submitted version scored, ROBUST first, in the order of the encoding audit
    ids = [r["case_id"] for r in enc["rows"] if r["corpus"] == "ROBUST"] +\
          [r["case_id"] for r in enc["rows"] if r["corpus"] != "ROBUST"]
    assert len(ids) == 48, len(ids)
    hits = set()
    for c in aud["corpora"].values():
        hits |= set(c["as_scored_v18"]["ECM-full"]["cases"])
    mech = {r["case_id"]: r["mechanism_match"] for r in aud["postfix_rows"]}
    rel = {cid: k for k, v in aud["rederivation_relation"].items() for cid in v}
    encrow = {r["case_id"]: r for r in enc["rows"]}
    pilot_p = load("pilot/PILOT_CASES.json")
    pilot = set(pilot_p["quarantined_pilot_cases"]) if pilot_p else set()
    rel_names = {"same_instance": "same instance", "same_mechanism_other_instance": "same mechanism, other instance",
                 "different_failure": "different failure", "encoding_only": "encoded claim only", "no_concrete_source": "no source"}
    rows = []
    counts = {"v18_hits": 0, "hit_no_match": 0, "v2_right_reason": 0}
    for i in ids:
        cid = i
        v18 = "hit" if cid in hits else "miss"
        counts["v18_hits"] += v18 == "hit"
        m = mech.get(cid, "--") if v18 == "hit" else "--"
        counts["hit_no_match"] += m == "no"
        e = encrow.get(cid)
        asc = ((e or {}).get("as_scored") or {}).get("hit", {}).get("ECM-full")
        cor = ((e or {}).get("corrected") or {}).get("hit", {}).get("ECM-full")
        ench = ("--" if e is None else "no corrected encoding" if cor is None else
                "hit lost" if asc and not cor else "hit gained" if cor and not asc else "unchanged")
        spec = load(f"specs/{cid}.json")
        if cid in pilot:
            v2 = "pilot (quarantined)"
        elif spec is None and cid in MERGED_V18:
            v2 = f"merged into {MERGED_V18[cid]} (same defect)"
        elif spec is None:
            v2 = "not specified"
        elif not spec.get("eligible"):
            # labelled by the first failed criterion, as in the funnel (R1 review, peer review m13)
            el = spec.get("eligibility") or {}
            failed = [k for k in ("E1", "E2", "E3", "E4") if (el.get(k) or {}).get("pass") is False]
            first = failed[0] if failed else None
            e2 = (el.get("E2") or {}).get("reason_code") if first == "E2" else None
            v2 = "ineligible" + (f" ({EXIT_NAMES.get('E2:' + e2, tex(e2)).replace('E2 ', '')})" if e2 else f" ({first})" if first else "")
        elif spec.get("outcome_class") != "failure":
            v2 = tex(str(spec.get("outcome_class")))
        else:
            sc = load(f"scores_adjudicated/{cid}.json")
            st = sc["broken"]["ECM"]["state"] if sc else "unassessable"
            v2 = tex(st.replace("_", " "))
            counts["v2_right_reason"] += st == "right_reason"
        rows.append([tex(cid), v18, m, rel_names.get(rel.get(cid), "--") if v18 == "hit" else "--", ench, v2])
    NUMBERS["ledger_v18"] = counts
    NUMBERS["ledger_v18"]["v2_states"] = dict(collections.Counter(r[5] for r in rows))
    header = " & ".join(f"\\textbf{{{h}}}" for h in ["Case", "V18 ECM", "Mechanism match", "Re-derivation", "Encoding audit", "v2.1 ECM (primary)"]) + " \\\\"
    out = ["\\begin{longtable}{@{}ll" + "".join(">{\\raggedright\\arraybackslash}p{%s}" % w for w in ("1.8cm", "2.1cm", "1.7cm", "2.1cm")) + "@{}}",
           "\\caption{The 48 cases scored by the submitted version, with the submitted verdict, the audit findings, "
           "and the state of each case in the rebuilt evaluation.}\\label{tab:ledger_v18}\\\\",
           "\\toprule", header, "\\midrule\\endfirsthead",
           "\\toprule", header, "\\midrule\\endhead",
           "\\bottomrule\\endfoot"]
    out += [" & ".join(r) + " \\\\" for r in rows]
    out += ["\\end{longtable}"]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- main
def main() -> None:
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(V19, "paper_source", "tables_v2")
    os.makedirs(out, exist_ok=True)
    os.makedirs(os.path.join(HERE, "report"), exist_ok=True)
    res = load("results_adjudicated.json")
    pilot_p = load("pilot/PILOT_CASES.json")
    pilot = set(pilot_p["quarantined_pilot_cases"]) if pilot_p else set()
    sys.path.insert(0, HERE)
    from s2_queue import MATCHABLE  # noqa: E402
    files = {"funnel.tex": funnel(pilot), "h1.tex": h1_table(),
             "sensitivity.tex": sensitivities(res), "kappa.tex": kappa(), "c3_inscope.tex": c3_inscope(res, MATCHABLE),
             "derivability.tex": derivability(), "port_sample.tex": port_sample(), "dimensions.tex": dimensions(), "detection.tex": detection_all(res), "false_alarms.tex": false_alarms_all(res), "overlap.tex": overlap_all(res), "ledger_v18.tex": ledger_v18()}
    for c in CORPORA:
        if c not in res["by_corpus"]:
            continue
        files[f"detection_{c}.tex"] = detection(res, c)
        files[f"byclass_{c}.tex"] = by_class(res, c)
        files[f"casecontrol_{c}.tex"] = case_control(res, c)
        files[f"pairwise_{c}.tex"] = pairwise(res, c)
        files[f"overlap_{c}.tex"] = overlap(res, c)
        files[f"undetected_{c}.tex"] = undetected(res, c)
    import report_extra
    files.update(report_extra.build(sys.modules[__name__], res))
    for name, body in files.items():
        open(os.path.join(out, name), "w").write("% generated by experiments/pathb_v2/make_report.py; do not edit\n" + body)
    NUMBERS["c3_selection"] = {k: v for k, v in res["c3_selection"].items() if k != "per_repo"}
    NUMBERS["c3_adjudication_effect"] = res["c3_adjudication_effect"]
    json.dump(NUMBERS, open(os.path.join(HERE, "report", "numbers.json"), "w"), indent=1, default=str)
    md = ["# Path B v2.1 results (adjudicated, primary)\n"]
    for c in CORPORA:
        if c not in res["by_corpus"]:
            continue
        p = res["by_corpus"][c]["primary_all_eligible"]
        md.append(f"## {c}: {p['n_failures']} failures ({p['n_unassessable_failures']} unassessable, {p['n_silent']} silent); controls {p['n_controls']}")
        for m in METHODS:
            md.append(f"- {m}: right reason {pct(p['methods'][m]['right_reason'])}, FA observed {pct(p['methods'][m]['false_alarm_fixed_observed'], False)}")
    md.append("\n## H1\n" + json.dumps({k: v for k, v in res["H1"].items()}, indent=1))
    open(os.path.join(HERE, "report", "summary.md"), "w").write("\n".join(md).replace("\\%", "%"))
    print(len(files), "tables written to", out)


if __name__ == "__main__":
    main()
