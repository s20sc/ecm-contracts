"""Path B v2.1 scoring (frozen with PROTOCOL.md, Sections 8-12).

  python3 scoring.py [--write] [--adjudicated]

Reads specs/*.json (plus adjudicated/overrides.json with --adjudicated),
assembled/<case_id>.json (plus adjudicated/provenance_verdicts.json), runs the frozen
checker through its wrapper and the four baselines on every assembled unit, matches
finding instances against the specification's failed conditions (rule-instance
matching, Section 9), assigns the scoring states of Section 10, and aggregates
(Section 12). Writes scores/<case_id>.json and results.json (or results_adjudicated.json).
"""
from __future__ import annotations

import copy
import glob
import json
import math
import os
import re
import sys
from math import comb
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(os.path.dirname(HERE), "pathb", "checker")
sys.path.insert(0, CHECKER)
sys.path.insert(0, HERE)
from contract_checker import ECM_FULL, Severity, all_findings  # noqa: E402

import baselines_v2 as B  # noqa: E402

METHODS = ["ECM", "NT", "DI", "DQ", "SV"]
CLASSES = {"nominal_type_mismatch", "definition_mismatch", "frame_mismatch", "unit_mismatch", "qos_reliability",
           "qos_durability", "qos_deadline", "rate_shortfall", "exclusive_resource_conflict", "permission_missing",
           "recovery_conflict", "element_removed_or_renamed", "element_retyped", "representation_convention", "other"}

# Section 9: (method, rule) pairs that match a class. `token` rules match only when the
# finding's token is an implicated element; `edge` rules when the edge element is.
MATCH: Dict[str, List[Tuple[str, str, str]]] = {
    "nominal_type_mismatch": [("ECM", "type_mismatch", "edge"), ("NT", "nt_type_mismatch", "edge")],
    "definition_mismatch": [("DI", "di_definition_mismatch", "edge"), ("DQ", "di_definition_mismatch", "edge"),
                            ("ECM", "field_break", "token")],
    "frame_mismatch": [("ECM", "frame_mismatch", "edge")],
    "unit_mismatch": [("ECM", "unit_mismatch", "edge")],
    "qos_reliability": [("ECM", "qos_reliability", "edge"), ("DQ", "dq_qos_reliability", "edge")],
    "qos_durability": [("ECM", "qos_durability", "edge"), ("DQ", "dq_qos_durability", "edge")],
    "qos_deadline": [("ECM", "qos_deadline", "edge"), ("DQ", "dq_qos_deadline", "edge")],
    "rate_shortfall": [("ECM", "rate_starvation", "edge")],
    "exclusive_resource_conflict": [("ECM", "lock_conflict", "token")],
    "permission_missing": [("ECM", "missing_permission", "token"), ("ECM", "limit_exceeded", "token")],
    "recovery_conflict": [],
    "representation_convention": [],
    "element_removed_or_renamed": [("ECM", "field_break", "token")],
    "element_retyped": [("ECM", "field_break", "token")],
    "other": [],
}
_TOKEN_RE = {"field_break": re.compile(r"changed field '(.+)' is read"),
             "lock_conflict": re.compile(r"both claim exclusive '(.+)'"),
             "missing_permission": re.compile(r"permission '(.+)' not granted"),
             "limit_exceeded": re.compile(r"^(\S+)=")}


# --------------------------------------------------------------------------- #
# Frozen wrapper around the checker (Section 8)                                #
# --------------------------------------------------------------------------- #
def ecm_findings(enc: dict) -> Tuple[List[dict], List[str]]:
    """Finding instances of the frozen checker; unevaluable rules listed separately."""
    case = copy.deepcopy(enc)
    unevaluable = []
    if case.get("type") == "UPGRADE":
        vd = case.get("ver_delta") or {}
        so, sn = vd.get("semver_old"), vd.get("semver_new")
        if so is None or sn is None:
            so = sn = None
            unevaluable.append("semver_major")
        case["old"] = {"interface_hash": None, "semver": so}
        case["new"] = {"interface_hash": None, "semver": sn, "changed_fields": vd.get("changed_fields") or []}
        case["consumer_reads"] = vd.get("consumer_reads") or []
    case.setdefault("edge", {})
    out = []
    for f in all_findings(case):
        if f.severity != Severity.CRITICAL or f.check_type not in ECM_FULL.checks:
            continue
        tok = None
        m = _TOKEN_RE.get(f.check_type)
        if m:
            mm = m.search(f.detail)
            tok = mm.group(1) if mm else None
        out.append({"rule": f.check_type, "dimension": f.dimension, "token": tok, "detail": f.detail})
    return out, unevaluable


def norm(s: Optional[str]) -> str:
    if s is None:
        return ""
    s = s.strip().lower()
    if ":" in s:
        kind, name = s.split(":", 1)
        return f"{kind}:{name.lstrip('/')}"
    return s.lstrip("/")


def token_matches(token: str, implicated: List[str], cls: str) -> bool:
    t = norm(token)
    for el in implicated:
        e = norm(el)
        if t == e or t == e.split(":", 1)[-1] or (":" in e and t == e.split(":", 1)[1]):
            return True
        if cls == "definition_mismatch":
            # a field token matches its message parent and vice versa
            if e.startswith("msg:") and t.startswith("field:") and t[6:].split(".")[0] == e[4:]:
                return True
            if t.startswith("msg:") and e.startswith("field:") and e[6:].split(".")[0] == t[4:]:
                return True
    return False


def edge_matches(f: dict, implicated: List[str], cls: str) -> bool:
    """An edge-level finding matches when its edge element is implicated or, for a
    definition mismatch, when the message type carried on that edge is implicated."""
    if token_matches(f.get("element") or "", implicated, cls):
        return True
    if cls == "definition_mismatch" and f.get("msg_type"):
        return token_matches("msg:" + f["msg_type"], implicated, cls)
    return False


# --------------------------------------------------------------------------- #
# Trigger paths and provenance                                                 #
# --------------------------------------------------------------------------- #
def ecm_trigger_paths(rule: str, token: Optional[str]) -> List[str]:
    po, pi = "producer.outputs[0]", "consumer.inputs[0]"
    return {
        "type_mismatch": [f"{po}.msg_type", f"{pi}.msg_type"],
        "frame_mismatch": [f"{po}.frame", f"{pi}.frame"],
        "unit_mismatch": [f"{po}.units", f"{pi}.units"],
        "qos_reliability": [f"{po}.qos.reliability", f"{pi}.qos.reliability"],
        "qos_durability": [f"{po}.qos.durability", f"{pi}.qos.durability"],
        "qos_deadline": [f"{pi}.qos.deadline_ms", f"{po}.rate_hz"],
        "rate_starvation": [f"{po}.rate_hz", f"{pi}.min_rate_hz"],
        "lock_conflict": [f"producer.exclusive[{token}]", f"consumer.exclusive[{token}]"],
        "missing_permission": [f"consumer.perm_requires[{token}]", "producer.perm_grants", "consumer.perm_grants"],
        "limit_exceeded": [f"producer.perm_limits[{token}]", f"consumer.perm_limits[{token}]"],
        "field_break": [f"ver_delta.changed_fields[{token}]", f"ver_delta.consumer_reads[{token}]"],
        "semver_major": ["ver_delta.semver_old", "ver_delta.semver_new"],
    }[rule]


def provenance_state(paths: List[str], prov: Dict[str, str], verdicts: Dict[str, str], enc: dict) -> str:
    """verified | unverified. A path is verified when it has a provenance entry and no
    adjudicator marked it wrong or unverifiable. Grant sets must be in state `absent`."""
    for p in paths:
        if p.endswith(".perm_grants"):
            side = p.split(".")[0]
            if ((enc.get(side) or {}).get("_states") or {}).get("perm_grants") != "absent":
                return "unverified"
            continue
        if not prov.get(p):
            return "unverified"
        if verdicts.get(p) in ("wrong", "unverifiable"):
            return "unverified"
    return "verified"


# --------------------------------------------------------------------------- #
# Per composition                                                              #
# --------------------------------------------------------------------------- #
def run_unit(unit: dict) -> Dict[str, List[dict]]:
    """Finding instances per method for one assembled unit."""
    enc, kind = unit["encoding"], unit["kind"]
    out: Dict[str, List[dict]] = {m: [] for m in METHODS}
    out["_unevaluable"] = []
    mt = None
    if kind in ("edge", "pair_view"):
        ins = (enc.get("consumer") or {}).get("inputs") or []
        mt = ins[0].get("msg_type") if ins else None
    if kind in ("edge", "upgrade"):
        fs, unev = ecm_findings(enc)
        out["ECM"] = [dict(f, element=unit["element"] if kind == "edge" else f["token"], msg_type=mt) for f in fs]
        out["_unevaluable"] = unev
    if kind in ("edge", "pair_view"):
        for m in ("NT", "DI", "DQ"):
            out[m] = [dict(f, element=unit["element"], msg_type=mt) for f in B.BASELINES[m](enc)]
    if kind == "upgrade":
        out["SV"] = [dict(f, element=None) for f in B.BASELINES["SV"](enc)]
    return out


def score_composition(comp: dict, conditions: List[dict], operation: str, verdicts: Dict[str, str]) -> Dict[str, dict]:
    """Section 10 states per method for one composition."""
    res: Dict[str, dict] = {}
    if comp["status"] != "done":
        return {m: {"state": "unassessable", "reason": comp.get("reason"), "findings": []} for m in METHODS}
    per_method: Dict[str, List[dict]] = {m: [] for m in METHODS}
    unevaluable = set()
    for unit in comp["units"]:
        if unit["status"] != "done":
            continue
        r = run_unit(unit)
        unevaluable.update(r["_unevaluable"])
        for m in METHODS:
            for f in r[m]:
                f = dict(f)
                paths = (ecm_trigger_paths(f["rule"], f.get("token")) if m == "ECM"
                         else B.trigger_paths(f["rule"], "producer.outputs[0]", "consumer.inputs[0]"))
                f["provenance"] = provenance_state(paths, unit["provenance"], verdicts, unit["encoding"])
                f["unit_kind"] = unit["kind"]
                per_method[m].append(f)
    for m in METHODS:
        fs = per_method[m]
        matched_verified, matched_unverified = [], []
        unsupported = conditions and all(c["class"] in ("other", "recovery_conflict", "representation_convention") for c in conditions)
        if operation == "SWITCH":
            state = "not_supported"  # no implemented check applies; raw findings are kept
        elif unsupported:
            state = "wrong_reason" if fs else "not_supported"
        else:
            for c in conditions:
                for (mm, rule, how) in MATCH.get(c["class"], []):
                    if mm != m:
                        continue
                    for f in fs:
                        if f["rule"] != rule:
                            continue
                        ok = (token_matches(f.get("token") or "", c["implicated_elements"], c["class"]) if how == "token"
                              else edge_matches(f, c["implicated_elements"], c["class"]))
                        if not ok:
                            continue
                        (matched_verified if f["provenance"] == "verified" else matched_unverified).append(
                            {"class": c["class"], "rule": rule, "element": f.get("element"), "token": f.get("token")})
            if matched_verified:
                state = "right_reason"
            elif matched_unverified:
                state = "unverified"
            elif fs:
                state = "wrong_reason"
            else:
                state = "accept"
        res[m] = {"state": state, "reject": bool(fs), "findings": fs,
                  "matched": matched_verified if state == "right_reason" else
                  (matched_unverified if state == "unverified" else []),
                  "unevaluable": sorted(unevaluable) if m == "ECM" else []}
    return res


def score_control(comp: dict, verdicts: Dict[str, str]) -> Dict[str, dict]:
    if comp is None:
        return {}
    if comp["status"] != "done":
        return {m: {"state": "unassessable", "reason": comp.get("reason")} for m in METHODS}
    out = {m: {"state": "accept", "findings": []} for m in METHODS}
    for unit in comp["units"]:
        if unit["status"] != "done":
            continue
        r = run_unit(unit)
        for m in METHODS:
            if r[m]:
                out[m]["state"] = "reject"
                out[m]["findings"].extend(r[m])
    return out


# --------------------------------------------------------------------------- #
# Statistics                                                                   #
# --------------------------------------------------------------------------- #
def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) * 0.5 ** n)


def rate(k: int, n: int) -> dict:
    return {"k": k, "n": n, "rate": (k / n if n else None), "wilson95": wilson(k, n),
            "reason": None if n else "no_observations"}


# --------------------------------------------------------------------------- #
# Aggregation (Section 12)                                                     #
# --------------------------------------------------------------------------- #
def aggregate(rows: List[dict], complete_case: bool = False) -> dict:
    def st(r, m):
        return r["broken"][m]["state"]
    fails = [r for r in rows if r["outcome_class"] == "failure"]
    if complete_case:
        fails = [r for r in fails if r["assembled_status"] == "done"]
    silent = [r for r in fails if r["loudness"] == "silent_documented"]
    unknown_loud = [r for r in fails if r["loudness"] == "unknown"]
    ctl_obs = [r for r in rows if r["resolved"] and r["resolution_status"] == "observed"]
    ctl_rec = [r for r in rows if r["resolved"] and r["resolution_status"] == "recommended"]
    ctl_warn = [r for r in rows if r["outcome_class"] == "warning_only"]
    if complete_case:
        ctl_obs = [r for r in ctl_obs if r["resolved"]["ECM"]["state"] != "unassessable"]
        ctl_rec = [r for r in ctl_rec if r["resolved"]["ECM"]["state"] != "unassessable"]
        ctl_warn = [r for r in ctl_warn if r["assembled_status"] == "done"]
    out = {"n_failures": len(fails), "n_silent": len(silent), "n_loudness_unknown": len(unknown_loud),
           "n_unassessable_failures": sum(1 for r in fails if r["assembled_status"] != "done"),
           "n_controls": {"fixed_observed": len(ctl_obs), "fixed_recommended": len(ctl_rec), "warning_only": len(ctl_warn)},
           "methods": {}, "pairwise": {}, "hit_matrix": {}, "undetected_by_class": {}, "by_class": {}}
    for m in METHODS:
        rr = [r["case_id"] for r in fails if st(r, m) == "right_reason"]
        rs = [r["case_id"] for r in silent if st(r, m) == "right_reason"]
        binary = [r["case_id"] for r in fails if st(r, m) in ("right_reason", "unverified", "wrong_reason")]
        fa_obs = [r["case_id"] for r in ctl_obs if r["resolved"][m]["state"] == "reject"]
        fa_rec = [r["case_id"] for r in ctl_rec if r["resolved"][m]["state"] == "reject"]
        fa_warn = [r["case_id"] for r in ctl_warn if st(r, m) in ("right_reason", "unverified", "wrong_reason")]
        tp, fn = len(rr), len(fails) - len(rr)
        fp = len(fa_obs) + len(fa_warn)
        tn = len(ctl_obs) + len(ctl_warn) - fp
        prec = tp / (tp + fp) if tp + fp else None
        rec = tp / (tp + fn) if tp + fn else None
        f1 = (2 * prec * rec / (prec + rec)) if prec and rec else (0.0 if (prec is not None and rec is not None) else None)
        out["methods"][m] = {
            "right_reason": dict(rate(tp, len(fails)), cases=rr),
            "right_reason_silent": dict(rate(len(rs), len(silent)), cases=rs),
            "binary_reject": dict(rate(len(binary), len(fails)), cases=binary),
            "states": {s: [r["case_id"] for r in fails if st(r, m) == s]
                       for s in ("right_reason", "unverified", "wrong_reason", "accept", "not_supported", "unassessable")},
            "false_alarm_fixed_observed": dict(rate(len(fa_obs), len(ctl_obs)), cases=fa_obs),
            "false_alarm_fixed_recommended": dict(rate(len(fa_rec), len(ctl_rec)), cases=fa_rec),
            "false_alarm_warning_only": dict(rate(len(fa_warn), len(ctl_warn)), cases=fa_warn),
            "case_control": {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": prec, "recall": rec, "f1": f1,
                             "prevalence": (len(fails) / (len(fails) + len(ctl_obs) + len(ctl_warn))
                                            if fails or ctl_obs or ctl_warn else None)},
        }
    for r in fails:
        out["hit_matrix"][r["case_id"]] = {m: st(r, m) == "right_reason" for m in METHODS}
    for scope, pool in (("all_failures", fails), ("silent_failures", silent)):
        for i, a in enumerate(METHODS):
            for bname in METHODS[i + 1:]:
                A = {r["case_id"] for r in pool if st(r, a) == "right_reason"}
                Bs = {r["case_id"] for r in pool if st(r, bname) == "right_reason"}
                b, c = len(A - Bs), len(Bs - A)
                nested = (a == "ECM" and bname in B.NESTED_IN_ECM)
                out["pairwise"][f"{scope}:{a}_vs_{bname}"] = {
                    "b_first_only": b, "c_second_only": c, "both": len(A & Bs), "neither": len(pool) - len(A | Bs),
                    "structurally_nested": nested,
                    "mcnemar_exact_p": None if nested else mcnemar_exact(b, c),
                    "wilson95_b_over_discordant": wilson(b, b + c)}
    union = {r["case_id"] for r in fails if any(st(r, m) == "right_reason" for m in METHODS)}
    out["union_detected"] = rate(len(union), len(fails))
    for r in fails:
        for c in r["classes"]:
            out["by_class"].setdefault(c, {"n": 0, **{m: 0 for m in METHODS}})
            out["by_class"][c]["n"] += 1
            for m in METHODS:
                out["by_class"][c][m] += st(r, m) == "right_reason"
        if r["case_id"] not in union:
            for c in r["classes"]:
                out["undetected_by_class"].setdefault(c, []).append(r["case_id"])
    return out


C3_PLANNED_N = 40
C3_PER_REPO_CAP = 6


def c3_selection(specs: Dict[str, dict]) -> dict:
    """PROTOCOL.md Section 3: walk the frozen C3 order; eligible failures are selected until
    C3_PLANNED_N, at most C3_PER_REPO_CAP per repository. Every candidate up to the stop point
    must have been specified, except candidates of a repository already at its cap (skipped).
    Returns {status, stop_index, selected, capped, after_stop, skipped_capped_repo, first_missing}."""
    order_p = os.path.join(HERE, "candidates", "C3_order.json")
    ledger_p = os.path.join(HERE, "candidates", "C3_ledger.json")
    if not (os.path.exists(order_p) and os.path.exists(ledger_p)):
        return {"status": "no_c3", "selected": [], "capped": [], "after_stop": [], "skipped_capped_repo": []}
    urls = json.load(open(order_p))["ordered"]
    hits = json.load(open(ledger_p))["hits"]
    per_repo, selected, capped, skipped = {}, [], [], []
    status, stop_index, first_missing = "incomplete", None, None
    for i, url in enumerate(urls):
        cid, repo = f"C3-{i + 1:03d}", hits[url]["repo"]
        spec = specs.get(cid)
        if per_repo.get(repo, 0) >= C3_PER_REPO_CAP:
            if spec is None:
                skipped.append(cid)
            elif spec.get("eligible") and spec.get("outcome_class") == "failure":
                capped.append(cid)
            continue
        if spec is None:
            first_missing = cid
            break
        if spec.get("eligible") and spec.get("outcome_class") == "failure":
            selected.append(cid)
            per_repo[repo] = per_repo.get(repo, 0) + 1
            if len(selected) == C3_PLANNED_N:
                status, stop_index = "reached", i
                break
    else:
        status = "exhausted"
    after = [f"C3-{j + 1:03d}" for j in range((stop_index if stop_index is not None else len(urls)) + 1, len(urls))
             if f"C3-{j + 1:03d}" in specs] if status == "reached" else []
    return {"status": status, "stop_index": stop_index, "first_missing": first_missing, "selected": selected,
            "capped": capped, "after_stop": after, "skipped_capped_repo": skipped, "per_repo": per_repo}


def h1_record(rows: List[dict]) -> dict:
    fails = [r for r in rows if r["corpus"] == "C3" and r["outcome_class"] == "failure" and r.get("c3_selected")]
    E = {r["case_id"] for r in fails if r["broken"]["ECM"]["state"] == "right_reason"}
    D = {r["case_id"] for r in fails if r["broken"]["DQ"]["state"] == "right_reason"}
    b, c = len(E - D), len(D - E)
    return {"hypothesis": "H1: ECM right-reason detection > DQ on eligible C3 failures (pre-registered)",
            "n_eligible_failures": len(fails), "planned_n": 40, "underpowered": len(fails) < 40,
            "b_ecm_only": b, "c_dq_only": c, "both": len(E & D), "neither": len(fails) - len(E | D),
            "mcnemar_exact_two_sided_p": mcnemar_exact(b, c), "alpha": 0.05,
            "min_relevant_gain": 4, "gain_b_minus_c": b - c, "wilson95_b_over_discordant": wilson(b, b + c)}


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def load_specs(adjudicated: bool) -> Dict[str, dict]:
    specs = {}
    for f in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        s = json.load(open(f))
        specs[s["case_id"]] = s
    if adjudicated:
        ov = os.path.join(HERE, "adjudicated", "overrides.json")
        if os.path.exists(ov):
            for cid, o in json.load(open(ov)).items():
                if cid in specs:
                    specs[cid].update(o)
                    specs[cid]["_adjudication_changed"] = True
    return specs


def main(write: bool, adjudicated: bool) -> None:
    specs = load_specs(adjudicated)
    verdicts_all = {}
    if adjudicated:
        p = os.path.join(HERE, "adjudicated", "provenance_verdicts.json")
        verdicts_all = json.load(open(p)) if os.path.exists(p) else {}
    rows = []
    pilot_p = os.path.join(HERE, "pilot", "PILOT_CASES.json")
    pilot = set(json.load(open(pilot_p))["quarantined_pilot_cases"]) if os.path.exists(pilot_p) else set()
    models_p = os.path.join(HERE, "ledger", "s1_models.json")
    s1_models = json.load(open(models_p)) if os.path.exists(models_p) else {}
    sel = c3_selection(specs)
    selected, excluded_c3 = set(sel["selected"]), set(sel["capped"]) | set(sel["after_stop"])
    for cid, spec in specs.items():
        if cid in pilot:
            continue  # quarantined pilot case (Section 14): reported as pilot, never as a result
        if spec.get("corpus") == "C3" and cid in excluded_c3:
            continue  # beyond the C3 stop rule (Section 3); counted in the funnel only
        if not spec.get("eligible"):
            continue
        for c in spec.get("failed_conditions") or []:
            assert c["class"] in CLASSES, (cid, c["class"])
        a = json.load(open(os.path.join(HERE, "assembled", f"{cid}.json"))) if os.path.exists(
            os.path.join(HERE, "assembled", f"{cid}.json")) else \
            {"status": "unassessable", "reason": "not_assembled",
             "compositions": {"broken": {"status": "unassessable", "reason": "not_assembled", "units": []}, "resolved": None}}
        v = verdicts_all.get(cid, {})
        conds = spec.get("failed_conditions") or []
        row = {"case_id": cid, "corpus": spec["corpus"], "operation": spec["operation"],
               "outcome_class": spec["outcome_class"], "loudness": spec.get("loudness"),
               "detection_stage": spec.get("detection_stage"), "classes": sorted({c["class"] for c in conds}),
               "resolution_status": (spec.get("resolution") or {}).get("status"),
               "ros_generation": spec.get("ros_generation"), "excerpt_based": bool(spec.get("excerpt_based")),
               "unpinned": any(not u.get("pinned") for u in spec.get("units") or []),
               "single_composition": a["compositions"]["resolved"] is None,
               "adjudication_changed": bool(spec.get("_adjudication_changed")),
               "built_against_basis": ((spec.get("consumer_built_against") or {}).get("basis")
                                       if spec["operation"] == "UPGRADE" else "n/a"),
               "s1_model": (s1_models.get(cid) or {}).get("model", "claude-opus-5-5" if spec["corpus"] in ("C3", "C3N") else None),
               "c3_selected": cid in selected,
               "assembled_status": a["status"], "assembled_reason": a.get("reason"),
               "broken": score_composition(a["compositions"]["broken"], conds, spec["operation"], v.get("broken", {})),
               "resolved": score_control(a["compositions"]["resolved"], v.get("resolved", {})) or None}
        rows.append(row)
    results = {"adjudicated": adjudicated, "n_rows": len(rows), "by_corpus": {}, "strata": {}}
    for corpus in sorted({r["corpus"] for r in rows}):
        rs = [r for r in rows if r["corpus"] == corpus]
        results["by_corpus"][corpus] = {"primary_all_eligible": aggregate(rs), "complete_case": aggregate(rs, True)}
    results["pilot_excluded"] = sorted(pilot & set(specs))
    results["c3_selection"] = sel
    for name, key in (("ros_generation", "ros_generation"), ("excerpt_based", "excerpt_based"),
                      ("unpinned", "unpinned"), ("single_composition", "single_composition"),
                      ("adjudication_changed", "adjudication_changed"), ("built_against_basis", "built_against_basis"),
                      ("s1_model", "s1_model")):
        results["strata"][name] = {}
        for val in sorted({str(r[key]) for r in rows}):
            results["strata"][name][val] = {m: aggregate([r for r in rows if str(r[key]) == val])["methods"][m]["right_reason"]
                                            for m in METHODS}
    results["H1"] = h1_record(rows)
    if write:
        os.makedirs(os.path.join(HERE, "scores"), exist_ok=True)
        for r in rows:
            json.dump(r, open(os.path.join(HERE, "scores", f"{r['case_id']}.json"), "w"), indent=1, allow_nan=False)
        out = "results_adjudicated.json" if adjudicated else "results.json"
        json.dump(results, open(os.path.join(HERE, out), "w"), indent=1, allow_nan=False)
    for corpus, res in results["by_corpus"].items():
        p = res["primary_all_eligible"]
        print(corpus, "failures", p["n_failures"], "unassessable", p["n_unassessable_failures"],
              {m: p["methods"][m]["right_reason"]["k"] for m in METHODS})
    print("H1", {k: results["H1"][k] for k in ("n_eligible_failures", "b_ecm_only", "c_dq_only", "mcnemar_exact_two_sided_p")})


if __name__ == "__main__":
    main("--write" in sys.argv, "--adjudicated" in sys.argv)
