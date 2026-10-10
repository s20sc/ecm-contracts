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
    assert agg["pairwise"]["all_failures:ECM_vs_NT"]["structurally_nested"] and agg["pairwise"]["all_failures:ECM_vs_NT"]["mcnemar_exact_p"] is None
    assert agg["pairwise"]["all_failures:DI_vs_DQ"]["mcnemar_exact_p"] is not None
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
    for d in ("specs", "scores", "assembled", "ledger"):
        (tmp_path / d).mkdir()
    prov = {"producer.outputs[0].definition_id": "snapshot:a.msg:1 | x", "consumer.inputs[0].definition_id": "built: snapshot:b.msg:1 | y"}
    units = [{"kind": "pair_view", "element": e, "status": "done", "encoding": {}, "provenance": prov} for e in ("msg:p/M", "field:p/M.a", "field:p/M.b")]
    json.dump({"case_id": "c", "compositions": {"broken": {"units": units}}}, open(tmp_path / "assembled" / "c.json", "w"))
    findings = [{"rule": "di_definition_mismatch", "element": e, "unit_kind": "pair_view"} for e in ("msg:p/M", "field:p/M.a", "field:p/M.b")]
    score = {"case_id": "c", "broken": {"DI": {"state": "right_reason", "findings": findings,
             "matched": [{"rule": "di_definition_mismatch", "element": f["element"]} for f in findings]}}, "resolved": {}}
    json.dump(score, open(tmp_path / "scores" / "c.json", "w"))
    monkeypatch.setattr(J, "METHODS", ["DI"])
    J.items()
    a2 = json.load(open(tmp_path / "adjudication" / "packets" / "A2_00.json"))
    assert len(a2) == 1 and len(a2[0]["also_covers"]) == 2


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

