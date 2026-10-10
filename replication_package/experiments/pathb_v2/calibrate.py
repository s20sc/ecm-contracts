"""Adjudicator calibration with planted errors (steward; DEVIATIONS.md 2026-09-27).

The A1 design shows the adjudicator a specification and asks it to agree or disagree. An
adjudicator that agrees with everything looks perfect in kappa terms and adjudicates nothing.
This script measures, before an adjudicator's corpus records are counted, whether it catches
errors planted in copies of real specifications.

  python3 calibrate.py build            -> calibration/specs/CAL-XX.json, calibration/packets/CAL_00.json,
                                           calibration/key.json (outside every workspace)
  python3 calibrate.py prompt <who>     -> workspace calibration_work/CAL_00.<who>, prompt path
  python3 calibrate.py collect <who>    -> calibration/records/<who>/*.json
  python3 calibrate.py score            -> calibration/sensitivity.json

Planted: one error per perturbed copy (failed-condition class x2, loudness x2, resolution x2,
eligibility x1, implicated elements x1); 4 copies are unchanged. Detection = `disagree` on the
planted field. Disagreement on an unchanged copy is reported, not called an error, because the
real specification may itself be wrong.
"""
import copy
import glob
import json
import os
import random
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Set v1 (calibration/): single-field plants; several are visible as a contradiction inside the copy
# itself (the plant disagrees with the specification's own quote or evidence sentence).
# Set v2 (calibration/v2/, `--set v2` on every command): plants kept consistent with the rest of the
# copy (neighbouring class; loudness and resolution rewritten together with their evidence sentence
# and detection stage), so that only the sources reveal them, as with a real specification error.
SET = sys.argv[sys.argv.index("--set") + 1] if "--set" in sys.argv else "v1"
CAL = os.path.join(HERE, "calibration") if SET == "v1" else os.path.join(HERE, "calibration", SET)
WORK = os.path.join(HERE, "calibration_work")
PKT = "CAL_00" if SET == "v1" else f"CAL_{SET}"
SEED = "20260925:calibration" if SET == "v1" else f"20260925:calibration:{SET}"
PLAN = (["class", "class", "loudness", "loudness", "resolution", "resolution", "eligibility", "elements"] if SET == "v1"
        else ["near_class", "near_class", "loudness_consistent", "loudness_consistent",
              "resolution_consistent", "resolution_consistent", "eligibility", "eligibility"])
NEAR = {"element_retyped": "element_removed_or_renamed", "element_removed_or_renamed": "element_retyped",
        "qos_reliability": "qos_durability", "qos_durability": "qos_reliability",
        "representation_convention": "frame_mismatch", "frame_mismatch": "representation_convention",
        "definition_mismatch": "nominal_type_mismatch", "nominal_type_mismatch": "definition_mismatch",
        "other": "representation_convention", "exclusive_resource_conflict": "rate_shortfall",
        "rate_shortfall": "exclusive_resource_conflict"}
LOUD_TEXT = {"loud_documented": ("connect", "The mismatch is reported when the two units connect: the consumer logs an "
                                 "incompatibility error naming the element before any data is exchanged."),
             "silent_documented": ("run", "No existing tooling reports the mismatch at build, connection, or activation; "
                                   "the reporter observed only wrong behaviour at run time.")}
RES_TEXT = {"none": "No change resolving the failure was merged or tested; the thread ends without a fix.",
            "observed": "The reporter confirms that the composition works after the fix, with both units at the stated revisions."}
N_CONTROL = 4
# a class far from the true one, so that a reader of the source cannot mistake the plant for a borderline call
FAR = {"other": "qos_reliability", "qos_reliability": "frame_mismatch", "qos_durability": "frame_mismatch",
       "representation_convention": "exclusive_resource_conflict", "element_retyped": "qos_durability",
       "element_removed_or_renamed": "rate_shortfall", "frame_mismatch": "qos_reliability",
       "definition_mismatch": "exclusive_resource_conflict", "nominal_type_mismatch": "qos_durability",
       "exclusive_resource_conflict": "frame_mismatch", "rate_shortfall": "element_removed_or_renamed"}
LOUD_FLIP = {"silent_documented": "loud_documented", "loud_documented": "silent_documented"}
RES_FLIP = {"observed": "none", "recommended": "none", "none": "observed"}


def pool():
    """Eligible failures that are corpus A1 items (not pilot), in a fixed order."""
    import adjudicate as J
    pilot = J.pilot_cases()
    out = []
    for f in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        s = json.load(open(f))
        if s["case_id"] in pilot or not s.get("eligible") or s.get("outcome_class") != "failure":
            continue
        if s.get("failed_conditions") and s.get("loudness") in LOUD_FLIP and (s.get("resolution") or {}).get("status") in RES_FLIP:
            out.append(s)
    return out


def plant(s, kind):
    """Return (perturbed spec, key entry) or None when this spec cannot carry this kind of error."""
    p = copy.deepcopy(s)
    if kind == "near_class":
        c0 = p["failed_conditions"][0]
        if c0.get("class") not in NEAR:
            return None
        c0["class"] = NEAR[c0["class"]]
        return p, {"field": "failed_conditions[0].class", "original": s["failed_conditions"][0]["class"], "planted": c0["class"]}
    if kind == "loudness_consistent":
        new = LOUD_FLIP[s["loudness"]]
        p["loudness"], (p["detection_stage"], p["loudness_evidence"]) = new, LOUD_TEXT[new]
        return p, {"field": "loudness", "original": s["loudness"], "planted": new}
    if kind == "resolution_consistent":
        new = "none" if s["resolution"]["status"] in ("observed", "recommended") else "observed"
        p["resolution"]["status"], p["resolution"]["evidence"] = new, RES_TEXT[new]
        if new == "none":
            p["resolution"]["summary"] = "No resolving change is documented."
        return p, {"field": "resolution.status", "original": s["resolution"]["status"], "planted": new}
    if kind == "class":
        c0 = p["failed_conditions"][0]
        if c0.get("class") not in FAR:
            return None
        c0["class"] = FAR[c0["class"]]
        return p, {"field": "failed_conditions[0].class", "original": s["failed_conditions"][0]["class"], "planted": c0["class"]}
    if kind == "loudness":
        p["loudness"] = LOUD_FLIP[s["loudness"]]
        return p, {"field": "loudness", "original": s["loudness"], "planted": p["loudness"]}
    if kind == "resolution":
        p["resolution"]["status"] = RES_FLIP[s["resolution"]["status"]]
        return p, {"field": "resolution.status", "original": s["resolution"]["status"], "planted": p["resolution"]["status"]}
    if kind == "elements":
        implicated = set(p["failed_conditions"][0].get("implicated_elements") or [])
        spare = [e["element"] for e in (p.get("inventory") or []) if e.get("element") not in implicated]
        if not implicated or not spare:
            return None
        p["failed_conditions"][0]["implicated_elements"] = [spare[0]]
        return p, {"field": "failed_conditions[0].implicated_elements", "original": sorted(implicated), "planted": [spare[0]]}
    if kind == "eligibility":
        for k in ("units", "operation", "consumer_built_against", "inventory", "failed_conditions", "outcome_class", "loudness",
                  "loudness_evidence", "detection_stage", "resolution", "ros_generation", "excerpt_based"):
            p[k] = None
        p["eligible"] = False
        p["ineligible_reason"] = "internal: the failure is a defect inside one unit; the value crossing the interface is valid"
        p["eligibility"]["E2"] = {"pass": False, "stop_step": 2, "reason_code": "internal",
                                  "reason": "The documented failure is a defect inside one unit; no interaction between two units failed."}
        for k in ("E3", "E4"):
            p["eligibility"].pop(k, None)
        p["notes"] = ""
        return p, {"field": "eligibility", "original": True, "planted": False}
    raise ValueError(kind)


def build():
    rng = random.Random(SEED)
    cands = pool()
    if SET != "v1":  # a later set never reuses a case an earlier set planted in or kept as a control
        v1 = {k["source_case"] for k in json.load(open(os.path.join(HERE, "calibration", "key.json"))).values()}
        cands = [s for s in cands if s["case_id"] not in v1]
    rng.shuffle(cands)
    used, made = set(), []
    for kind in PLAN:
        for s in cands:
            if s["case_id"] in used:
                continue
            r = plant(s, kind)
            if r is None:
                continue
            used.add(s["case_id"])
            made.append((r[0], dict(r[1], kind=kind, source_case=s["case_id"])))
            break
        else:
            raise SystemExit(f"no specification can carry a planted {kind} error")
    for s in cands:
        if len([m for m in made if m[1]["kind"] == "control"]) == N_CONTROL:
            break
        if s["case_id"] not in used:
            used.add(s["case_id"])
            made.append((copy.deepcopy(s), {"kind": "control", "source_case": s["case_id"]}))
    rng.shuffle(made)
    shutil.rmtree(os.path.join(CAL, "specs"), ignore_errors=True)
    shutil.rmtree(os.path.join(CAL, "artifacts"), ignore_errors=True)
    os.makedirs(os.path.join(CAL, "specs")); os.makedirs(os.path.join(CAL, "artifacts")); os.makedirs(os.path.join(CAL, "packets"), exist_ok=True)
    key, items = {}, []
    for i, (spec, k) in enumerate(made, 1):
        cid = f"CAL-{i:02d}" if SET == "v1" else f"CAL{SET[1:]}-{i:02d}"
        spec = dict(spec, case_id=cid)
        json.dump(spec, open(os.path.join(CAL, "specs", f"{cid}.json"), "w"), indent=1)
        art = os.path.join(HERE, "artifacts", f"{k['source_case']}.txt")
        if os.path.exists(art):
            shutil.copy(art, os.path.join(CAL, "artifacts", f"{cid}.txt"))
        key[cid] = k
        items.append({"item_id": f"A1-{cid}", "kind": "A1", "case_id": cid, "spec": f"specs/{cid}.json"})
    json.dump(items, open(os.path.join(CAL, "packets", f"{PKT}.json"), "w"), indent=1)
    json.dump(key, open(os.path.join(CAL, "key.json"), "w"), indent=1)
    print(len(items), "calibration items;", sum(k["kind"] != "control" for k in key.values()), "planted")


def workdir(who):
    wd = os.path.join(WORK, f"{PKT}.{who}")
    shutil.rmtree(wd, ignore_errors=True)
    for d in ("specs", "artifacts", "prompts", os.path.join("adjudication", "packets"), os.path.join("adjudication", who)):
        os.makedirs(os.path.join(wd, d))
    shutil.copy(os.path.join(HERE, "prompts", "S1_specify.md"), os.path.join(wd, "prompts", "S1_specify.md"))
    shutil.copy(os.path.join(CAL, "packets", f"{PKT}.json"), os.path.join(wd, "adjudication", "packets", f"{PKT}.json"))
    shutil.copy(os.path.join(HERE, "definition_hash.py"), os.path.join(wd, "definition_hash.py"))
    for f in glob.glob(os.path.join(CAL, "specs", "*.json")):
        shutil.copy(f, os.path.join(wd, "specs"))
    for f in glob.glob(os.path.join(CAL, "artifacts", "*.txt")):
        shutil.copy(f, os.path.join(wd, "artifacts"))
    return os.path.realpath(wd)


def prompt(who):
    wd = workdir(who)
    text = open(os.path.join(HERE, "prompts", "A_adjudicate.md")).read()
    text = text.replace("{PB2}", wd).replace("{INPUT}", os.path.join(wd, "adjudication", "packets", f"{PKT}.json")).replace("{WHO}", who)
    os.makedirs(os.path.join(CAL, "prompts"), exist_ok=True)
    out = os.path.join(CAL, "prompts", f"{PKT}.{who}.md")
    open(out, "w").write(text)
    print(out)


def collect(who):
    src = os.path.join(WORK, f"{PKT}.{who}", "adjudication", who)
    dst = os.path.join(CAL, "records", who)
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in sorted(glob.glob(os.path.join(src, "*.json"))):
        json.load(open(f))
        shutil.copy(f, os.path.join(dst, os.path.basename(f)))
        n += 1
    print(n, "records collected for", who)


def detected(rec, k):
    f = k["field"]
    if f == "eligibility":
        return (rec.get("eligibility") or {}).get("verdict") == "disagree"
    if f == "loudness":
        return (rec.get("loudness") or {}).get("verdict") == "disagree"
    if f == "resolution.status":
        return (rec.get("resolution") or {}).get("verdict") == "disagree"
    c0 = next((x for x in rec.get("failed_conditions") or [] if x.get("index") == 0), {})
    if f == "failed_conditions[0].class":
        return c0.get("class_verdict") == "disagree"
    if f == "failed_conditions[0].implicated_elements":
        return c0.get("elements_verdict") == "disagree"
    raise ValueError(f)


def any_disagree(rec):
    parts = [rec.get("eligibility"), rec.get("loudness"), rec.get("resolution")]
    verdicts = [(p or {}).get("verdict") for p in parts]
    verdicts += [x.get(v) for x in rec.get("failed_conditions") or [] for v in ("class_verdict", "elements_verdict")]
    return "disagree" in verdicts or bool(rec.get("missed_conditions"))


def score():
    key = json.load(open(os.path.join(CAL, "key.json")))
    out = {}
    for d in sorted(glob.glob(os.path.join(CAL, "records", "*"))):
        who = os.path.basename(d)
        if not os.path.isdir(d):
            continue
        recs = {json.load(open(f))["case_id"]: json.load(open(f)) for f in glob.glob(os.path.join(d, "*.json"))}
        planted = {c: k for c, k in key.items() if k["kind"] != "control"}
        controls = [c for c, k in key.items() if k["kind"] == "control"]
        per = {c: {"kind": k["kind"], "detected": detected(recs[c], k) if c in recs else None} for c, k in planted.items()}
        out[who] = {"records": len(recs), "planted": len(planted),
                    "detected": sum(1 for v in per.values() if v["detected"]),
                    "missing": sorted(c for c in key if c not in recs),
                    "control_items_with_any_disagreement": sum(1 for c in controls if c in recs and any_disagree(recs[c])),
                    "controls": len(controls), "per_item": per}
    json.dump(out, open(os.path.join(CAL, "sensitivity.json"), "w"), indent=1)
    for who, v in out.items():
        print(f"{who}: {v['detected']}/{v['planted']} planted errors detected; "
              f"{v['control_items_with_any_disagreement']}/{v['controls']} unchanged copies disagreed; missing {v['missing']}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "prompt":
        prompt(sys.argv[2])
    elif cmd == "collect":
        collect(sys.argv[2])
    elif cmd == "score":
        score()
    else:
        raise SystemExit(__doc__)
