"""Tests for the Path B v2.1 pipeline. Run: PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider test_scoring.py

Covers: exact statistics oracles; every baseline rule and its ECM counterpart in both
directions; rule-instance matching on tokens and edges; exact-path provenance; the
semver wrapper; SWITCH and `other`; assembler edges, UPGRADE deltas and pair views;
control false alarms; strata; strict JSON; packet building on the real C1/C2 pools.
"""
import copy
import json
import os

import assemble as A
import baselines_v2 as B
import build_packets as K
import scoring as S

PO, PI = "producer.outputs[0]", "consumer.inputs[0]"


def port(msg="geometry_msgs/Pose", frame="map", units="m", rel="reliable", dur="volatile", dl=None,
         rate=None, minr=None, did=None, role="e"):
    return {"role": role, "msg_type": msg, "frame": frame, "units": units,
            "qos": {"reliability": rel, "durability": dur, "deadline_ms": dl},
            "rate_hz": rate, "min_rate_hz": minr,
            "definition_id": ({"algorithm": "ros1_md5", "kind": "msg", "value": did} if did else None)}


def edge(out, inp, ctype="PAIR", pex=None, cex=None, grants_state="unknown"):
    return {"type": ctype,
            "producer": {"outputs": [out], "inputs": [], "exclusive": pex or [], "perm_requires": [], "perm_grants": [],
                         "perm_limits": {}, "recovery": None, "_states": {"perm_grants": grants_state}},
            "consumer": {"outputs": [], "inputs": [inp], "exclusive": cex or [], "perm_requires": [], "perm_grants": [],
                         "perm_limits": {}, "recovery": None, "_states": {"perm_grants": grants_state}},
            "edge": {"out_role": "e", "in_role": "e"}}


def prov_for(*paths):
    return {p: f"snapshot:x.py:1 | {p}" for p in paths}


def unit(enc, prov, kind="edge", element="e"):
    return {"kind": kind, "element": element, "status": "done", "encoding": enc, "provenance": prov}


def comp(*units):
    return {"status": "done", "reason": None, "units": list(units)}


def cond(cls, *els):
    return {"class": cls, "implicated_elements": list(els), "quote": "q", "url": "u"}


# ----------------------------------------------------------------------------- statistics
def test_wilson_and_mcnemar_oracles():
    lo, hi = S.wilson(20, 40)
    assert abs(lo - 0.35199) < 1e-4 and abs(hi - 0.64801) < 1e-4
    assert S.wilson(0, 40)[1] - 0.08762 < 1e-4 and S.wilson(0, 40)[0] == 0.0
    assert S.wilson(0, 0) is None
    assert S.mcnemar_exact(5, 0) == 0.0625 and S.mcnemar_exact(6, 0) == 0.03125
    assert S.mcnemar_exact(0, 0) == 1.0 and abs(S.mcnemar_exact(5, 1) - 0.21875) < 1e-12


def test_rate_with_zero_n_is_null_not_zero():
    r = S.rate(0, 0)
    assert r["rate"] is None and r["wilson95"] is None and r["reason"] == "no_observations"


# ----------------------------------------------------------------------------- baselines vs checker
def test_nt_is_nested_in_ecm_including_promotion():
    e = edge(port(msg="geometry_msgs/Pose2D"), port(msg="geometry_msgs/Pose"))
    assert B.nominal_type(e) == [] and S.ecm_findings(e)[0] == []
    e2 = edge(port(msg="a/A"), port(msg="b/B"))
    assert [f["rule"] for f in B.nominal_type(e2)] == ["nt_type_mismatch"]
    assert "type_mismatch" in [f["rule"] for f in S.ecm_findings(e2)[0]]


def test_di_not_nested_in_ecm_and_wildcard():
    e = edge(port(did="aa"), port(did="bb"))
    assert [f["rule"] for f in B.definition_identity(e)] == ["di_definition_mismatch"]
    assert S.ecm_findings(e)[0] == []
    assert B.definition_identity(edge(port(did="*"), port(did="bb"))) == []
    mixed = edge(port(did="aa"), port(did="bb"))
    mixed["consumer"]["inputs"][0]["definition_id"]["algorithm"] = "sha256_normalised"
    assert B.definition_identity(mixed) == []  # not comparable


def test_dq_rules_in_both_directions():
    bad = edge(port(rel="best_effort", dur="volatile", dl=200), port(rel="reliable", dur="transient_local", dl=100))
    rules = sorted(f["rule"] for f in B.definition_and_qos(bad))
    assert rules == ["dq_qos_deadline", "dq_qos_durability", "dq_qos_reliability"]
    ok = edge(port(rel="reliable", dur="transient_local", dl=100), port(rel="best_effort", dur="volatile", dl=200))
    assert B.definition_and_qos(ok) == []
    # ECM deadline uses publication rate, DQ uses the offered deadline: they can disagree
    e = edge(port(dl=200, rate=20), port(dl=100))
    assert [f["rule"] for f in B.definition_and_qos(e)] == ["dq_qos_deadline"]
    assert "qos_deadline" not in [f["rule"] for f in S.ecm_findings(e)[0]]


def test_semver_wrapper_never_invents_a_bump():
    for so, sn in ((None, "2.0.0"), ("1.0.0", None), (None, None)):
        enc = {"type": "UPGRADE", "ver_delta": {"changed_fields": [], "consumer_reads": [], "semver_old": so, "semver_new": sn}}
        fs, unev = S.ecm_findings(enc)
        assert fs == [] and unev == ["semver_major"]
        assert B.declared_semver(enc) == []
    enc = {"type": "UPGRADE", "ver_delta": {"changed_fields": [], "consumer_reads": [], "semver_old": "1.4.0", "semver_new": "2.0.0"}}
    assert [f["rule"] for f in S.ecm_findings(enc)[0]] == ["semver_major"]
    assert [f["rule"] for f in B.declared_semver(enc)] == ["sv_major"]


# ----------------------------------------------------------------------------- matching and provenance
def test_frame_tp_requires_exact_path_provenance_on_both_ports():
    e = edge(port(frame="enu"), port(frame="ned"))
    good = prov_for(f"{PO}.frame", f"{PI}.frame")
    r = S.score_composition(comp(unit(e, good)), [cond("frame_mismatch", "e")], "PAIR", {})
    assert r["ECM"]["state"] == "right_reason" and r["DQ"]["state"] == "accept"
    only_one = prov_for(f"{PO}.frame")
    assert S.score_composition(comp(unit(e, only_one)), [cond("frame_mismatch", "e")], "PAIR", {})["ECM"]["state"] == "unverified"
    port_level = {PO: "x", PI: "y"}
    assert S.score_composition(comp(unit(e, port_level)), [cond("frame_mismatch", "e")], "PAIR", {})["ECM"]["state"] == "unverified"


def test_wrong_reason_when_class_does_not_match():
    e = edge(port(frame="enu"), port(frame="ned"))
    r = S.score_composition(comp(unit(e, prov_for(f"{PO}.frame", f"{PI}.frame"))), [cond("qos_reliability", "e")], "PAIR", {})
    assert r["ECM"]["state"] == "wrong_reason" and r["ECM"]["reject"]


def test_adjudicated_wrong_provenance_demotes_to_unverified():
    e = edge(port(frame="enu"), port(frame="ned"))
    p = prov_for(f"{PO}.frame", f"{PI}.frame")
    r = S.score_composition(comp(unit(e, p)), [cond("frame_mismatch", "e")], "PAIR", {f"{PI}.frame": "wrong"})
    assert r["ECM"]["state"] == "unverified"


def test_field_break_token_must_be_implicated_and_grounded():
    enc = {"type": "UPGRADE", "ver_delta": {"changed_fields": ["topic:gps/fix", "param:foo"],
                                            "consumer_reads": ["topic:gps/fix", "param:foo"], "semver_old": None, "semver_new": None}}
    p = prov_for("ver_delta.changed_fields[topic:gps/fix]", "ver_delta.consumer_reads[topic:gps/fix]",
                 "ver_delta.changed_fields[param:foo]", "ver_delta.consumer_reads[param:foo]")
    u = unit(enc, p, kind="upgrade", element=None)
    r = S.score_composition(comp(u), [cond("element_removed_or_renamed", "topic:/gps/fix")], "UPGRADE", {})
    assert r["ECM"]["state"] == "right_reason" and r["ECM"]["matched"][0]["token"] == "topic:gps/fix"
    r2 = S.score_composition(comp(u), [cond("element_removed_or_renamed", "topic:other")], "UPGRADE", {})
    assert r2["ECM"]["state"] == "wrong_reason"
    p3 = prov_for("ver_delta.changed_fields[topic:gps/fix]")  # consumer side ungrounded
    r3 = S.score_composition(comp(unit(enc, p3, kind="upgrade", element=None)), [cond("element_removed_or_renamed", "topic:gps/fix")], "UPGRADE", {})
    assert r3["ECM"]["state"] == "unverified"


def test_definition_mismatch_field_matches_msg_parent():
    assert S.token_matches("field:pkg/T.x", ["msg:pkg/T"], "definition_mismatch")
    assert not S.token_matches("field:pkg/T.x", ["msg:pkg/T"], "element_retyped")
    assert S.token_matches("joint1/position", ["resource:joint1/position"], "exclusive_resource_conflict")


def test_match_table_has_no_declared_signal_rules():
    for cls, rules in S.MATCH.items():
        assert all(rule not in ("semver_major", "sv_major") for _, rule, _ in rules), cls
    assert S.MATCH["other"] == [] and S.MATCH["recovery_conflict"] == [] and S.MATCH["representation_convention"] == []


def test_semver_major_alone_is_never_right_reason():
    enc = {"type": "UPGRADE", "ver_delta": {"changed_fields": [], "consumer_reads": [], "semver_old": "1.0.0", "semver_new": "2.0.0"}}
    u = unit(enc, prov_for("ver_delta.semver_old", "ver_delta.semver_new"), kind="upgrade", element=None)
    for cls in ("definition_mismatch", "element_removed_or_renamed", "element_retyped"):
        r = S.score_composition(comp(u), [cond(cls, "msg:pkg/T")], "UPGRADE", {})
        assert r["ECM"]["state"] == "wrong_reason" and r["SV"]["state"] == "wrong_reason"


def test_lock_conflict_token_and_permission_closed_world():
    e = edge(port(), port(), ctype="CONCURRENT", pex=["joint1/position"], cex=["joint1/position"])
    p = prov_for("producer.exclusive[joint1/position]", "consumer.exclusive[joint1/position]")
    r = S.score_composition(comp(unit(e, p)), [cond("exclusive_resource_conflict", "resource:joint1/position")], "CONCURRENT", {})
    assert r["ECM"]["state"] == "right_reason"
    e2 = edge(port(), port(), grants_state="unknown")
    e2["consumer"]["perm_requires"] = ["camera"]
    p2 = prov_for("consumer.perm_requires[camera]")
    assert S.score_composition(comp(unit(e2, p2)), [cond("permission_missing", "camera")], "PAIR", {})["ECM"]["state"] == "unverified"
    e3 = copy.deepcopy(e2)
    e3["producer"]["_states"]["perm_grants"] = e3["consumer"]["_states"]["perm_grants"] = "absent"
    assert S.score_composition(comp(unit(e3, p2)), [cond("permission_missing", "camera")], "PAIR", {})["ECM"]["state"] == "right_reason"


def test_switch_and_other_are_not_supported_but_raw_kept():
    e = edge(port(frame="enu"), port(frame="ned"))
    r = S.score_composition(comp(unit(e, prov_for(f"{PO}.frame", f"{PI}.frame"))), [cond("frame_mismatch", "e")], "SWITCH", {})
    assert r["ECM"]["state"] == "not_supported" and r["ECM"]["reject"] and r["ECM"]["findings"]
    r2 = S.score_composition(comp(unit(e, {})), [cond("other", "e")], "PAIR", {})
    assert r2["ECM"]["state"] == "wrong_reason"
    ok = edge(port(), port())
    assert S.score_composition(comp(unit(ok, {})), [cond("other", "e")], "PAIR", {})["ECM"]["state"] == "not_supported"


def test_unassessable_composition_and_edge():
    r = S.score_composition({"status": "unassessable", "reason": "recon_missing", "units": []}, [cond("frame_mismatch", "e")], "PAIR", {})
    assert all(v["state"] == "unassessable" for v in r.values())
    bad = {"kind": "edge", "element": "e", "status": "unassessable_edge", "reason": "port_missing_consumer", "encoding": None, "provenance": {}}
    good = unit(edge(port(frame="enu"), port(frame="ned")), prov_for(f"{PO}.frame", f"{PI}.frame"))
    r2 = S.score_composition(comp(bad, good), [cond("frame_mismatch", "e")], "PAIR", {})
    assert r2["ECM"]["state"] == "right_reason"


# ----------------------------------------------------------------------------- assembler
def desc(unit_name, ports, declares=None, references=None, exclusive=None, version=None):
    prov = {}
    for i, p in enumerate(ports):
        for k in ("msg_type", "frame", "units", "definition_id"):
            if p.get(k) is not None:
                prov[f"ports[{i}].{k}"] = f"snapshot:{unit_name}:{i}:{k}"
        for k in ("reliability", "durability", "deadline_ms"):
            if (p.get("qos") or {}).get(k) is not None:
                prov[f"ports[{i}].qos.{k}"] = f"snapshot:{unit_name}:{i}:{k}"
    for el in (declares or {}):
        prov[f"declares[{el}]"] = f"snapshot:{unit_name}:decl:{el}"
    for el in (references or []):
        prov[f"references[{el}]"] = f"snapshot:{unit_name}:ref:{el}"
    for tok in (exclusive or []):
        prov[f"exclusive[{tok}]"] = f"snapshot:{unit_name}:ex:{tok}"
    if version:
        prov["manifest_version"] = f"snapshot:{unit_name}:package.xml"
    return {"task_id": unit_name, "ports": ports, "declares": declares or {}, "references": references or [],
            "exclusive": exclusive or [], "manifest_version": version, "provenance": prov,
            "perm_requires": {"state": "absent"}, "perm_grants": {"state": "absent"}, "recovery": {"state": "absent"}}


def sport(element, side, **kw):
    p = port(role=element, **kw)
    p.update({"element": element, "side": side})
    return p


def test_assembler_pairs_by_element_and_carries_token_provenance():
    spec = {"case_id": "c", "corpus": "C1", "operation": "PAIR",
            "units": [{"name": "P", "role": "provider", "broken_rev": "a"}, {"name": "C", "role": "consumer", "broken_rev": "b"}],
            "inventory": [{"element": "topic:/att", "sides": {"P": "provides", "C": "consumes"}},
                          {"element": "topic:/other", "sides": {"P": "provides", "C": "consumes"}}],
            "resolution": {"status": "none"}}
    P = desc("P", [sport("topic:/att", "provides", frame="enu"), sport("topic:/other", "provides")])
    C = desc("C", [sport("topic:/att", "consumes", frame="ned")])
    units = A.edge_units(spec, P, C, "PAIR")
    assert [u["status"] for u in units] == ["done", "unassessable_edge"]
    e = units[0]
    assert e["encoding"]["edge"] == {"out_role": "topic:/att", "in_role": "topic:/att"}
    assert e["provenance"][f"{PO}.frame"].startswith("snapshot:P") and e["provenance"][f"{PI}.frame"].startswith("snapshot:C")
    r = S.score_composition(comp(*units), [cond("frame_mismatch", "topic:/att")], "PAIR", {})
    assert r["ECM"]["state"] == "right_reason"


def test_assembler_upgrade_delta_and_pair_view():
    spec = {"case_id": "c", "corpus": "C1", "operation": "UPGRADE",
            "units": [{"name": "P", "role": "provider"}, {"name": "C", "role": "consumer"}],
            "inventory": [{"element": "topic:gps/fix", "sides": {"P": "provides", "C": "consumes"}}]}
    built = desc("Pold", [sport("topic:gps/fix", "provides", msg="sensor_msgs/NavSatFix", did="aaa")],
                 declares={"topic:gps/fix": "topic gps/fix: sensor_msgs/NavSatFix"}, version="0.11.0")
    built["not_declared"] = ["topic:global_position/raw/fix"]
    built["provenance"]["not_declared[topic:global_position/raw/fix]"] = "snapshot:Pold:grep | no such advertise"
    running = desc("Pnew", [sport("topic:gps/fix", "provides", msg="sensor_msgs/NavSatFix", did="bbb")],
                   declares={"topic:global_position/raw/fix": "topic global_position/raw/fix: sensor_msgs/NavSatFix"}, version="0.12.0")
    running["not_declared"] = ["topic:gps/fix"]
    running["provenance"]["not_declared[topic:gps/fix]"] = "snapshot:Pnew:grep | gps plugin removed"
    cons = desc("C", [sport("topic:gps/fix", "consumes", msg="sensor_msgs/NavSatFix")], references=["topic:gps/fix"])
    units = A.upgrade_units(spec, built, running, cons)
    up = units[0]
    assert up["kind"] == "upgrade"
    assert up["encoding"]["ver_delta"]["changed_fields"] == ["topic:global_position/raw/fix", "topic:gps/fix"]
    assert up["encoding"]["ver_delta"]["consumer_reads"] == ["topic:gps/fix"]
    assert "ver_delta.changed_fields[topic:gps/fix]" in up["provenance"] and "ver_delta.consumer_reads[topic:gps/fix]" in up["provenance"]
    r = S.score_composition(comp(*units), [cond("element_removed_or_renamed", "topic:gps/fix")], "UPGRADE", {})
    assert r["ECM"]["state"] == "right_reason"
    pv = units[1]
    assert pv["kind"] == "pair_view" and pv["encoding"]["consumer"]["inputs"][0]["definition_id"]["value"] == "aaa"
    r2 = S.score_composition(comp(*units), [cond("definition_mismatch", "msg:sensor_msgs/NavSatFix")], "UPGRADE", {})
    assert r2["DI"]["state"] == "right_reason"  # the implicated definition is the type carried on that edge
    r2b = S.score_composition(comp(*units), [cond("definition_mismatch", "msg:other/Type")], "UPGRADE", {})
    assert r2b["DI"]["state"] == "wrong_reason"
    r3 = S.score_composition(comp(*units), [cond("definition_mismatch", "topic:gps/fix")], "UPGRADE", {})
    assert r3["DI"]["state"] == "right_reason" and r3["DQ"]["state"] == "right_reason"


def test_assembler_missing_recon_is_unassessable():
    ledger = {"tasks": {}, "by_key": {}}
    spec = {"case_id": "c", "corpus": "C1", "operation": "PAIR",
            "units": [{"name": "P", "role": "provider", "broken_rev": "a"}, {"name": "C", "role": "consumer", "broken_rev": "b"}],
            "inventory": [], "resolution": {"status": "none"}}
    a = A.assemble_case(spec, ledger)
    assert a["status"] == "unassessable" and a["reason"].startswith("producer:")


# ----------------------------------------------------------------------------- aggregation
def row(cid, corpus, broken, resolved=None, outcome="failure", loud="silent_documented", classes=("frame_mismatch",),
        res_status="none", assembled="done", **kw):
    r = {"case_id": cid, "corpus": corpus, "operation": "PAIR", "outcome_class": outcome, "loudness": loud,
         "detection_stage": None, "classes": list(classes), "resolution_status": res_status, "ros_generation": "ROS2",
         "excerpt_based": False, "unpinned": False, "single_composition": resolved is None, "adjudication_changed": False,
         "assembled_status": assembled, "assembled_reason": None, "broken": broken, "resolved": resolved}
    r.update(kw)
    return r


def states(**per_method):
    base = {m: {"state": "accept", "reject": False, "findings": [], "matched": [], "unevaluable": []} for m in S.METHODS}
    for m, s in per_method.items():
        base[m] = {"state": s, "reject": s != "accept", "findings": [], "matched": [], "unevaluable": []}
    return base


def test_aggregate_primary_counts_unassessable_as_not_detected():
    rows = [row("a", "C3", states(ECM="right_reason")),
            row("b", "C3", states(ECM="unassessable", NT="unassessable", DI="unassessable", DQ="unassessable", SV="unassessable"), assembled="unassessable")]
    p = S.aggregate(rows)
    assert p["n_failures"] == 2 and p["methods"]["ECM"]["right_reason"]["k"] == 1 and p["n_unassessable_failures"] == 1
    c = S.aggregate(rows, complete_case=True)
    assert c["n_failures"] == 1


def test_unassessable_control_is_a_false_alarm_in_primary_but_dropped_in_complete_case():
    """PROTOCOL.md Section 15 'Bounds': an unassessable control counts as not accepted (a false alarm for every
    method) in the primary numbers; the complete-case numbers drop it. The scorer counted it as not rejected
    until 2026-09-29 (DEVIATIONS.md)."""
    ok = {m: {"state": "accept", "findings": []} for m in S.METHODS}
    una = {m: {"state": "unassessable", "findings": []} for m in S.METHODS}
    rows = [row("f", "C1", states(ECM="right_reason")),
            row("c1", "C1", states(), resolved=ok, res_status="observed"),
            row("c2", "C1", states(), resolved=una, res_status="observed"),
            row("c3", "C1", states(), resolved=una, res_status="recommended"),
            row("w1", "C1", states(ECM="unassessable", NT="unassessable", DI="unassessable", DQ="unassessable", SV="unassessable"),
                outcome="warning_only", assembled="unassessable")]
    p = S.aggregate(rows)
    for m in S.METHODS:
        assert p["methods"][m]["false_alarm_fixed_observed"]["k"] == 1 and p["methods"][m]["false_alarm_fixed_observed"]["n"] == 2
        assert p["methods"][m]["false_alarm_fixed_recommended"]["k"] == 1 and p["methods"][m]["false_alarm_fixed_recommended"]["n"] == 1
        assert p["methods"][m]["false_alarm_warning_only"]["k"] == 1 and p["methods"][m]["false_alarm_warning_only"]["n"] == 1
    assert p["methods"]["ECM"]["case_control"]["fp"] == 2 and p["methods"]["ECM"]["case_control"]["tn"] == 1
    c = S.aggregate(rows, complete_case=True)
    assert c["n_controls"] == {"fixed_observed": 1, "fixed_recommended": 0, "warning_only": 0}
    assert c["methods"]["ECM"]["false_alarm_fixed_observed"]["k"] == 0 and c["methods"]["ECM"]["case_control"]["fp"] == 0


def test_by_class_credits_only_the_matched_class():
    """A case carrying two classes is credited only under the class its rule matched (DEVIATIONS.md 2026-09-30):
    C3-099 carried definition_mismatch, element_retyped and other; DI matched only definition_mismatch."""
    b = states(ECM="right_reason", DI="right_reason")
    b["ECM"]["matched"] = [{"class": "definition_mismatch"}, {"class": "element_retyped"}]
    b["DI"]["matched"] = [{"class": "definition_mismatch"}]
    p = S.aggregate([row("a", "C3", b, classes=("definition_mismatch", "element_retyped", "other"))])
    bc = p["by_class"]
    assert bc["definition_mismatch"]["ECM"] == 1 and bc["definition_mismatch"]["DI"] == 1
    assert bc["element_retyped"]["ECM"] == 1 and bc["element_retyped"]["DI"] == 0
    assert bc["other"]["ECM"] == 0 and bc["other"]["DI"] == 0 and bc["other"]["n"] == 1


def test_distinct_nulled_counts_a_described_value_once(tmp_path, monkeypatch):
    """A described value enters once per edge (message and field element) and once per composition; the
    sensitivity table counts it once (pre-dispatch audit 2026-09-30, findings N1/N2/TF-2)."""
    import report_extra as X
    d = tmp_path / "s2_work" / "tasks" / "t1" / "recon"
    d.mkdir(parents=True)
    (d / "t1.json").write_text(json.dumps({"ports": [
        {"element": "msg:a/B", "side": "provides", "qos": {"reliability": "reliable"}},
        {"element": "msg:a/B", "side": "consumes", "qos": {"reliability": "best_effort"}}]}))
    monkeypatch.setattr(X, "HERE", str(tmp_path))
    occ = [{"task_id": "t1", "element": el, "path": "producer.outputs[0].qos.reliability", "value": "reliable",
            "reason": "no_token", "composition": comp} for el in ("msg:a/B", "field:a/B.x") for comp in ("broken", "resolved")]
    occ.append({"task_id": "t1", "element": "msg:a/B", "path": "consumer.inputs[0].qos.reliability", "value": "best_effort",
                "reason": "named_profile", "composition": "broken"})
    got = X.distinct_nulled(occ)
    assert got["occurrences"] == 5 and got["values"] == 2 and got["ports"] == 2
    assert got["by_reason"] == {"no_token": 1, "named_profile": 1}


def test_report_strata_are_per_corpus_and_hit_matrix_lists_detections():
    import make_report as MR
    import report_extra as X
    rows = [row("a", "C1", states(ECM="right_reason"), ros_generation="ROS1"),
            row("b", "C1", states(), ros_generation="ROS1"),
            row("c", "C3", states(), ros_generation="ROS1"),
            row("d", "C3", states(DI="right_reason"), ros_generation="ROS2")]
    for r in rows:
        r.update({"built_against_basis": "n/a", "s1_model": "m", "same_repository": False})
    MR.NUMBERS.clear()
    X.strata(MR, rows)
    ros1 = MR.NUMBERS["strata_per_corpus"]["ros_generation"]["ROS1"]
    assert ros1["C1"]["ECM"]["k"] == 1 and ros1["C1"]["ECM"]["n"] == 2
    assert ros1["C3"]["ECM"]["k"] == 0 and ros1["C3"]["ECM"]["n"] == 1
    body = X.hit_matrix(MR, rows)
    assert "a &" in body and "d &" in body and "b &" not in body and "c &" not in body
    assert MR.NUMBERS["hit_matrix_no_detection"] == {"C1": 1, "C2": 0, "C3": 1, "C3N": 0}


def test_detection_stage_counts_an_unknown_loudness_failure_once():
    """A failure whose loudness is unknown has its own row and is not also counted under its stage, so the
    stage rows and the unknown row sum to the corpus's failures (re-audit 2026-09-30, finding F7)."""
    import make_report as MR
    import report_extra as X
    rows = [row("a", "C1", states(ECM="right_reason"), loud="loud_documented"),
            row("b", "C1", states(), loud="unknown"),
            row("c", "C1", states(), loud="silent_documented")]
    for r, stage in zip(rows, ("build", "build", "run")):
        r["detection_stage"] = stage
    MR.NUMBERS.clear()
    X.detection_stage(MR, rows)
    c1 = MR.NUMBERS["detection_stage"]["C1"]
    assert c1["build"]["n"] == 1 and c1["build"]["ECM"] == 1
    assert c1["loudness_unknown"]["n"] == 1 and c1["run"]["n"] == 1
    assert sum(v["n"] for v in c1.values()) == 3


def test_alert_ratios_separate_findings_from_the_bound():
    """Supplementary ratios (R1 review, external review F3): an unassessable control is a bound penalty, not an emitted
    alert, so it enters neither the binary PPV nor the cause-correct share; a wrong-reason rejection of a failure
    is an emitted alert that counts as a rejected failure but not as a correct cause; a warning-only case rejected
    for its documented condition names the documented cause (pre-R2 audit, 2026-09-30)."""
    import make_report as MR
    import report_extra as X
    ctl_rej = dict({m: {"state": "accept", "findings": []} for m in S.METHODS}, ECM={"state": "reject", "findings": []})
    ctl_un = dict({m: {"state": "accept", "findings": []} for m in S.METHODS}, ECM={"state": "unassessable"})
    rows = [row("a", "C1", states(ECM="right_reason"), resolved=ctl_rej, res_status="observed"),
            row("b", "C1", states(ECM="wrong_reason"), resolved=ctl_un, res_status="observed"),
            row("c", "C1", states(), outcome="warning_only"),
            row("d", "C1", states(ECM="right_reason"), outcome="warning_only")]
    MR.NUMBERS.clear()
    X.alert_ratios(MR, rows)
    c1 = MR.NUMBERS["alert_ratios"]["C1"]
    assert c1["rejected_failures"] == 2 and c1["controls_rejected_by_findings"] == 2
    assert c1["controls_rejected_under_bound"] == 3
    assert c1["binary_ppv"] == [2, 4] and c1["cause_correct_share"] == [2, 4]


def test_aggregate_controls_precision_and_pairs():
    ctl = {m: {"state": "accept", "findings": []} for m in S.METHODS}
    ctl_rej = dict(ctl, ECM={"state": "reject", "findings": []})
    rows = [row("a", "C3", states(ECM="right_reason"), resolved=ctl, res_status="observed"),
            row("b", "C3", states(ECM="right_reason", DQ="right_reason"), resolved=ctl_rej, res_status="observed"),
            row("c", "C3", states(DQ="right_reason"), loud="loud_documented"),
            row("d", "C3", states(ECM="wrong_reason"), outcome="warning_only")]
    agg = S.aggregate(rows)
    ecm = agg["methods"]["ECM"]
    assert ecm["right_reason"]["k"] == 2 and ecm["false_alarm_fixed_observed"]["k"] == 1 and ecm["false_alarm_warning_only"]["k"] == 1
    cc = ecm["case_control"]
    assert (cc["tp"], cc["fp"], cc["fn"]) == (2, 2, 1) and abs(cc["precision"] - 0.5) < 1e-12
    pw = agg["pairwise"]["all_failures:ECM_vs_DQ"]
    assert (pw["b_first_only"], pw["c_second_only"]) == (1, 1) and pw["mcnemar_exact_p"] == 1.0
    assert agg["pairwise"]["all_failures:ECM_vs_NT"]["raw_rule_inclusion_scope"] == "NT_in_ECM_on_PAIR_CONCURRENT_only" and agg["pairwise"]["all_failures:ECM_vs_NT"]["mcnemar_exact_p"] is None
    assert agg["pairwise"]["all_failures:DI_vs_DQ"]["mcnemar_exact_p"] is None
    assert agg["pairwise"]["all_failures:DI_vs_DQ"]["exclusion_basis"] == "DI_rules_in_DQ"
    for pair in ["ECM_vs_SV", "NT_vs_SV", "DI_vs_SV", "DQ_vs_SV"]:
        item = agg["pairwise"]["all_failures:" + pair]
        assert item["inference_excluded"] and item["mcnemar_exact_p"] is None
        assert item["exclusion_basis"] == "SV_has_no_matching_class"
    assert agg["pairwise"]["all_failures:NT_vs_SV"]["raw_rule_inclusion_scope"] is None
    assert agg["methods"]["ECM"]["right_reason_silent"]["n"] == 2
    assert agg["union_detected"]["k"] == 3


def test_h1_record_and_strict_json():
    rows = [dict(row("a", "C3", states(ECM="right_reason")), c3_selected=True), row("b", "C2", states(ECM="right_reason")),
            dict(row("c", "C3", states(ECM="right_reason")), c3_selected=False)]
    h = S.h1_record(rows)
    assert h["n_eligible_failures"] == 1 and h["b_ecm_only"] == 1 and h["underpowered"]
    json.dumps(S.aggregate([]), allow_nan=False)
    json.dumps(h, allow_nan=False)


# ----------------------------------------------------------------------------- packets on the real pools
def test_c1_packets_keep_all_92_including_confidential_and_absent_fixes():
    it = K.items("C1")
    assert len(it) == 92
    st = {x["fix_status"] for x in it}
    assert {"listed", "confidential", "absent"} <= st
    assert all(isinstance(x["fix_commits"], list) for x in it)


def test_c2_packets_dedupe_one_source_per_candidate():
    it = K.items("C2")
    urls = [x["source_url"].rstrip("/") for x in it]
    assert len(it) == 31 and urls.count("https://github.com/ros-controls/ros2_control/issues/1400") == 1
    assert urls.count("https://arxiv.org/html/2407.19292v1") == 6  # modelled candidates stay for S1 to judge


# ----------------------------------------------------------------------------- definition ids
def test_ros1_md5_resolves_packages_by_package_xml(tmp_path):
    import definition_hash as D
    snap = tmp_path / "u0007"  # opaque snapshot id, single-package repo at the root
    (snap / "msg").mkdir(parents=True)
    (snap / "package.xml").write_text("<package><name>std_msgs</name></package>")
    (snap / "msg" / "String.msg").write_text("# comment\nstring data\n")
    (snap / "msg" / "Header.msg").write_text("uint32 seq\ntime stamp\nstring frame_id\n")
    mono = tmp_path / "u0008" / "geometry_msgs"  # monorepo subdirectory
    (mono / "msg").mkdir(parents=True)
    (mono / "package.xml").write_text("<package>\n  <name>geometry_msgs</name>\n</package>")
    (mono / "msg" / "Point.msg").write_text("float64 x\nfloat64 y\nfloat64 z\n")
    (mono / "msg" / "Quaternion.msg").write_text("float64 x\nfloat64 y\nfloat64 z\nfloat64 w\n")
    (mono / "msg" / "Pose.msg").write_text("Point position\nQuaternion orientation\n")
    (mono / "msg" / "PoseStamped.msg").write_text("Header header\nPose pose\n")
    (mono / "msg" / "PoseArray.msg").write_text("Header header\nPose[] poses\n")
    dirs = [str(snap), str(tmp_path / "u0008")]
    assert D.ros1_md5("std_msgs", "String", dirs) == "992ce8a1687cec8c8bd883ec73ca41d1"
    assert D.ros1_md5("geometry_msgs", "PoseStamped", dirs) == "d3812c3cbc69362b77dc0b19b345f8f5"
    assert D.ros1_md5("geometry_msgs", "PoseArray", dirs) == "916c28c5764443f268b296bb671b9d97"
    import pytest
    with pytest.raises(FileNotFoundError):
        D.ros1_md5("other_pkg", "String", dirs)  # same file name, wrong package


def test_materialize_asks_provider_about_consumer_only_elements(tmp_path, monkeypatch):
    import materialize as M
    monkeypatch.setattr(M, "S2", str(tmp_path / "s2"))
    monkeypatch.setattr(M, "LEDGER", str(tmp_path / "ledger"))
    monkeypatch.setattr(M, "export", lambda repo, rev, dest: (os.makedirs(dest, exist_ok=True) or ("done", "deadbeef")))
    monkeypatch.setattr(M, "HERE", str(tmp_path))
    (tmp_path / "specs").mkdir()
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "S2_describe.md").write_text("work in {S2WORK}")
    (tmp_path / "definition_hash.py").write_text("# stub")
    spec = {"case_id": "c", "eligible": True, "operation": "UPGRADE", "excerpt_based": False,
            "units": [{"name": "P", "role": "provider", "repo": "r", "broken_rev": "new", "resolved_rev": "new", "pinned": True},
                      {"name": "C", "role": "consumer", "repo": "r", "broken_rev": "c1", "resolved_rev": "c2", "pinned": True}],
            "consumer_built_against": {"broken": "old", "resolved": "new"},
            "inventory": [{"element": "topic:gps/fix", "sides": {"C": "consumes"}},
                          {"element": "topic:gp/raw", "sides": {"P": "provides", "C": "consumes"}}],
            "resolution": {"status": "observed"}}
    json.dump(spec, open(tmp_path / "specs" / "c.json", "w"))
    monkeypatch.setattr("sys.argv", ["materialize.py"])
    M.main()
    ledger = json.load(open(tmp_path / "ledger" / "tasks.json"))
    keys = set(ledger["by_key"])
    assert {"P@old", "P@new", "C@c1", "C@c2"} <= keys
    for tid in ledger["tasks"]:
        ws = tmp_path / "s2" / "tasks" / tid
        assert (ws / "packet.json").exists() and (ws / "recon").is_dir() and (ws / "definition_hash.py").exists()
        assert json.load(open(ws / "packet.json"))["task_id"] == tid
        assert (ws / "S2_PROMPT.md").read_text() == f"work in {ws}"
        assert ledger["tasks"][tid]["resolved_commit"] == "deadbeef"
    assert not (tmp_path / "s2" / "packets").exists() and not (tmp_path / "s2" / "recon").exists()
    p_old = ledger["tasks"][ledger["by_key"]["P@old"]]
    assert p_old["elements"] == {"topic:gps/fix": "provides", "topic:gp/raw": "provides"}
    c1 = ledger["tasks"][ledger["by_key"]["C@c1"]]
    assert c1["elements"]["topic:gps/fix"] == "consumes"


def test_materialize_excerpt_is_per_unit_and_follows_artifact(tmp_path, monkeypatch):
    import materialize as M
    monkeypatch.setattr(M, "S2", str(tmp_path / "s2"))
    monkeypatch.setattr(M, "LEDGER", str(tmp_path / "ledger"))
    monkeypatch.setattr(M, "export", lambda repo, rev, dest: (os.makedirs(dest, exist_ok=True) or ("done", "c0ffee")))
    monkeypatch.setattr(M, "HERE", str(tmp_path))
    for d in ("specs", "prompts", "artifacts"):
        (tmp_path / d).mkdir()
    (tmp_path / "prompts" / "S2_describe.md").write_text("x")
    (tmp_path / "definition_hash.py").write_text("# stub")
    spec = {"case_id": "c", "eligible": True, "operation": "PAIR", "excerpt_based": True,
            "units": [{"name": "R", "role": "consumer", "repo": "r", "broken_rev": "b", "resolved_rev": "f", "pinned": True},
                      {"name": "Pub", "role": "provider", "repo": None, "broken_rev": "as-reported", "resolved_rev": "as-reported"}],
            "inventory": [{"element": "topic:/t", "sides": {"Pub": "provides", "R": "consumes"}}],
            "resolution": {"status": "recommended"}}
    json.dump(spec, open(tmp_path / "specs" / "c.json", "w"))
    (tmp_path / "artifacts" / "c.txt").write_text("[[Pub@as-reported]]\n\"uses Best Effort\" -- u\n")
    monkeypatch.setattr("sys.argv", ["materialize.py"])
    M.main()
    ledger = json.load(open(tmp_path / "ledger" / "tasks.json"))
    by = ledger["by_key"]
    # the unit with a repository is a snapshot task even though the case is excerpt-based
    assert ledger["tasks"][by["R@b"]]["status"] == "done" and ledger["tasks"][by["R@f"]]["status"] == "done"
    pub = ledger["tasks"][by["Pub@as-reported"]]
    assert pub["status"] == "excerpt"
    ws = tmp_path / "s2" / "tasks" / pub["task_id"]
    assert (ws / "artifact.txt").read_text().startswith('"uses Best Effort"')
    # an undispatched excerpt task follows a changed artifact; a dispatched one does not
    (tmp_path / "artifacts" / "c.txt").write_text("[[Pub@as-reported]]\n\"uses Reliable\" -- u\n")
    M.main()
    assert (ws / "artifact.txt").read_text().startswith('"uses Reliable"')
    (ws / "DISPATCHED").write_text("2026-09-25T00:00:00Z\n")
    (tmp_path / "artifacts" / "c.txt").write_text("[[Pub@as-reported]]\n\"changed again\" -- u\n")
    (tmp_path / "prompts" / "S2_describe.md").write_text("y")
    M.main()
    assert (ws / "artifact.txt").read_text().startswith('"uses Reliable"')
    assert (ws / "S2_PROMPT.md").read_text() == "x"


def test_upgrade_delta_ignores_whitespace_only_signature_differences():
    spec = {"case_id": "c", "corpus": "C1", "operation": "UPGRADE",
            "units": [{"name": "P", "role": "provider"}, {"name": "C", "role": "consumer"}],
            "inventory": [{"element": "param:rate", "sides": {"P": "provides", "C": "consumes"}}]}
    built = desc("Pold", [], declares={"param:rate": "param rate:  double"})
    running = desc("Pnew", [], declares={"param:rate": "param rate: double"})
    cons = desc("C", [], references=["param:rate"])
    up = A.upgrade_units(spec, built, running, cons)[0]
    assert up["encoding"]["ver_delta"]["changed_fields"] == []


def test_canonical_sig_drops_transcription_but_keeps_real_changes():
    same = [("RCL_ACTION_PUBLIC RCL_WARN_UNUSED rcl_ret_t f( int x );", "rcl_ret_t f(int x)"),
            ("param png_level: int", "param .ns.compressed.png_level: int"),
            ("api mavlink::common::msg::X: struct X : mavlink::Message", "struct X : mavlink::Message {"),
            ("attribute_deprecated int g(AVCodecContext *c);", "int g(AVCodecContext*c)")]
    differ = [("char[16]", "char[24]"),
              ("def load(stream, Loader=None):", "def load(stream, Loader=Loader):"),
              ("def cb(time_jump: TimeJump):", "def cb(self, time_jump: TimeJump):"),
              ("int w(int participant)", "int w(int owner)")]  # C parameter names are left to the A2 substance check
    for a, b in same:
        assert A.canonical_sig(a) == A.canonical_sig(b), (a, b)
    for a, b in differ:
        assert A.canonical_sig(a) != A.canonical_sig(b), (a, b)


def test_upgrade_delta_ignores_macro_only_difference_but_keeps_type_change():
    spec = {"case_id": "c", "corpus": "C3", "operation": "UPGRADE",
            "units": [{"name": "P", "role": "provider"}, {"name": "C", "role": "consumer"}],
            "inventory": [{"element": "api:f", "sides": {"P": "provides", "C": "consumes"}},
                          {"element": "field:p/Gid.data", "sides": {"P": "provides", "C": "consumes"}}]}
    built = desc("Pold", [], declares={"api:f": "api f: RMW_PUBLIC rmw_ret_t f( int x );", "field:p/Gid.data": "field p/Gid.data: char[16]"})
    running = desc("Pnew", [], declares={"api:f": "rmw_ret_t f(int x)", "field:p/Gid.data": "field p/Gid.data: char[24]"})
    cons = desc("C", [], references=["api:f", "field:p/Gid.data"])
    up = A.upgrade_units(spec, built, running, cons)[0]
    assert up["encoding"]["ver_delta"]["changed_fields"] == ["field:p/Gid.data"]


def test_canonical_type_joins_spellings_of_one_type_only():
    for a in ("sensor_msgs/msg/Image", "sensor_msgs::msg::Image", "sensor_msgs/Image", " sensor_msgs/Image "):
        assert A.canonical_type(a) == "sensor_msgs/Image"
    assert A.canonical_type("rcl_interfaces/srv/GetParameters") == A.canonical_type("rcl_interfaces/GetParameters")
    assert A.canonical_type("nav2_msgs/action/FollowPath") == "nav2_msgs/FollowPath"
    assert A.canonical_type("sensor_msgs/Image") != A.canonical_type("sensor_msgs/CompressedImage")
    assert A.canonical_type("geometry_msgs/Pose") != A.canonical_type("my_msgs/Pose")
    assert A.canonical_type(None) is None
    # a spelling difference alone does not make a type mismatch in the assembled edge
    p = {"ports": [{"element": "topic:/img", "side": "provides", "msg_type": "sensor_msgs/msg/Image"}]}
    c = {"ports": [{"element": "topic:/img", "side": "consumes", "msg_type": "sensor_msgs/Image"}]}
    assert A.port_of(p, "topic:/img", "provides")[0]["msg_type"] == A.port_of(c, "topic:/img", "consumes")[0]["msg_type"]


def _a2_record(iid, cid, path, value_verdict, substance):
    return {"item_id": iid, "kind": "A2", "case_id": cid, "composition": "broken", "method_label": "M1", "rule": "field_break",
            "values": [{"path": path, "verdict": value_verdict, "source_excerpt": "x"},
                       {"path": "ver_delta.consumer_reads[api:f]", "verdict": "verified", "source_excerpt": "y"}],
            "substance": ([{"path": path, "verdict": substance, "built_excerpt": "a", "running_excerpt": "b"}] if substance else []),
            "operation_edge": {"verdict": "agree", "reason": ""}, "notes": ""}


def test_fold_substance_demotes_transcription_only_changes(tmp_path, monkeypatch):
    import adjudicate as J
    monkeypatch.setattr(J, "HERE", str(tmp_path)); monkeypatch.setattr(J, "ADJ", str(tmp_path / "adjudication")); monkeypatch.setattr(J, "OUT", str(tmp_path / "adjudicated"))
    (tmp_path / "specs").mkdir(); (tmp_path / "ledger").mkdir()
    for who in ('adj1', 'withdrawn_google', 'adj1_repeat'):
        (tmp_path / "adjudication" / who).mkdir(parents=True)
    path = "ver_delta.changed_fields[api:f]"
    enc = {"type": "UPGRADE", "ver_delta": {"changed_fields": ["api:f"], "consumer_reads": ["api:f"], "semver_old": None, "semver_new": None}}
    u = unit(enc, prov_for(path, "ver_delta.consumer_reads[api:f]"), kind="upgrade", element=None)

    def ecm_state():
        v = json.load(open(tmp_path / "adjudicated" / "provenance_verdicts.json")).get("c", {}).get("broken", {})
        return S.score_composition(comp(u), [cond("element_retyped", "api:f")], "UPGRADE", v)["ECM"]["state"]
    for who in ('adj1', 'withdrawn_google'):
        json.dump(_a2_record("A2-c", "c", path, "verified", "transcription_only"), open(tmp_path / "adjudication" / who / "A2-c.json", "w"))
    J.fold()
    assert ecm_state() == "unverified"
    # reading (ii): the same records folded without the substance demotion go to their own directory
    J.fold(no_substance=True)
    assert ecm_state() == "unverified"  # the primary fold is untouched
    v2 = json.load(open(tmp_path / "adjudicated_nosubstance" / "provenance_verdicts.json")).get("c", {}).get("broken", {})
    assert S.score_composition(comp(u), [cond("element_retyped", "api:f")], "UPGRADE", v2)["ECM"]["state"] == "right_reason"
    import pytest
    with pytest.raises(SystemExit):
        J.fold(adj1_only=True, no_substance=True)
    for who in ('adj1', 'withdrawn_google'):
        json.dump(_a2_record("A2-c", "c", path, "verified", "substantive"), open(tmp_path / "adjudication" / who / "A2-c.json", "w"))
    J.fold()
    assert ecm_state() == "right_reason"
    json.dump(_a2_record("A2-c", "c", path, "verified", "transcription_only"), open(tmp_path / "adjudication" / 'withdrawn_google' / "A2-c.json", "w"))
    J.fold()
    assert {s["domain"] for s in json.load(open(tmp_path / "adjudicated" / "splits.json"))} == {"substance"}
    assert ecm_state() == "unverified"  # a pending split does not count as substantive
    json.dump(_a2_record("A2-c", "c", path, "verified", None), open(tmp_path / "adjudication" / 'adj1' / "A2-c.json", "w"))
    json.dump(_a2_record("A2-c", "c", path, "verified", None), open(tmp_path / "adjudication" / 'withdrawn_google' / "A2-c.json", "w"))
    J.fold()
    assert ecm_state() == "unverified"  # no substance answer at all counts as unverifiable


def test_upgrade_delta_needs_determinate_states_on_both_sides():
    spec = {"case_id": "c", "corpus": "C1", "operation": "UPGRADE",
            "units": [{"name": "P", "role": "provider"}, {"name": "C", "role": "consumer"}],
            "inventory": [{"element": "topic:/imu", "sides": {"P": "provides", "C": "consumes"}},
                          {"element": "field:p/T.raw", "sides": {"P": "provides", "C": "consumes"}}]}
    built = desc("Pold", [], declares={"field:p/T.raw": "field p/T.raw: std_msgs/String"})  # topic undetermined
    running = desc("Pnew", [], declares={"topic:/imu": "topic /imu: p/T"})
    running["not_declared"] = ["field:p/T.raw"]
    running["provenance"]["not_declared[field:p/T.raw]"] = "snapshot:Pnew:msg/T.msg:1-5 | complete definition"
    cons = desc("C", [], references=["topic:/imu", "field:p/T.raw"])
    up = A.upgrade_units(spec, built, running, cons)[0]
    assert up["encoding"]["ver_delta"]["changed_fields"] == ["field:p/T.raw"]
    assert up["unknown_delta"] == ["topic:/imu"]
    assert "ver_delta.changed_fields[field:p/T.raw]" in up["provenance"]


def test_section_empty_body_is_no_evidence():
    import materialize as M
    text = "[[A@r1]]\nfloat32 x\n\n[[B@r1]]\n\n[[C@r1]]\n"
    assert M._section(text, "A", "r1") == "float32 x\n"
    assert M._section(text, "B", "r1") is None and M._section(text, "C", "r1") is None


def test_materialize_ids_are_never_reused_and_orphans_are_withdrawn(tmp_path, monkeypatch):
    import materialize as M
    monkeypatch.setattr(M, "S2", str(tmp_path / "s2"))
    monkeypatch.setattr(M, "LEDGER", str(tmp_path / "ledger"))
    monkeypatch.setattr(M, "export", lambda repo, rev, dest: (os.makedirs(dest, exist_ok=True) or ("done", "abc")))
    monkeypatch.setattr(M, "HERE", str(tmp_path))
    for d in ("specs", "prompts", "artifacts"):
        (tmp_path / d).mkdir()
    (tmp_path / "prompts" / "S2_describe.md").write_text("x")
    (tmp_path / "definition_hash.py").write_text("# stub")
    spec = {"case_id": "c", "eligible": True, "operation": "PAIR",
            "units": [{"name": "A", "role": "provider", "repo": "r", "broken_rev": "a1", "resolved_rev": "a1", "pinned": True},
                      {"name": "B", "role": "consumer", "repo": "r", "broken_rev": "b1", "resolved_rev": "b1", "pinned": True}],
            "inventory": [{"element": "topic:/t", "sides": {"A": "provides", "B": "consumes"}}], "resolution": {"status": "recommended"}}
    json.dump(spec, open(tmp_path / "specs" / "c.json", "w"))
    monkeypatch.setattr("sys.argv", ["materialize.py"])
    M.main()
    L = json.load(open(tmp_path / "ledger" / "tasks.json"))
    assert set(L["by_key"]) == {"A@a1", "B@b1"} and L["next_id"] == 3
    # the consumer is renamed by a re-run of S1: its old task is withdrawn, the new one gets a fresh id
    spec["units"][1]["name"] = "B_renamed"
    spec["inventory"][0]["sides"] = {"A": "provides", "B_renamed": "consumes"}
    json.dump(spec, open(tmp_path / "specs" / "c.json", "w"))
    M.main()
    L = json.load(open(tmp_path / "ledger" / "tasks.json"))
    old = L["tasks"]["u0002"]
    assert old["status"] == "withdrawn" and not (tmp_path / "s2" / "tasks" / "u0002").exists()
    assert L["by_key"]["B_renamed@b1"] == "u0003" and L["next_id"] == 4
    # a dispatched task is never withdrawn
    (tmp_path / "s2" / "tasks" / "u0003" / "DISPATCHED").write_text("t\n")
    spec["units"][1]["name"] = "B_again"
    spec["inventory"][0]["sides"] = {"A": "provides", "B_again": "consumes"}
    json.dump(spec, open(tmp_path / "specs" / "c.json", "w"))
    M.main()
    L = json.load(open(tmp_path / "ledger" / "tasks.json"))
    assert L["tasks"]["u0003"]["status"] == "superseded" and (tmp_path / "s2" / "tasks" / "u0003").exists()
    assert "B_renamed@b1" not in L["by_key"] and L["by_key"]["B_again@b1"] == "u0004"


def test_edge_direction_follows_element_sides():
    import assemble as A
    spec = {"inventory": [{"element": "service:/s", "sides": {"srv": "provides", "cli": "consumes"}},
                          {"element": "field:pkg/srv/S.request_x", "sides": {"cli": "provides", "srv": "consumes"}}]}
    srv = {"ports": [{"element": "service:/s", "side": "provides", "msg_type": "pkg/srv/S"},
                     {"element": "field:pkg/srv/S.request_x", "side": "consumes", "msg_type": "pkg/srv/S"}], "provenance": {}}
    cli = {"ports": [{"element": "service:/s", "side": "consumes", "msg_type": "pkg/srv/S"},
                     {"element": "field:pkg/srv/S.request_x", "side": "provides", "msg_type": "pkg/srv/S"}], "provenance": {}}
    units = A.edge_units(spec, srv, cli, "PAIR", "srv", "cli")
    by = {u["element"]: u for u in units}
    assert by["service:/s"]["status"] == "done" and by["service:/s"]["direction"] == {"producer": "srv", "consumer": "cli"}
    assert by["field:pkg/srv/S.request_x"]["status"] == "done"
    assert by["field:pkg/srv/S.request_x"]["direction"] == {"producer": "cli", "consumer": "srv"}


def test_a2_items_merge_identical_evidence(tmp_path, monkeypatch):
    import adjudicate as J
    monkeypatch.setattr(J, "HERE", str(tmp_path)); monkeypatch.setattr(J, "ADJ", str(tmp_path / "adjudication"))
    for d in ("specs", "scores_adjudicated", "scores_adjudicated_adj1only", "assembled", "ledger"):
        (tmp_path / d).mkdir()
    prov = {"producer.outputs[0].definition_id": "snapshot:a.msg:1 | x", "consumer.inputs[0].definition_id": "built: snapshot:b.msg:1 | y"}
    units = [{"kind": "pair_view", "element": e, "status": "done", "encoding": {}, "provenance": prov} for e in ("msg:p/M", "field:p/M.a", "field:p/M.b")]
    json.dump({"case_id": "c", "compositions": {"broken": {"units": units}}}, open(tmp_path / "assembled" / "c.json", "w"))
    findings = [{"rule": "di_definition_mismatch", "element": e, "unit_kind": "pair_view"} for e in ("msg:p/M", "field:p/M.a", "field:p/M.b")]
    score = {"case_id": "c", "broken": {"DI": {"state": "right_reason", "findings": findings,
             "matched": [{"rule": "di_definition_mismatch", "element": f["element"]} for f in findings]}}, "resolved": {}}
    json.dump(score, open(tmp_path / "scores_adjudicated" / "c.json", "w"))
    json.dump(score, open(tmp_path / "scores_adjudicated_adj1only" / "c.json", "w"))   # the same finding in both variants
    monkeypatch.setattr(J, "METHODS", ["DI"])
    J.items()
    a2 = json.load(open(tmp_path / "adjudication" / "packets" / "A2_00.json"))
    assert len(a2) == 1 and len(a2[0]["also_covers"]) == 2
    first_id = a2[0]["item_id"]
    # a finding that only the ADJ1-only scoring produces becomes its own item; ids do not depend on file order
    other = {"producer.outputs[0].frame": "snapshot:a.py:3 | map", "consumer.inputs[0].frame": "snapshot:b.py:4 | odom"}
    units.append({"kind": "edge", "element": "topic:/f", "status": "done", "encoding": {}, "provenance": other})
    json.dump({"case_id": "c", "compositions": {"broken": {"units": units}}}, open(tmp_path / "assembled" / "c.json", "w"))
    extra = {"rule": "dq_qos_reliability", "element": "topic:/f", "unit_kind": "edge"}
    score2 = json.loads(json.dumps(score))
    score2["broken"]["DI"]["findings"].append(extra)
    score2["broken"]["DI"]["matched"].insert(0, {"rule": "dq_qos_reliability", "element": "topic:/f"})  # position 0 in this file too
    json.dump(score2, open(tmp_path / "scores_adjudicated_adj1only" / "c.json", "w"))
    J.items()
    a2 = json.load(open(tmp_path / "adjudication" / "packets" / "A2_00.json"))
    assert len(a2) == 2 and a2[0]["item_id"] == first_id and len({x["item_id"] for x in a2}) == 2


def _adj_record(iid, cid, elig="agree", loud="agree", loud_prop=None, res="agree", res_prop=None):
    return {"item_id": iid, "kind": "A1", "case_id": cid,
            "eligibility": {"verdict": elig, "stop_step": 6, "reason_code": None, "quote": "q", "url": "u"},
            "failed_conditions": [{"index": 0, "class_verdict": "agree", "proposed_class": None, "elements_verdict": "agree", "proposed_elements": [], "quote": "q", "url": "u"}],
            "missed_conditions": [], "loudness": {"verdict": loud, "proposed": loud_prop, "quote": "q", "url": "u"},
            "resolution": {"verdict": res, "proposed": res_prop, "quote": "q"}, "notes": ""}


def test_fold_split_goes_to_third_and_is_pending_without_it(tmp_path, monkeypatch):
    import adjudicate as J
    monkeypatch.setattr(J, "HERE", str(tmp_path)); monkeypatch.setattr(J, "ADJ", str(tmp_path / "adjudication")); monkeypatch.setattr(J, "OUT", str(tmp_path / "adjudicated"))
    (tmp_path / "specs").mkdir(); (tmp_path / "ledger").mkdir()
    json.dump({"case_id": "c", "eligible": True, "loudness": "silent_documented", "resolution": {"status": "observed"},
               "failed_conditions": [{"class": "frame_mismatch", "implicated_elements": ["topic:/t"]}]}, open(tmp_path / "specs" / "c.json", "w"))
    for who in ('adj1', 'withdrawn_google', 'adj1_repeat'):
        (tmp_path / "adjudication" / who).mkdir(parents=True)
    json.dump(_adj_record("A1-c", "c", loud="disagree", loud_prop="unknown", res="disagree", res_prop="recommended"),
              open(tmp_path / "adjudication" / 'adj1' / "A1-c.json", "w"))
    json.dump(_adj_record("A1-c", "c"), open(tmp_path / "adjudication" / 'withdrawn_google' / "A1-c.json", "w"))
    J.fold()
    log = {x["item"]: x for x in json.load(open(tmp_path / "adjudicated" / "fold_log.json"))}
    assert log["A1-c"]["decision"] == "split_pending"
    assert {s["domain"] for s in json.load(open(tmp_path / "adjudicated" / "splits.json"))} == {"loudness", "resolution"}
    assert json.load(open(tmp_path / "adjudicated" / "overrides.json")) == {}
    # the third adjudicator sides with the first on loudness only
    json.dump(_adj_record("A1-c", "c", loud="disagree", loud_prop="unknown", res="agree"),
              open(tmp_path / "adjudication" / 'adj1_repeat' / "A1-c.json", "w"))
    J.fold()
    ov = json.load(open(tmp_path / "adjudicated" / "overrides.json"))
    assert ov == {"c": {"loudness": "unknown"}}
    assert json.load(open(tmp_path / "adjudicated" / "splits.json")) == []
    k = json.load(open(tmp_path / "adjudicated" / "kappa.json"))
    assert k["loudness"]["n"] == 1 and k["resolution"]["n"] == 1


def _a1_ids(tmp_path):
    out = []
    for f in sorted((tmp_path / "adjudication" / "packets").glob("A1_*.json")):
        out += json.load(open(f))
    return out


def test_a1_items_skip_pilot_add_extras_once_and_keep_the_sample(tmp_path, monkeypatch):
    import adjudicate as J
    monkeypatch.setattr(J, "HERE", str(tmp_path)); monkeypatch.setattr(J, "ADJ", str(tmp_path / "adjudication"))
    for d in ("specs", "scores", "ledger", "pilot"):
        (tmp_path / d).mkdir()
    specs = [{"case_id": "P", "corpus": "C1", "eligible": True, "outcome_class": "failure"},
             {"case_id": "C3-001", "corpus": "C3", "eligible": True, "outcome_class": "warning_only"},
             {"case_id": "C3N-001", "corpus": "C3N", "eligible": True, "outcome_class": "undocumented"},
             {"case_id": "U", "corpus": "C1", "eligible": True, "outcome_class": "undocumented"},
             {"case_id": "X", "corpus": "C1", "eligible": False, "eligibility": {"E3": {"pass": False}}}]
    specs += [{"case_id": f"E{i:02d}", "corpus": "C1", "eligible": False, "eligibility": {"E2": {"pass": False}}} for i in range(10)]
    for s in specs:
        json.dump(s, open(tmp_path / "specs" / f"{s['case_id']}.json", "w"))
    json.dump({"quarantined_pilot_cases": ["P"]}, open(tmp_path / "pilot" / "PILOT_CASES.json", "w"))
    J.items()
    before = {it["case_id"] for it in _a1_ids(tmp_path) if it.get("sample") == "E2_exclusion_20pct"}
    assert len(before) == 2
    sampled = sorted(before)[0]
    json.dump({"cases": [{"case_id": c} for c in ("X", "P", sampled, "U")]}, open(tmp_path / "ledger" / "a1_extra.json", "w"))
    J.items()
    items_ = _a1_ids(tmp_path)
    ids = [it["case_id"] for it in items_]
    assert "P" not in ids                                   # pilot never enters, not even as an extra
    assert ids.count(sampled) == 1 and ids.count("X") == 1 and ids.count("U") == 1
    assert {it["case_id"] for it in items_ if it.get("sample") == "E2_exclusion_20pct"} == before
    assert {it["case_id"] for it in items_ if it.get("sample") == "added"} == {"X", "U"}
    assert "C3-001" in ids and "C3N-001" in ids              # every eligible C3 and C3-neutral case


def test_fold_excluded_case_folds_eligibility_only(tmp_path, monkeypatch):
    import adjudicate as J
    monkeypatch.setattr(J, "HERE", str(tmp_path)); monkeypatch.setattr(J, "ADJ", str(tmp_path / "adjudication")); monkeypatch.setattr(J, "OUT", str(tmp_path / "adjudicated"))
    (tmp_path / "specs").mkdir(); (tmp_path / "ledger").mkdir()
    json.dump({"case_id": "x", "eligible": False, "ineligible_reason": "internal"}, open(tmp_path / "specs" / "x.json", "w"))
    for who in ('adj1', 'withdrawn_google', 'adj1_repeat'):
        (tmp_path / "adjudication" / who).mkdir(parents=True)
    for who in ('adj1', 'withdrawn_google'):
        json.dump(_adj_record("A1-x", "x"), open(tmp_path / "adjudication" / who / "A1-x.json", "w"))
    J.fold()
    k = json.load(open(tmp_path / "adjudicated" / "kappa.json"))
    assert k["eligibility"]["n"] == 1
    assert k["loudness"]["n"] == 0 and k["resolution"]["n"] == 0 and k["class"]["n"] == 0
    # both adjudicators find the case eligible: the exclusion is overturned, nothing else is touched
    for who in ('adj1', 'withdrawn_google'):
        json.dump(_adj_record("A1-x", "x", elig="disagree", loud="disagree", loud_prop="loud_documented"),
                  open(tmp_path / "adjudication" / who / "A1-x.json", "w"))
    J.fold()
    assert json.load(open(tmp_path / "adjudicated" / "overrides.json")) == {"x": {"eligible": True, "ineligible_reason": None}}


def _c3_fixture(tmp_path, monkeypatch, repos):
    import scoring as S
    (tmp_path / "candidates").mkdir()
    urls = [f"https://github.com/o/{r}/issues/{i}" for i, r in enumerate(repos)]
    json.dump({"ordered": urls}, open(tmp_path / "candidates" / "C3_order.json", "w"))
    json.dump({"hits": {u: {"repo": f"o/{r}"} for u, r in zip(urls, repos)}}, open(tmp_path / "candidates" / "C3_ledger.json", "w"))
    monkeypatch.setattr(S, "HERE", str(tmp_path))
    monkeypatch.setattr(S, "C3_PLANNED_N", 3)
    monkeypatch.setattr(S, "C3_PER_REPO_CAP", 2)
    return S


def _fail(cid):
    return {"case_id": cid, "corpus": "C3", "eligible": True, "outcome_class": "failure"}


def test_c3_selection_cap_stop_and_gap(tmp_path, monkeypatch):
    S = _c3_fixture(tmp_path, monkeypatch, ["a", "a", "a", "b", "a", "b", "c", "c"])
    specs = {f"C3-{i:03d}": _fail(f"C3-{i:03d}") for i in (1, 2, 3, 4)}
    specs["C3-003"]["eligible"] = True
    # 001,002 selected (repo a hits cap 2); 003 in capped repo -> capped; 004 (b) selected -> N=3 reached
    sel = S.c3_selection(specs)
    assert sel["status"] == "reached" and sel["selected"] == ["C3-001", "C3-002", "C3-004"]
    assert sel["capped"] == ["C3-003"] and sel["stop_index"] == 3
    # a spec processed beyond the stop point is reported as after_stop
    specs["C3-006"] = _fail("C3-006")
    assert S.c3_selection(specs)["after_stop"] == ["C3-006"]
    # a gap before the stop point halts the walk (no skipping of unspecified, uncapped candidates)
    del specs["C3-002"]
    sel = S.c3_selection(specs)
    assert sel["status"] == "incomplete" and sel["first_missing"] == "C3-002" and sel["selected"] == ["C3-001"]
    # an unspecified candidate in a capped repository is skipped, not a gap
    specs2 = {c: _fail(c) for c in ("C3-001", "C3-002", "C3-004")}
    sel = S.c3_selection(specs2)
    assert sel["skipped_capped_repo"] == ["C3-003"] and sel["status"] == "reached"


def test_main_excludes_pilot_and_counts_only_selected_c3_in_h1(tmp_path, monkeypatch):
    S = _c3_fixture(tmp_path, monkeypatch, ["a", "b", "c", "d"])
    (tmp_path / "specs").mkdir(); (tmp_path / "pilot").mkdir(); (tmp_path / "ledger").mkdir()
    json.dump({"quarantined_pilot_cases": ["P-1"]}, open(tmp_path / "pilot" / "PILOT_CASES.json", "w"))
    base = {"operation": "PAIR", "failed_conditions": [{"class": "other", "implicated_elements": []}], "units": []}
    for cid, corpus in (("P-1", "C1"), ("X-1", "C1"), ("C3-001", "C3"), ("C3-002", "C3"), ("C3-003", "C3"), ("C3-004", "C3")):
        json.dump(dict(base, case_id=cid, corpus=corpus, eligible=True, outcome_class="failure"),
                  open(tmp_path / "specs" / f"{cid}.json", "w"))
    S.main(write=True, adjudicated=False)
    res = json.load(open(tmp_path / "results.json"))
    assert res["pilot_excluded"] == ["P-1"]
    assert not (tmp_path / "scores" / "P-1.json").exists() and (tmp_path / "scores" / "X-1.json").exists()
    assert res["H1"]["n_eligible_failures"] == 3          # C3-001..003 selected, N=3
    assert not (tmp_path / "scores" / "C3-004.json").exists()  # after the stop point
    assert "s1_model" in res["strata"] and "built_against_basis" in res["strata"]


def test_sha_dir_survives_dangling_and_external_symlinks(tmp_path):
    import materialize as M
    d = tmp_path / "snap"
    (d / "a").mkdir(parents=True)
    (d / "a" / "f.txt").write_text("x")
    os.symlink("does/not/exist.yaml", d / "a" / "dangling.yaml")
    outside = tmp_path / "host.txt"
    outside.write_text("host 1")
    os.symlink(str(outside), d / "a" / "external.txt")
    h1 = M.sha_dir(str(d))
    outside.write_text("host 2")  # changing a file outside the snapshot must not change the hash
    assert M.sha_dir(str(d)) == h1
    os.remove(d / "a" / "dangling.yaml")
    os.symlink("other/target.yaml", d / "a" / "dangling.yaml")  # a different link target does
    assert M.sha_dir(str(d)) != h1



def test_add_ledger_keeps_same_basename_files_apart_and_keeps_history(tmp_path, monkeypatch):
    import freeze as F
    monkeypatch.setattr(F, "HERE", str(tmp_path)); monkeypatch.setattr(F, "MANIFEST", str(tmp_path / "FREEZE.json"))
    json.dump({"files": {}, "ledgers": {}}, open(tmp_path / "FREEZE.json", "w"))
    (tmp_path / "v2").mkdir()
    (tmp_path / "key.json").write_text("a"); (tmp_path / "v2" / "key.json").write_text("b")
    F.add_ledger(str(tmp_path / "key.json")); F.add_ledger(str(tmp_path / "v2" / "key.json"))
    m = json.load(open(tmp_path / "FREEZE.json"))
    assert {r["path"] for r in m["ledgers"].values()} == {"key.json", os.path.join("v2", "key.json")}
    (tmp_path / "key.json").write_text("a2")
    F.add_ledger(str(tmp_path / "key.json"))
    m = json.load(open(tmp_path / "FREEZE.json"))
    assert len(m["ledgers"]) == 2 and [h["path"] for h in m["ledger_history"]] == ["key.json"]
    import hashlib
    assert m["ledger_history"][0]["sha256"] == hashlib.sha256(b"a").hexdigest()  # the earlier content, not erased


# ----------------------------------------------------------------------------- declared sensitivity analyses
def _qos_tasks(tmp_path):
    t = tmp_path / "s2_work" / "tasks"
    (t / "u1" / "snapshot" / "pkg").mkdir(parents=True)
    (t / "u1" / "snapshot" / "pkg" / "a.cpp").write_text(
        "auto qos = rclcpp::QoS(10);\n"
        "qos.reliability(RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT);\n"
        "auto s = rclcpp::SensorDataQoS();\n")
    (t / "u2" / "snapshot").mkdir(parents=True)
    (t / "u2" / "snapshot" / "b.py").write_text("qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE)\n")
    (t / "u3").mkdir()
    (t / "u3" / "artifact.txt").write_text("publishes using **Best Effort** reliability\nthe link is unreliable\n")
    (t / "u4" / "snapshot").mkdir(parents=True)
    (t / "u4" / "snapshot" / "c.py").write_text("self.create_subscription(Pose, 'p', self.cb, 10)\n")
    return str(t)


def test_qos_literal_reads_the_cited_lines_not_the_explanation(tmp_path):
    import qos_literal as Q
    td = _qos_tasks(tmp_path)
    assert Q.classify("reliability", "best_effort", "u1", "snapshot:pkg/a.cpp:2 | qos.reliability(...)", td) == "literal"
    assert Q.classify("reliability", "best_effort", "u1", "snapshot:pkg/a.cpp:1-2 | ...", td) == "literal"
    assert Q.classify("reliability", "reliable", "u1", "snapshot:pkg/a.cpp:2 | ...", td) == "no_token"
    # the explanation names the default's macro, the cited line does not
    assert Q.classify("reliability", "reliable", "u1",
                      "snapshot:pkg/a.cpp:1 | QoS(10); default is RMW_QOS_POLICY_RELIABILITY_RELIABLE", td) == "no_token"
    assert Q.classify("reliability", "best_effort", "u1", "snapshot:pkg/a.cpp:3 | SensorDataQoS()", td) == "named_profile"
    assert Q.classify("reliability", "reliable", "u2", "snapshot:b.py:1", td) == "literal"
    # a location outside the unit's own snapshot, or none at all, is not evidence
    assert Q.classify("reliability", "reliable", "u1", "snapshot:../../u2/snapshot/b.py:1", td) == "no_location"
    assert Q.classify("reliability", "reliable", "u1", "same as ports[0]", td) == "no_location"
    assert Q.classify("reliability", "reliable", "u1", None, td) == "no_location"
    # an excerpt artifact is prose: the value's words count, "unreliable" does not
    assert Q.classify("reliability", "best_effort", "u3", "artifact.txt:1 | \"...\"", td) == "literal"
    assert Q.classify("reliability", "reliable", "u3", "artifact.txt:2", td) == "no_token"


def test_qos_literal_nulls_per_side_and_changes_the_score(tmp_path):
    import qos_literal as Q
    td = _qos_tasks(tmp_path)
    enc = edge(port(rel="best_effort", dur=None), port(rel="reliable", dur="volatile"))
    prov = {f"{PO}.qos.reliability": "snapshot:pkg/a.cpp:2", f"{PI}.qos.reliability": "snapshot:c.py:1",
            f"{PO}.msg_type": "snapshot:pkg/a.cpp:1", f"{PI}.msg_type": "snapshot:c.py:1"}
    u = dict(unit(enc, prov, element="topic:/p"), tasks={"producer": "u1", "consumer": "u4"})
    before = copy.deepcopy(u)
    nu, nulled = Q.null_unit(u, tasks_dir=td)
    assert u == before  # the input unit is not changed
    assert nu["encoding"]["producer"]["outputs"][0]["qos"]["reliability"] == "best_effort"
    assert nu["encoding"]["consumer"]["inputs"][0]["qos"] == {"reliability": None, "durability": None, "deadline_ms": None}
    assert sorted((x["path"], x["reason"], x["task_id"]) for x in nulled) == [
        (f"{PI}.qos.durability", "no_location", "u4"), (f"{PI}.qos.reliability", "no_token", "u4")]
    c = [cond("qos_reliability", "topic:/p")]
    assert S.score_composition(comp(u), c, "PAIR", {})["DQ"]["state"] == "right_reason"
    comp_q, _ = Q.null_composition(comp(u), tasks_dir=td)
    assert S.score_composition(comp_q, c, "PAIR", {})["DQ"]["state"] == "accept"
    # the named-profile variant (exploratory) keeps a value set by a named profile, the declared rule does not
    prov2 = dict(prov, **{f"{PI}.qos.reliability": "snapshot:pkg/a.cpp:3"})
    u2 = dict(unit(edge(port(rel="reliable"), port(rel="best_effort")), prov2), tasks={"producer": "u4", "consumer": "u1"})
    assert Q.null_unit(u2, tasks_dir=td)[0]["encoding"]["consumer"]["inputs"][0]["qos"]["reliability"] is None
    assert Q.null_unit(u2, True, td)[0]["encoding"]["consumer"]["inputs"][0]["qos"]["reliability"] == "best_effort"
    assert Q.null_composition(None) == (None, [])


def test_cited_text_follows_a_bare_line_reference_to_the_last_path(tmp_path):
    import qos_literal as Q
    t = tmp_path / "tasks"
    (t / "u1" / "snapshot" / "pkg").mkdir(parents=True)
    (t / "u1" / "snapshot" / "pkg" / "g.cpp").write_text(
        'odom.header.frame_id = frame_id;\n// other\ndeclare("frame_id", "map");\n')
    td = str(t)
    text, _ = Q.cited_text("u1", "snapshot:pkg/g.cpp:1 (assign) with parameter default at :3 (declare)", td)
    assert '"map"' in text and "odom.header" in text
    assert '"map"' in Q.cited_text("u1", "snapshot:pkg/g.cpp:1 and (:3)", td)[0]
    # a bare reference with no path before it, or a clock time, is not a location
    assert Q.cited_text("u1", "default at :3", td)[0] is None
    assert '"map"' not in Q.cited_text("u1", "snapshot:pkg/g.cpp:1 at 10:3", td)[0]


def test_frame_literal_keeps_tokens_and_verbatim_values_and_nulls_descriptions(tmp_path):
    import frame_literal as F
    t = tmp_path / "tasks"
    (t / "u1" / "snapshot").mkdir(parents=True)
    (t / "u1" / "snapshot" / "d.py").write_text(
        'msg.header.frame_id = "From real-time state data"\nsp = transform_frame_enu_ned(v)\nframe = "ned"\n')
    td = str(t)
    assert F.classify("per_message", "u1", None, td) == "token" and F.classify("none", "u1", None, td) == "token"
    assert F.classify("From real-time state data", "u1", "snapshot:d.py:1", td) == "literal"
    assert F.classify("ENU (ROS input) -> FCU frame via transform_frame_enu_ned", "u1", "snapshot:d.py:2", td) == "not_in_cited_lines"
    assert F.classify("ned", "u1", "snapshot:d.py:1", td) == "not_in_cited_lines"
    assert F.classify("ned", "u1", "no line cited", td) == "no_location"
    # a frame mismatch that rests on a description is gone under the sensitivity, one on literals stays
    e = edge(port(frame="ENU (ROS input) -> FCU frame via transform_frame_enu_ned"), port(frame="ned"))
    prov = {f"{PO}.frame": "snapshot:d.py:2", f"{PI}.frame": "snapshot:d.py:3"}
    u = dict(unit(e, prov), tasks={"producer": "u1", "consumer": "u1"})
    c = [cond("frame_mismatch", "e")]
    assert S.score_composition(comp(u), c, "PAIR", {})["ECM"]["state"] == "right_reason"
    before = copy.deepcopy(u)
    cf, nulled = F.null_composition(comp(u), td)
    assert u == before
    assert [(x["path"], x["reason"]) for x in nulled] == [(f"{PO}.frame", "not_in_cited_lines")]
    assert cf["units"][0]["encoding"]["consumer"]["inputs"][0]["frame"] == "ned"
    assert S.score_composition(cf, c, "PAIR", {})["ECM"]["state"] != "right_reason"
    assert F.null_composition(None) == (None, [])


def test_assembler_units_name_the_task_behind_each_side():
    spec = {"case_id": "c", "corpus": "C1", "operation": "UPGRADE",
            "units": [{"name": "P", "role": "provider"}, {"name": "C", "role": "consumer"}],
            "inventory": [{"element": "topic:x", "sides": {"P": "provides", "C": "consumes"}},
                          {"element": "topic:missing", "sides": {"P": "provides", "C": "consumes"}}]}
    P = desc("P", [sport("topic:x", "provides")])
    C = desc("C", [sport("topic:x", "consumes")])
    e = A.edge_units(spec, P, C, "PAIR", "P", "C")
    assert [u["tasks"] for u in e] == [{"producer": "P", "consumer": "C"}] * 2
    up = A.upgrade_units(spec, desc("Pold", [sport("topic:x", "provides")]), P, C)
    assert up[0]["tasks"] == {"built": "Pold", "running": "P", "consumer": "C"}
    assert up[1]["kind"] == "pair_view" and up[1]["tasks"] == {"producer": "P", "consumer": "C", "built": "Pold"}
    assert up[2]["status"] == "unassessable_edge" and up[2]["tasks"]["producer"] == "P"


def test_main_reports_declared_sensitivities(tmp_path, monkeypatch):
    S = _c3_fixture(tmp_path, monkeypatch, ["a"])
    (tmp_path / "specs").mkdir(); (tmp_path / "ledger").mkdir()
    base = {"operation": "PAIR", "failed_conditions": [{"class": "other", "implicated_elements": []}], "units": [],
            "outcome_class": "failure", "eligible": True}
    json.dump(dict(base, case_id="X-1", corpus="C1", excerpt_based=True), open(tmp_path / "specs" / "X-1.json", "w"))
    json.dump(dict(base, case_id="X-2", corpus="C1"), open(tmp_path / "specs" / "X-2.json", "w"))
    # X-3: a DQ reliability detection whose consumer value is a library default (no token on the cited line)
    json.dump(dict(base, case_id="X-3", corpus="C1", failed_conditions=[cond("qos_reliability", "topic:/p")]),
              open(tmp_path / "specs" / "X-3.json", "w"))
    _qos_tasks(tmp_path)
    prov = {f"{PO}.qos.reliability": "snapshot:pkg/a.cpp:2", f"{PI}.qos.reliability": "snapshot:c.py:1"}
    u = dict(unit(edge(port(rel="best_effort", dur=None), port(rel="reliable", dur=None)), prov, element="topic:/p"),
             tasks={"producer": "u1", "consumer": "u4"})
    (tmp_path / "assembled").mkdir()
    json.dump({"case_id": "X-3", "corpus": "C1", "operation": "PAIR", "status": "done", "reason": None,
               "compositions": {"broken": comp(u), "resolved": None}}, open(tmp_path / "assembled" / "X-3.json", "w"))
    S.main(write=True, adjudicated=False)
    res = json.load(open(tmp_path / "results.json"))
    sens = res["sensitivity"]
    assert "X-3" in res["by_corpus"]["C1"]["primary_all_eligible"]["methods"]["DQ"]["right_reason"]["cases"]
    assert {"case_id": "X-3", "method": "DQ", "primary": "right_reason", "sensitivity": "accept"} in sens["qos_literal"]["state_changes"]
    assert sens["qos_literal"]["nulled_by_reason"] == {"no_token": 1}
    assert "X-3" not in sens["qos_literal"]["by_corpus"]["C1"]["primary_all_eligible"]["methods"]["DQ"]["right_reason"]["cases"]
    assert sens["excerpt_excluded"]["excluded"] == ["X-1"] and sens["excerpt_excluded"]["n_rows"] == 2
    assert sens["excerpt_excluded"]["by_corpus"]["C1"]["primary_all_eligible"]["n_failures"] == 2
    assert sens["qos_literal"]["declared_in_advance"] and not sens["qos_literal_named_profiles_kept"]["declared_in_advance"]
    assert sens["qos_literal"]["by_corpus"]["C1"]["primary_all_eligible"]["n_failures"] == 3
    # the fixture's frames carry no provenance, so both are nulled; a QoS detection does not depend on them
    assert sens["frame_literal"]["declared_in_advance"] and sens["frame_literal"]["nulled_by_reason"] == {"no_location": 2}
    assert "X-3" in sens["frame_literal"]["by_corpus"]["C1"]["primary_all_eligible"]["methods"]["DQ"]["right_reason"]["cases"]
    assert sens["frame_literal"]["state_changes"] == []
    assert sens["frame_literal"]["by_corpus"]["C1"]["primary_all_eligible"]["n_failures"] == 3


def test_items_refuses_to_reshuffle_a1_packets_once_records_exist(tmp_path, monkeypatch):
    import adjudicate as J
    import pytest
    monkeypatch.setattr(J, "HERE", str(tmp_path)); monkeypatch.setattr(J, "ADJ", str(tmp_path / "adjudication"))
    for d in ("specs", "scores", "ledger", "pilot"):
        (tmp_path / d).mkdir()
    json.dump({"quarantined_pilot_cases": []}, open(tmp_path / "pilot" / "PILOT_CASES.json", "w"))
    for i in range(12):
        json.dump({"case_id": f"C3-{i:03d}", "corpus": "C3", "eligible": True, "outcome_class": "failure"},
                  open(tmp_path / "specs" / f"C3-{i:03d}.json", "w"))
    J.items()
    before = _a1_ids(tmp_path)
    (tmp_path / "adjudication" / 'adj1').mkdir()
    json.dump({"item_id": before[0]["item_id"]}, open(tmp_path / "adjudication" / 'adj1' / f"{before[0]['item_id']}.json", "w"))
    J.items()                                   # unchanged inputs: allowed, A1 packets identical
    assert _a1_ids(tmp_path) == before
    json.dump({"case_id": "C3-000a", "corpus": "C3", "eligible": True, "outcome_class": "failure"},
              open(tmp_path / "specs" / "C3-000a.json", "w"))
    with pytest.raises(SystemExit):             # a new case would shift items between packets
        J.items()
    assert _a1_ids(tmp_path) == before          # and nothing was deleted


def test_adjudicated_h1_keeps_the_s1_selection_and_never_replaces(tmp_path, monkeypatch):
    S = _c3_fixture(tmp_path, monkeypatch, ["a", "b", "c", "d", "e"])
    # This selection/output fixture has no A2 findings or records.
    monkeypatch.setattr(S.AG, "load_coverage", lambda *_args: {})
    (tmp_path / "specs").mkdir(); (tmp_path / "adjudicated").mkdir()
    base = {"operation": "PAIR", "failed_conditions": [{"class": "other", "implicated_elements": []}], "units": [],
            "corpus": "C3", "outcome_class": "failure"}
    for i in (1, 2, 3, 4, 5):
        json.dump(dict(base, case_id=f"C3-{i:03d}", eligible=(i != 2)), open(tmp_path / "specs" / f"C3-{i:03d}.json", "w"))
    # S1 selection (N=3): C3-001, C3-003, C3-004. Adjudication excludes C3-003 and makes C3-002 eligible.
    json.dump({"C3-003": {"eligible": False}, "C3-002": {"eligible": True}}, open(tmp_path / "adjudicated" / "overrides.json", "w"))
    S.main(write=True, adjudicated=True)
    res = json.load(open(tmp_path / "results_adjudicated.json"))
    assert res["c3_selection"]["selected"] == ["C3-001", "C3-003", "C3-004"]
    assert res["H1"]["n_eligible_failures"] == 2                       # C3-003 dropped, nothing replaces it
    assert res["c3_adjudication_effect"] == {"selected_not_in_h1": ["C3-003"], "eligible_failures_not_selected": ["C3-002"]}
    assert not (tmp_path / "scores" / "C3-005.json").exists()            # after the S1 stop point, never pulled in


def test_fold_missed_condition_named_by_one_record_goes_to_the_third(tmp_path, monkeypatch):
    import adjudicate as J
    monkeypatch.setattr(J, "HERE", str(tmp_path)); monkeypatch.setattr(J, "ADJ", str(tmp_path / "adjudication")); monkeypatch.setattr(J, "OUT", str(tmp_path / "adjudicated"))
    (tmp_path / "specs").mkdir(); (tmp_path / "ledger").mkdir()
    json.dump({"case_id": "c", "eligible": True, "loudness": "silent_documented", "resolution": {"status": "observed"},
               "failed_conditions": [{"class": "frame_mismatch", "implicated_elements": ["topic:/t"]}]}, open(tmp_path / "specs" / "c.json", "w"))
    for who in ('adj1', 'withdrawn_google', 'adj1_repeat'):
        (tmp_path / "adjudication" / who).mkdir(parents=True)
    miss = {"class": "qos_reliability", "implicated_elements": ["topic:/t"], "quote": "q", "url": "u"}
    json.dump(dict(_adj_record("A1-c", "c"), missed_conditions=[miss]), open(tmp_path / "adjudication" / 'adj1' / "A1-c.json", "w"))
    json.dump(_adj_record("A1-c", "c"), open(tmp_path / "adjudication" / 'withdrawn_google' / "A1-c.json", "w"))
    J.fold()
    assert [s["domain"] for s in json.load(open(tmp_path / "adjudicated" / "splits.json"))] == ["missed"]
    assert json.load(open(tmp_path / "adjudicated" / "overrides.json")) == {}
    assert json.load(open(tmp_path / "adjudicated" / "kappa.json"))["missed_condition_proposals"] == {"both": 0, "adj1_only": 1, "adj2_only": 0}
    # the third adjudicator does not name it: not added, split resolved
    json.dump(_adj_record("A1-c", "c"), open(tmp_path / "adjudication" / 'adj1_repeat' / "A1-c.json", "w"))
    J.fold()
    assert json.load(open(tmp_path / "adjudicated" / "overrides.json")) == {} and json.load(open(tmp_path / "adjudicated" / "splits.json")) == []
    # the third adjudicator names the same class: added
    json.dump(dict(_adj_record("A1-c", "c"), missed_conditions=[dict(miss, quote="other quote")]),
              open(tmp_path / "adjudication" / 'adj1_repeat' / "A1-c.json", "w"))
    J.fold()
    fc = json.load(open(tmp_path / "adjudicated" / "overrides.json"))["c"]["failed_conditions"]
    assert [x["class"] for x in fc] == ["frame_mismatch", "qos_reliability"] and fc[1]["added_by"] == "adjudication"
    # both first records name it: added without the third
    json.dump(dict(_adj_record("A1-c", "c"), missed_conditions=[miss]), open(tmp_path / "adjudication" / 'withdrawn_google' / "A1-c.json", "w"))
    os.remove(tmp_path / "adjudication" / 'adj1_repeat' / "A1-c.json")
    J.fold()
    assert [x["class"] for x in json.load(open(tmp_path / "adjudicated" / "overrides.json"))["c"]["failed_conditions"]] == ["frame_mismatch", "qos_reliability"]


def test_third_splits_packets_of_ten_and_keeps_every_split_item(tmp_path, monkeypatch):
    import adjudicate as J
    monkeypatch.setattr(J, "ADJ", str(tmp_path / "adjudication")); monkeypatch.setattr(J, "OUT", str(tmp_path / "adjudicated"))
    (tmp_path / "adjudication" / "packets").mkdir(parents=True); (tmp_path / "adjudicated").mkdir()
    items_ = [{"item_id": f"A1-c{i:02d}", "kind": "A1"} for i in range(25)]
    json.dump(items_[:15], open(tmp_path / "adjudication" / "packets" / "A1_00.json", "w"))
    json.dump(items_[15:], open(tmp_path / "adjudication" / "packets" / "A1_01.json", "w"))
    json.dump([{"item": f"A1-c{i:02d}", "domain": "loudness"} for i in range(0, 25, 2)] + [{"item": "A1-c00", "domain": "class"}],
              open(tmp_path / "adjudicated" / "splits.json", "w"))
    json.dump([{"item_id": "stale"}], open(tmp_path / "adjudication" / "packets" / "A3_05.json", "w"))
    J.third()
    packets = sorted((tmp_path / "adjudication" / "packets").glob("A3_*.json"))
    assert [p.name for p in packets] == ["A3_00.json", "A3_01.json"]
    got = [it["item_id"] for p in packets for it in json.load(open(p))]
    assert got == [f"A1-c{i:02d}" for i in range(0, 25, 2)] and len(json.load(open(packets[0]))) == 10



def test_fold_adj1_only_lets_adj1_decide_alone_in_its_own_directory(tmp_path, monkeypatch):
    import adjudicate as J
    monkeypatch.setattr(J, "HERE", str(tmp_path)); monkeypatch.setattr(J, "ADJ", str(tmp_path / "adjudication")); monkeypatch.setattr(J, "OUT", str(tmp_path / "adjudicated"))
    (tmp_path / "specs").mkdir(); (tmp_path / "ledger").mkdir()
    json.dump({"case_id": "c", "eligible": True, "loudness": "silent_documented", "resolution": {"status": "observed"},
               "failed_conditions": [{"class": "frame_mismatch", "implicated_elements": ["topic:/t"]}]}, open(tmp_path / "specs" / "c.json", "w"))
    for who in ('adj1', 'withdrawn_google', 'adj1_repeat'):
        (tmp_path / "adjudication" / who).mkdir(parents=True)
    miss = {"class": "qos_reliability", "implicated_elements": ["topic:/t"], "quote": "q", "url": "u"}
    json.dump(dict(_adj_record("A1-c", "c", loud="disagree", loud_prop="unknown"), missed_conditions=[miss]),
              open(tmp_path / "adjudication" / 'adj1' / "A1-c.json", "w"))
    json.dump(_adj_record("A1-c", "c"), open(tmp_path / "adjudication" / 'withdrawn_google' / "A1-c.json", "w"))
    json.dump(_adj_record("A1-c", "c"), open(tmp_path / "adjudication" / 'adj1_repeat' / "A1-c.json", "w"))
    J.fold()                                           # declared roles: the other two keep the specification
    assert json.load(open(tmp_path / "adjudicated" / "overrides.json")) == {}
    J.fold(adj1_only=True)                             # ADJ1 alone
    assert (tmp_path / "adjudicated_adj1only" / "overrides.json").exists()
    ov_all = json.load(open(tmp_path / "adjudicated_adj1only" / "overrides.json"))
    assert set(ov_all) == {"c"}
    ov = ov_all["c"]
    assert ov["loudness"] == "unknown" and [x["class"] for x in ov["failed_conditions"]] == ["frame_mismatch", "qos_reliability"]
    assert json.load(open(tmp_path / "adjudicated_adj1only" / "splits.json")) == []
    assert not (tmp_path / "adjudicated_adj1only" / "kappa.json").exists()
    assert json.load(open(tmp_path / "adjudicated" / "overrides.json")) == {}     # the primary fold is untouched


def test_scoring_modes_write_separate_scores_and_results(tmp_path, monkeypatch):
    S = _c3_fixture(tmp_path, monkeypatch, ["a"])
    # This selection/output fixture has no A2 findings or records.
    monkeypatch.setattr(S.AG, "load_coverage", lambda *_args: {})
    (tmp_path / "specs").mkdir(); (tmp_path / "adjudicated").mkdir(); (tmp_path / "adjudicated_adj1only").mkdir()
    base = {"operation": "PAIR", "failed_conditions": [{"class": "other", "implicated_elements": []}], "units": [],
            "corpus": "C1", "outcome_class": "failure", "eligible": True}
    json.dump(dict(base, case_id="X-1"), open(tmp_path / "specs" / "X-1.json", "w"))
    json.dump({}, open(tmp_path / "adjudicated" / "overrides.json", "w"))
    json.dump({"X-1": {"eligible": False}}, open(tmp_path / "adjudicated_adj1only" / "overrides.json", "w"))
    S.main(write=True, adjudicated=False)
    S.main(write=True, adjudicated=True)
    S.main(write=True, adjudicated=True, adj_dir="adjudicated_adj1only")
    assert (tmp_path / "scores" / "X-1.json").exists() and (tmp_path / "scores_adjudicated" / "X-1.json").exists()
    assert not (tmp_path / "scores_adjudicated_adj1only" / "X-1.json").exists()   # excluded under ADJ1 alone
    assert json.load(open(tmp_path / "results.json"))["n_rows"] == 1
    assert json.load(open(tmp_path / "results_adjudicated.json"))["n_rows"] == 1
    assert json.load(open(tmp_path / "results_adjudicated_adj1only.json"))["n_rows"] == 0



def test_same_repository_stratum():
    u = lambda repo: {"name": repo or "x", "repo": repo}
    assert S.same_repository({"units": [u("https://github.com/ros/geometry2"), u("https://github.com/ros/geometry2.git/")]})
    assert not S.same_repository({"units": [u("https://github.com/ros/geometry2"), u("https://github.com/ros/common_msgs")]})
    assert not S.same_repository({"units": [u("https://github.com/a/b"), u(None)]})     # an excerpt unit has no repository
    assert not S.same_repository({"units": [u(None), u(None)]})                         # two excerpt units share nothing
    assert not S.same_repository({"units": [u("https://github.com/a/b")]})


def test_consumer_blind_ablation_widens_reads_only_on_upgrades():
    """Exploratory ablation (pre-R2 audit, 2026-09-30): the consumer-blind variant flags every changed element,
    its credit rests on the changed element's provenance alone, and it leaves the input and edge units untouched."""
    import exploratory_consumer_blind as E
    up = {"kind": "upgrade", "element": None, "status": "done",
          "encoding": {"type": "UPGRADE", "ver_delta": {"changed_fields": ["api:foo"], "consumer_reads": ["api:bar"],
                                                        "semver_old": "1.0.0", "semver_new": "1.1.0"}},
          "provenance": {"ver_delta.changed_fields[api:foo]": "snapshot:a.h:1", "ver_delta.consumer_reads[api:bar]": "snapshot:b.cpp:2",
                         "ver_delta.semver_old": "snapshot:package.xml:3", "ver_delta.semver_new": "snapshot:package.xml:3"}}
    edge = {"kind": "edge", "element": "topic:/x", "status": "done", "encoding": {"producer": {}, "consumer": {}}, "provenance": {}}
    comp = {"status": "done", "units": [up, edge]}
    conds = [{"class": "element_removed_or_renamed", "implicated_elements": ["api:foo"]}]
    assert S.score_composition(comp, conds, "UPGRADE", {})["ECM"]["state"] == "accept"
    blind, changes = E.consumer_blind(comp)
    assert changes == [{"added_reads": ["api:foo"]}]
    assert comp["units"][0]["encoding"]["ver_delta"]["consumer_reads"] == ["api:bar"]  # input not mutated
    assert blind["units"][1] == edge
    assert S.score_composition(blind, conds, "UPGRADE", {})["ECM"]["state"] == "right_reason"
    wrong = {"ver_delta.changed_fields[api:foo]": "wrong"}
    assert S.score_composition(blind, conds, "UPGRADE", wrong)["ECM"]["state"] == "unverified"
    assert E.consumer_blind(None) == (None, [])


def test_consumer_blind_breaking_only_leaves_out_additions(tmp_path):
    """Pre-R3 audit (2026-09-30): the breaking-only variant widens reads only with changed elements the
    built-against provider declares (removals, modifications), never with additions, and fails on a missing
    description rather than treating it as declaring nothing."""
    import pytest
    import exploratory_consumer_blind as E
    rd = tmp_path / "u1" / "recon"
    rd.mkdir(parents=True)
    (rd / "u1.json").write_text(json.dumps({"declares": {"api:gone": "void gone();", "api:sig": "int sig(int);",
                                                         "api:undeclared": ""}}))
    up = {"kind": "upgrade", "element": None, "status": "done", "tasks": {"built": "u1", "running": "u2", "consumer": "u3"},
          "encoding": {"type": "UPGRADE", "ver_delta": {"changed_fields": ["api:gone", "api:sig", "api:added", "api:undeclared"],
                                                        "consumer_reads": ["api:sig"], "semver_old": "1.0.0", "semver_new": "1.1.0"}},
          "provenance": {}}
    comp = {"status": "done", "units": [up]}
    blind, changes = E.consumer_blind(comp, str(tmp_path))
    assert changes == [{"added_reads": ["api:gone"]}]
    assert blind["units"][0]["encoding"]["ver_delta"]["consumer_reads"] == ["api:sig", "api:gone"]
    assert E.consumer_blind(comp)[1] == [{"added_reads": ["api:gone", "api:added", "api:undeclared"]}]
    assert blind["units"][0]["encoding"]["ver_delta"]["changed_fields"] == ["api:gone", "api:sig"]
    # an addition the consumer already references is not flagged either (R3, external review F2)
    reads_add = {"status": "done", "units": [json.loads(json.dumps(up))]}
    reads_add["units"][0]["encoding"]["ver_delta"]["consumer_reads"] = ["api:added"]
    conds = [{"class": "element_removed_or_renamed", "implicated_elements": ["api:added"]}]
    toks = lambda c: {f.get("token") for f in S.score_composition(c, conds, "UPGRADE", {})["ECM"].get("findings", [])}
    assert "api:added" in toks(reads_add)
    assert toks(E.consumer_blind(reads_add, str(tmp_path))[0]) == {"api:gone", "api:sig"}
    missing = {"status": "done", "units": [dict(up, tasks={"built": "u9"})]}
    with pytest.raises(FileNotFoundError):
        E.consumer_blind(missing, str(tmp_path))


def test_a2_evidence_of_a_control_version_finding_comes_from_the_upgrade_unit():
    """R3 (peer review M1, D1): score_control leaves a control's findings without unit_kind; the A2 evidence of a
    version-rule finding must come from the upgrade unit, not from the pair view of the same element, which
    carries no version provenance. Other findings still match their unit by kind and element."""
    import adjudicate as J
    up = {"kind": "upgrade", "element": None, "provenance": {"ver_delta.changed_fields[api:f]": "snapshot:a.h:1"}}
    pv = {"kind": "pair_view", "element": "api:f", "provenance": {}}
    edge = {"kind": "edge", "element": "topic:/x", "provenance": {"consumer.perm_requires[p]": "snapshot:m.xml:3"}}
    units = [pv, up, edge]
    assert J.unit_for_finding(units, {"rule": "field_break", "element": "api:f", "token": "api:f"}) is up
    assert J.unit_for_finding(units, {"rule": "semver_major", "element": None}) is up
    assert J.unit_for_finding(units, {"rule": "field_break", "element": "api:f", "unit_kind": "pair_view"}) is pv
    assert J.unit_for_finding(units, {"rule": "missing_permission", "element": "topic:/x"}) is edge


def test_a2_evidence_refuses_a_version_finding_without_an_upgrade_unit(tmp_path, monkeypatch):
    """R3 (external review F1): a version-rule A2 item must carry the upgrade unit's evidence; a composition that has
    only a pair view of the element is an error, not an item with null provenance."""
    import pytest
    import adjudicate as J
    (tmp_path / "assembled").mkdir()
    pv = {"kind": "pair_view", "element": "api:f", "provenance": {}, "encoding": {}}
    up = {"kind": "upgrade", "element": None, "encoding": {},
          "provenance": {"ver_delta.changed_fields[api:f]": "snapshot:a.h:1", "ver_delta.consumer_reads[api:f]": "snapshot:b.cpp:2"}}
    (tmp_path / "assembled" / "c.json").write_text(json.dumps({"compositions": {"resolved": {"units": [pv, up]}, "broken": {"units": [pv]}}}))
    monkeypatch.setattr(J, "HERE", str(tmp_path))
    f = {"rule": "field_break", "element": "api:f", "token": "api:f"}
    ev = J.evidence("c", "resolved", "ECM", f)
    assert ev["unit_kind"] == "upgrade" and all(ev["provenance"].values())
    with pytest.raises(SystemExit):
        J.evidence("c", "broken", "ECM", f)


def test_assembler_carries_permission_provenance_keyed_by_the_value_path():
    """R3 (peer review M1, D2): S2 keys a permission value by its exact path, perm_requires.values[TOKEN]; the
    assembler must carry it to the composition as consumer.perm_requires[TOKEN], or the permission rule can
    never be credited. The older key form is still read."""
    prov = {}
    d = {"perm_requires": {"state": "present", "values": ["p1", "p2"]}, "perm_grants": {"state": "absent", "values": []},
         "provenance": {"perm_requires.values[p1]": "snapshot:m.xml:3", "perm_requires[p2]": "snapshot:m.xml:4"}}
    block = A.side_block(d, "consumer", prov)
    assert block["perm_requires"] == ["p1", "p2"] and block["_states"]["perm_grants"] == "absent"
    assert prov == {"consumer.perm_requires[p1]": "snapshot:m.xml:3", "consumer.perm_requires[p2]": "snapshot:m.xml:4"}
