"""Tables and numbers added after the pre-dispatch audit of 2026-09-30 (V19-EMSE/audit/
2026-09-30-predispatch-audit-triage.md), called from make_report.main().

Every table here is computed with the scorer's own aggregate() over the per-case score files, on the same
population as results_adjudicated.json (pilot cases left out; C3 failures outside the pre-specified selection
left out, their controls kept); build() checks that this population reproduces results_adjudicated.json before
writing anything. The calling module is passed in as `mr` (make_report runs as __main__, so importing it here
would create a second copy with its own NUMBERS).
"""
from __future__ import annotations

import collections
import glob
import json
import os
from typing import Dict, List

import scoring as S

HERE = os.path.dirname(os.path.abspath(__file__))
METHODS = S.METHODS
CORPORA = ["C1", "C2", "C3", "C3N"]

STRATA = [("ros_generation", "ROS generation"), ("excerpt_based", "Description source"),
          ("unpinned", "Unit revision"), ("single_composition", "Compositions scored"),
          ("built_against_basis", "Built-against revision"), ("s1_model", "Specification model"),
          ("same_repository", "Units")]
VALUE_LABELS = {("excerpt_based", "False"): "code snapshot", ("excerpt_based", "True"): "quoted artifact",
                ("unpinned", "False"): "pinned", ("unpinned", "True"): "unpinned",
                ("single_composition", "False"): "broken and fixed", ("single_composition", "True"): "broken only",
                ("same_repository", "False"): "different repositories", ("same_repository", "True"): "one repository",
                ("built_against_basis", "documented"): "documented", ("built_against_basis", "inferred"): "inferred",
                ("built_against_basis", "n/a"): "not an upgrade",
                ("s1_model", "claude-fable-5-1"): "Claude Fable 5.1", ("s1_model", "claude-opus-5-5"): "Claude Opus 5.5",
                ("ros_generation", "ROS1"): "ROS 1", ("ros_generation", "ROS2"): "ROS 2", ("ros_generation", "other"): "other"}
STAGES = [("build", "build"), ("connect", "connection"), ("activate", "activation"), ("run", "run time")]
REASONS = {"no_assessable_unit": "no interaction edge assembled", "evidence_inadequate": "evidence inadequate",
           "revision_unresolved": "revision unresolved"}
ROLES = {"producer": "provider", "consumer": "consumer", "provider_built": "provider (built against)"}


def load(name):
    p = os.path.join(HERE, name)
    return json.load(open(p)) if os.path.exists(p) else None


def rows(score_dir: str = "scores_adjudicated", results_name: str = "results_adjudicated.json") -> List[dict]:
    res = load(results_name)
    pilot = set(res["pilot_excluded"])
    out = []
    for f in sorted(glob.glob(os.path.join(HERE, score_dir, "*.json"))):
        r = json.load(open(f))
        if r["case_id"] in pilot:
            continue
        if r["corpus"] == "C3" and r["outcome_class"] == "failure" and not r.get("c3_selected"):
            continue
        out.append(r)
    got = S.by_corpus(out)
    if any(got.get(c) != res["by_corpus"][c] for c in res["by_corpus"]):
        raise SystemExit(f"population rebuilt from {score_dir} does not reproduce {results_name}")
    return out


def of(rs, corpus):
    return [r for r in rs if r["corpus"] == corpus]


def label(key, val):
    return VALUE_LABELS.get((key, val), val)


# --------------------------------------------------------------------------- strata, per corpus
def strata(mr, rs) -> str:
    """Checker right-reason detection per stratum, one column per corpus (PROTOCOL.md Section 12: per corpus,
    never pooled). A stratum with one value in every corpus carries no information and is left out; it is
    named in NUMBERS['strata_single_valued']."""
    body, single, data = [], [], {}
    for key, name in STRATA:
        vals = sorted({str(r[key]) for r in rs if r["outcome_class"] == "failure"})
        if len(vals) < 2:
            single.append(key)
            continue
        first = True
        for v in vals:
            cells, row_data = [], {}
            for c in CORPORA:
                agg = S.aggregate([r for r in of(rs, c) if str(r[key]) == v])
                rr = agg["methods"]["ECM"]["right_reason"]
                row_data[c] = {m: agg["methods"][m]["right_reason"] for m in METHODS}
                cells.append(mr.frac(rr["k"], rr["n"]))
            if all(row_data[c]["ECM"]["n"] == 0 for c in CORPORA):
                continue
            data.setdefault(key, {})[v] = row_data
            body.append([name if first else "", label(key, v)] + cells)
            first = False
    mr.NUMBERS["strata_per_corpus"] = data
    mr.NUMBERS["strata_single_valued"] = single
    return mr.tabular("llrrrr", ["Stratum", "Value"] + [mr.CORPUS_NAMES[c].split(" (")[0] for c in CORPORA], body)


def strata_all_methods(mr, rs) -> str:
    """Appendix: every method's right-reason detections per stratum and corpus (k; the denominator is the
    stratum's failure count, the same for every method)."""
    body = []
    for c in CORPORA:
        body.append([f"\\multicolumn{{8}}{{@{{}}l}}{{\\emph{{{mr.CORPUS_NAMES[c]}}}}}"])
        for key, name in STRATA:
            for v in sorted({str(r[key]) for r in of(rs, c) if r["outcome_class"] == "failure"}):
                agg = S.aggregate([r for r in of(rs, c) if str(r[key]) == v])
                n = agg["n_failures"]
                if n == 0:
                    continue
                body.append([name, label(key, v), str(n)] + [str(agg["methods"][m]["right_reason"]["k"]) for m in METHODS])
    return mr.tabular("llrrrrrr", ["Stratum", "Value", "Failures"] + METHODS, body)


# --------------------------------------------------------------------------- RQ2: detection stage
def detection_stage(mr, rs) -> str:
    """Per corpus and documented detection stage: failures, documented-silent failures, and right-reason
    detections per method; the unknown-loudness stratum as its own row (PROTOCOL.md Section 12, RQ2)."""
    body, data = [], {}
    for c in CORPORA:
        fails = [r for r in of(rs, c) if r["outcome_class"] == "failure"]
        first = True
        for key, name in STAGES:
            # a failure of unknown loudness gets its own row below and is not counted under its stage too
            sub = [r for r in fails if r.get("detection_stage") == key and r["loudness"] != "unknown"]
            if not sub:
                continue
            agg = S.aggregate(sub)
            silent = sum(r["loudness"] == "silent_documented" for r in sub)
            data.setdefault(c, {})[key] = {"n": len(sub), "silent": silent,
                                           **{m: agg["methods"][m]["right_reason"]["k"] for m in METHODS}}
            body.append([mr.CORPUS_NAMES[c].split(" (")[0] if first else "", name, str(len(sub)), str(silent)]
                        + [str(agg["methods"][m]["right_reason"]["k"]) for m in METHODS])
            first = False
        unk = [r for r in fails if r["loudness"] == "unknown"]
        if unk:
            agg = S.aggregate(unk)
            data.setdefault(c, {})["loudness_unknown"] = {"n": len(unk), "cases": [r["case_id"] for r in unk],
                                                          **{m: agg["methods"][m]["right_reason"]["k"] for m in METHODS}}
            body.append(["", "loudness unknown", str(len(unk)), "--"] + [str(agg["methods"][m]["right_reason"]["k"]) for m in METHODS])
    mr.NUMBERS["detection_stage"] = data
    return mr.tabular("llrrrrrrr", ["Corpus", "Stage", "Failures", "Silent"] + METHODS, body)


# --------------------------------------------------------------------------- Appendix C tables
def hit_matrix(mr, rs) -> str:
    """Every failure that at least one method detects for the right reason, with the method marks; the
    caption states how many failures per corpus no method detects."""
    body, none = [], {}
    for c in CORPORA:
        fails = [r for r in of(rs, c) if r["outcome_class"] == "failure"]
        hit = [r for r in fails if any(r["broken"][m]["state"] == "right_reason" for m in METHODS)]
        none[c] = len(fails) - len(hit)
        for r in sorted(hit, key=lambda x: x["case_id"]):
            body.append([mr.tex(r["case_id"]), mr.CORPUS_NAMES[c].split(" (")[0], r["operation"]]
                        + [("$\\bullet$" if r["broken"][m]["state"] == "right_reason" else "") for m in METHODS])
    mr.NUMBERS["hit_matrix_no_detection"] = none
    return mr.tabular("lll" + "c" * len(METHODS), ["Case", "Corpus", "Operation"] + METHODS, body)


def complete_case(mr, res) -> str:
    """Right-reason detection per corpus and method over the assessable failures only (secondary reading)."""
    body = []
    for c in CORPORA:
        p = res["by_corpus"][c]["complete_case"]
        body.append([mr.CORPUS_NAMES[c], str(p["n_failures"])] + [mr.kn_ci(p["methods"][m]["right_reason"]) for m in METHODS])
    mr.NUMBERS["complete_case"] = {c: {m: res["by_corpus"][c]["complete_case"]["methods"][m]["right_reason"] for m in METHODS}
                                   for c in CORPORA}
    return mr.tabular("lr" + "r" * len(METHODS), ["Corpus", "Assessable"] + METHODS, body)


def sensitivity_detail(mr, res) -> str:
    """Right-reason detection per corpus and method, and the checker's false alarms on observed fixes, under
    the primary analysis, each declared sensitivity, and the strict-adjudicator fold."""
    analyses = [("primary", res["by_corpus"])] + [(k, v["by_corpus"]) for k, v in res["sensitivity"].items()]
    adj1 = load("results_adjudicated_adj1only.json")
    if adj1 is not None:
        analyses.append(("strict-adjudicator fold", adj1["by_corpus"]))
    body = []
    for name, bc in analyses:
        first = True
        for c in CORPORA:
            if c not in bc:
                continue
            p = bc[c]["primary_all_eligible"]
            lab = name if name in ("primary", "strict-adjudicator fold") else mr.brk(mr.tex(name))
            if name in res["sensitivity"] and not res["sensitivity"][name].get("declared_in_advance"):
                lab += " (exploratory)"
            body.append([lab if first else "", mr.CORPUS_NAMES[c].split(" (")[0]]
                        + [mr.kn(p["methods"][m]["right_reason"]) for m in METHODS]
                        + [mr.kn(p["methods"]["ECM"]["false_alarm_fixed_observed"])])
            first = False
    return mr.tabular("p{2.6cm}l" + "r" * (len(METHODS) + 1), ["Analysis", "Corpus"] + METHODS + ["ECM false alarms"], body)


def resolution_shift(mr) -> None:
    """Cases scored under both the primary and the strict-adjudicator fold whose resolution status the
    strict fold changes; a changed status moves a fixed composition between the observed-fixed and the
    recommended-fixed controls, which is why that fold's observed-fixed denominators differ."""
    if load("results_adjudicated_adj1only.json") is None:
        return
    a = {r["case_id"]: r for r in rows()}
    b = {r["case_id"]: r for r in rows("scores_adjudicated_adj1only", "results_adjudicated_adj1only.json")}
    shift: Dict[str, int] = collections.Counter()
    for cid in sorted(a.keys() & b.keys()):
        x, y = a[cid].get("resolution_status"), b[cid].get("resolution_status")
        if x != y:
            shift[f"{a[cid]['corpus']}:{x}->{y}"] += 1
    mr.NUMBERS["adj1only_resolution_shift"] = dict(sorted(shift.items()))


def _served_tasks():
    """Tasks with a returned description that serve at least one non-pilot case."""
    led = load("ledger/tasks.json")["tasks"]
    pilot = set(load("results_adjudicated.json")["pilot_excluded"])
    for t, e in sorted(led.items()):
        if e["status"] not in ("done", "excerpt") or not [c for c in e.get("cases", []) if c not in pilot]:
            continue
        r = load(f"s2_work/tasks/{t}/recon/{t}.json")
        if r:
            yield t, e, r


def unit_fields(mr) -> None:
    """Unit-level contract fields (exclusive claims, permission requirements and grants, recovery) recorded
    per description, and the tasks and cases whose permission requirement is present (R1 review, peer review m1/m10)."""
    tot = collections.Counter()
    have = collections.Counter()
    perm = []
    for t, e, r in _served_tasks():
        tot["descriptions"] += 1
        have["exclusive"] += bool(r.get("exclusive"))
        for k in ("perm_requires", "perm_grants"):
            v = r.get(k) or {}
            have[k] += v.get("state") == "present" and bool(v.get("values"))
        rec = r.get("recovery") or {}
        have["recovery"] += rec.get("state") == "present"
        pr = r.get("perm_requires") or {}
        if pr.get("state") == "present" and pr.get("values"):
            perm.append({"task": t, "cases": sorted(e.get("cases", []))})
    specs = {}
    for p in perm:
        for c in p["cases"]:
            s = load(f"specs/{c}.json") or {}
            specs[c] = {"operation": s.get("operation"), "outcome_class": s.get("outcome_class")}
    mr.NUMBERS["unit_fields"] = {"descriptions": tot["descriptions"], **{k: have[k] for k in ("exclusive", "perm_requires", "perm_grants", "recovery")}}
    mr.NUMBERS["perm_requires_present"] = {"tasks": perm, "cases": specs}


def nt_pair_views(mr) -> None:
    """On UPGRADE cases the checker reads the declaration delta and NT the pair views; count the assembled pair
    views whose two message types differ, the only place NT could credit a failure the checker misses (R1 review)."""
    pilot = set(load("results_adjudicated.json")["pilot_excluded"])
    n = diff = 0
    cases = set()
    for f in sorted(glob.glob(os.path.join(HERE, "assembled", "*.json"))):
        a = json.load(open(f))
        if a["case_id"] in pilot or a.get("operation") != "UPGRADE":
            continue
        for comp in (a["compositions"].get("broken"), a["compositions"].get("resolved")):
            for u in (comp or {}).get("units", []):
                if u.get("kind") != "pair_view" or u.get("status") != "done":
                    continue
                enc = u.get("encoding") or {}
                out = ((enc.get("producer") or {}).get("outputs") or [{}])[0].get("msg_type")
                inp = ((enc.get("consumer") or {}).get("inputs") or [{}])[0].get("msg_type")
                n += 1
                if out and inp and out != inp:
                    diff += 1
                    cases.add(a["case_id"])
    mr.NUMBERS["nt_upgrade_pair_views"] = {"done": n, "types_differ": diff, "cases": sorted(cases)}


REJECT_STATES = ("right_reason", "unverified", "wrong_reason")


def alert_ratios(mr, rs) -> None:
    """Supplementary to the case-control matrices (R1 review, external review F3): over the documented failures and the
    observed-fixed and warning-only controls of each corpus, the share of rejected compositions that are
    failures (binary positive predictive value, by findings), and the share of all rejections by findings that
    name the documented cause: a right-reason detection of a failure, or a warning-only case rejected for its
    documented condition (pre-R2 audit, 2026-09-30). Neither is a deployment precision."""
    out = {}
    for c in CORPORA:
        rows_c = of(rs, c)
        fails = [r for r in rows_c if r["outcome_class"] == "failure"]
        rr = sum(r["broken"]["ECM"]["state"] == "right_reason" for r in fails)
        rej = sum(r["broken"]["ECM"]["state"] in REJECT_STATES for r in fails)
        ctl_find = ctl_bound = warn_cause = 0
        for r in rows_c:
            if r.get("resolution_status") == "observed" and r.get("resolved"):
                st = r["resolved"]["ECM"]["state"]
                ctl_find += st == "reject"
                ctl_bound += st in ("reject", "unassessable")
            if r["outcome_class"] == "warning_only":
                st = r["broken"]["ECM"]["state"]
                ctl_find += st in REJECT_STATES
                ctl_bound += st in REJECT_STATES + ("unassessable",)
                warn_cause += st == "right_reason"
        den = rej + ctl_find
        out[c] = {"right_reason": rr, "rejected_failures": rej, "controls_rejected_by_findings": ctl_find,
                  "controls_rejected_under_bound": ctl_bound,
                  "warning_only_rejected_for_documented_cause": warn_cause,
                  "binary_ppv": [rej, den], "cause_correct_share": [rr + warn_cause, den]}
    mr.NUMBERS["alert_ratios"] = out


def unassessable(mr, rs) -> str:
    """Every scored case whose composition could not be assembled, with the reason."""
    body, count = [], collections.Counter()
    for r in sorted(rs, key=lambda x: (CORPORA.index(x["corpus"]), x["case_id"])):
        if r["assembled_status"] == "done":
            continue
        reason = r.get("assembled_reason") or "?"
        role, _, why = reason.partition(":")
        text = REASONS.get(reason) or f"{ROLES.get(role, role)}: {REASONS.get(why, why.replace('_', ' '))}"
        count[(r["corpus"], r["outcome_class"])] += 1
        body.append([mr.tex(r["case_id"]), mr.CORPUS_NAMES[r["corpus"]].split(" (")[0],
                     r["outcome_class"].replace("_", "-"), text])
    mr.NUMBERS["unassessable"] = {f"{c}:{o}": n for (c, o), n in count.items()}
    return mr.tabular("llll", ["Case", "Corpus", "Outcome class", "Reason"], body)


# --------------------------------------------------------------------------- distinct values behind a sensitivity
def distinct_nulled(nulled: List[dict]) -> dict:
    """The literal sensitivities record one entry per occurrence: a described value appears once per edge and
    once per composition it enters. Map each entry back to the described port (same element or the message of a
    field element, same side, same value) and count distinct (task, port, field) values."""
    cache = {}

    def recon(t):
        if t not in cache:
            p = os.path.join(HERE, "s2_work", "tasks", t, "recon", f"{t}.json")
            cache[t] = json.load(open(p)) if os.path.exists(p) else {}
        return cache[t]

    def msg_of(el):
        return "msg:" + el[6:].rsplit(".", 1)[0] if el.startswith("field:") else el

    def get(port, field):
        v = port
        for k in field.split("."):
            v = (v or {}).get(k) if isinstance(v, dict) else None
        return v

    keys = {}
    for x in nulled:
        role = x["path"].split(".")[0]
        side = {"producer": "provides", "consumer": "consumes"}.get(role)
        field = ".".join(x["path"].split(".")[2:])
        ports = recon(x["task_id"]).get("ports") or []
        idx = next((i for i, pt in enumerate(ports) if pt.get("element") in (x["element"], msg_of(x["element"]))
                    and (side is None or pt.get("side") == side) and get(pt, field) == x["value"]), None)
        keys.setdefault((x["task_id"], idx if idx is not None else x["element"], field), x["reason"])
    return {"occurrences": len(nulled), "values": len(keys), "by_reason": dict(collections.Counter(keys.values())),
            "ports": len({(k[0], k[1]) for k in keys})}


# --------------------------------------------------------------------------- numbers the prose cites
def blinding(mr, rs) -> None:
    """The describer's answer to the blinding question ('is this revision defective?') against whether the
    snapshot was at the revision the documented fix changed, and, for each checker detection, whether a
    changed unit of its broken composition was answered 'yes'. Declared measure (PROTOCOL.md Section 6);
    this contrast was computed on 2026-09-30, after unsealing."""
    ledger = load("ledger/tasks.json")["tasks"]
    pilot = set(load("results_adjudicated.json")["pilot_excluded"])
    specs = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(os.path.join(HERE, "specs", "*.json"))}
    answer = {}
    for t in ledger:
        p = os.path.join(HERE, "s2_work", "tasks", t, "recon", f"{t}.json")
        if os.path.exists(p):
            answer[t] = (json.load(open(p)).get("blinding_guess") or {}).get("defective")

    def revision_class(t):
        e, kinds = ledger[t], set()
        for cid in e.get("cases", []):
            if cid in pilot or cid not in specs:
                continue
            for u in specs[cid].get("units", []):
                if u.get("name") != e["unit"]:
                    continue
                b, fixed = u.get("broken_rev"), u.get("resolved_rev")
                built = {v for k, v in (specs[cid].get("consumer_built_against") or {}).items() if k in ("broken", "resolved") and v}
                if e["revision"] == b and b != fixed:
                    kinds.add("defective")
                elif e["revision"] == fixed and b != fixed:
                    kinds.add("fixed")
                elif e["revision"] in (b, fixed):
                    kinds.add("unchanged")
                elif e["revision"] in built:
                    kinds.add("built_against")
        for k in ("defective", "fixed", "unchanged", "built_against"):
            if k in kinds and (k != "fixed" or kinds == {"fixed"}):
                return k
        return "fixed" if "fixed" in kinds else "unmatched"

    table: Dict[str, Dict[str, Dict[str, int]]] = {}
    for t, e in ledger.items():
        if e["status"] not in ("done", "excerpt") or t not in answer:
            continue
        if not [c for c in e.get("cases", []) if c not in pilot]:
            continue
        kind = "snapshot" if e["status"] == "done" else "excerpt"
        cell = table.setdefault(kind, {}).setdefault(revision_class(t), {"yes": 0, "no": 0, "cannot_tell": 0, "n": 0})
        cell[answer[t] if answer[t] in cell else "cannot_tell"] += 1
        cell["n"] += 1
    detections = {}
    for r in rs:
        if r["outcome_class"] != "failure" or r["broken"]["ECM"]["state"] != "right_reason":
            continue
        changed_yes = False
        for t, e in ledger.items():
            if r["case_id"] not in e.get("cases", []):
                continue
            for u in specs[r["case_id"]].get("units", []):
                if u.get("name") == e["unit"] and e["revision"] == u.get("broken_rev") != u.get("resolved_rev"):
                    changed_yes |= answer.get(t) == "yes"
        detections[r["case_id"]] = changed_yes
    mr.NUMBERS["blinding_by_revision"] = table
    mr.NUMBERS["blinding_detections"] = {"n": len(detections), "changed_unit_answered_yes": sorted(c for c, v in detections.items() if v),
                                         "none_answered_yes": sorted(c for c, v in detections.items() if not v)}


def enrichment(mr) -> None:
    """Eligible documented failures among specified issues, term-selected (C3) against unfiltered (C3N), with
    Wilson intervals (PROTOCOL.md Section 3, C3-neutral)."""
    out = {}
    for c in ("C3", "C3N"):
        f = mr.NUMBERS.get(f"funnel.{c}") or {}
        k = (f.get("outcome") or {}).get("failure")
        n = f.get("specified")
        if k is not None and n:
            out[c] = {"failures": k, "specified": n, "rate": k / n, "wilson95": S.wilson(k, n)}
    mr.NUMBERS["enrichment"] = out


def c2_generation(mr, rs) -> None:
    fails = [r for r in of(rs, "C2") if r["outcome_class"] == "failure"]
    mr.NUMBERS["c2_generation"] = dict(collections.Counter(r["ros_generation"] for r in fails))


def s1_intermodel(mr) -> None:
    d = load("reliability/s1_intermodel.json") or {}
    mr.NUMBERS["s1_intermodel"] = {"sample": d.get("sample"), "per_dimension": d.get("per_dimension")}


def submodules(mr) -> None:
    """Task snapshots whose .gitmodules names a path that `git archive` left empty (the export does not include
    submodule contents), with the cases they serve."""
    ledger = load("ledger/tasks.json")["tasks"]
    out = []
    for t, e in sorted(ledger.items()):
        snap = os.path.join(HERE, "s2_work", "tasks", t, "snapshot")
        gm = os.path.join(snap, ".gitmodules")
        if not os.path.exists(gm):
            continue
        paths = [ln.split("=", 1)[1].strip() for ln in open(gm, errors="replace") if ln.strip().startswith("path")]
        empty = [p for p in paths if not os.path.isdir(os.path.join(snap, p)) or not os.listdir(os.path.join(snap, p))]
        if empty:
            out.append({"task": t, "cases": e.get("cases", []), "submodules": len(paths), "empty": len(empty),
                        "status": e["status"]})
    mr.NUMBERS["submodules"] = out


def build(mr, res) -> Dict[str, str]:
    rs = rows()
    files = {"strata.tex": strata(mr, rs), "strata_all_methods.tex": strata_all_methods(mr, rs),
             "detection_stage.tex": detection_stage(mr, rs), "hit_matrix.tex": hit_matrix(mr, rs),
             "complete_case.tex": complete_case(mr, res), "sensitivity_detail.tex": sensitivity_detail(mr, res),
             "unassessable.tex": unassessable(mr, rs)}
    blinding(mr, rs)
    resolution_shift(mr)
    unit_fields(mr)
    nt_pair_views(mr)
    alert_ratios(mr, rs)
    enrichment(mr)
    c2_generation(mr, rs)
    s1_intermodel(mr)
    submodules(mr)
    return files
