"""Baselines for Path B v2.1 (frozen with PROTOCOL.md, Section 8).

Each baseline reads one assembled edge encoding (the same one the frozen ECM checker
reads; for UPGRADE cases the pair view built by assemble.py) and returns finding
instances: dicts with `rule`, `element` (the edge role) and `values`.

  NT  nominal type        : msg_type differ and the checker's own promotion table
                            does not relate them (shared ECM nominal rule on PAIR/CONCURRENT edges)
  DI  definition identity : both ports carry a definition_id of the same algorithm and
                            kind, values differ; the ROS 1 wildcard "*" is compatible
  DQ  definition + QoS    : DI plus DDS request-offer rules for reliability, durability
                            and deadline (offered deadline_ms <= requested deadline_ms)
  SV  declared semver     : UPGRADE whose provider major version increased (both
                            versions present); reported as a declared signal only

Port selection is the checker's (`_pick`), so every method compares the same pair.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Sequence

_CHECKER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pathb", "checker")
if _CHECKER not in sys.path:
    sys.path.insert(0, _CHECKER)
from contract_checker import _pick, _types_compatible  # noqa: E402


def _ports(case: dict):
    if case.get("type") == "UPGRADE":
        return None, None
    edge = case.get("edge", {}) or {}
    out = _pick((case.get("producer") or {}).get("outputs", []) or [], edge.get("out_role"))
    inp = _pick((case.get("consumer") or {}).get("inputs", []) or [], edge.get("in_role"))
    return out, inp


def _finding(rule: str, element: Optional[str], **values) -> dict:
    return {"rule": rule, "element": element, "values": values}


def _major(v: Optional[str]) -> Optional[int]:
    if not v:
        return None
    head = str(v).split("+")[0].split("-")[0].split(".")[0]
    try:
        return int(head)
    except ValueError:
        return None


def nominal_type(case: dict) -> List[dict]:
    out, inp = _ports(case)
    if out and inp and out.get("msg_type") and inp.get("msg_type") \
            and not _types_compatible(out["msg_type"], inp["msg_type"]):
        return [_finding("nt_type_mismatch", inp.get("role"), producer=out["msg_type"], consumer=inp["msg_type"])]
    return []


def _did(port: dict) -> Optional[dict]:
    d = port.get("definition_id")
    if isinstance(d, dict) and d.get("value"):
        return d
    return None


def definition_identity(case: dict) -> List[dict]:
    out, inp = _ports(case)
    if not (out and inp):
        return []
    a, b = _did(out), _did(inp)
    if not (a and b):
        return []
    if a.get("algorithm") != b.get("algorithm") or a.get("kind") != b.get("kind"):
        return []  # not comparable; reported by the scorer as such
    if "*" in (a["value"], b["value"]):
        return []  # ROS 1 wildcard subscriber/publisher
    if a["value"] != b["value"]:
        return [_finding("di_definition_mismatch", inp.get("role"), producer=a["value"], consumer=b["value"],
                         algorithm=a.get("algorithm"))]
    return []


def definition_and_qos(case: dict) -> List[dict]:
    findings = definition_identity(case)
    out, inp = _ports(case)
    if out and inp:
        oq, iq = out.get("qos") or {}, inp.get("qos") or {}
        if oq.get("reliability") == "best_effort" and iq.get("reliability") == "reliable":
            findings.append(_finding("dq_qos_reliability", inp.get("role"), producer="best_effort", consumer="reliable"))
        if oq.get("durability") == "volatile" and iq.get("durability") == "transient_local":
            findings.append(_finding("dq_qos_durability", inp.get("role"), producer="volatile", consumer="transient_local"))
        od, idl = oq.get("deadline_ms"), iq.get("deadline_ms")
        if od is not None and idl is not None and od > idl:
            findings.append(_finding("dq_qos_deadline", inp.get("role"), offered_ms=od, requested_ms=idl))
    return findings


def declared_semver(case: dict) -> List[dict]:
    if case.get("type") != "UPGRADE":
        return []
    vd = case.get("ver_delta") or {}
    old, new = _major(vd.get("semver_old")), _major(vd.get("semver_new"))
    if old is not None and new is not None and new > old:
        return [_finding("sv_major", None, old=vd.get("semver_old"), new=vd.get("semver_new"))]
    return []


BASELINES: Dict[str, callable] = {
    "NT": nominal_type,
    "DI": definition_identity,
    "DQ": definition_and_qos,
    "SV": declared_semver,
}

# Historical protocol classification, not a universal inclusion theorem.
# NT uses the shared nominal rule on PAIR/CONCURRENT edges, but UPGRADE pair views
# reach NT while ECM runs only its version rule. NT inclusion is observed in the
# 371 completed nonpilot upgrade pair views, not guaranteed for arbitrary upgrades.
# SV shares the raw semver-major rule. Current inference exclusions are defined
# separately in scoring.py; the historical PROTOCOL.md remains unchanged.
NESTED_IN_ECM = {"NT", "SV"}

# Triggering-value paths per baseline rule, relative to the edge encoding.
def trigger_paths(rule: str, po: str, pi: str) -> List[str]:
    return {
        "nt_type_mismatch": [f"{po}.msg_type", f"{pi}.msg_type"],
        "di_definition_mismatch": [f"{po}.definition_id", f"{pi}.definition_id"],
        "dq_qos_reliability": [f"{po}.qos.reliability", f"{pi}.qos.reliability"],
        "dq_qos_durability": [f"{po}.qos.durability", f"{pi}.qos.durability"],
        "dq_qos_deadline": [f"{po}.qos.deadline_ms", f"{pi}.qos.deadline_ms"],
        "sv_major": ["ver_delta.semver_old", "ver_delta.semver_new"],
    }[rule]
