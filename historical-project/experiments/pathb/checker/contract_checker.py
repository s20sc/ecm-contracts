"""ECM Contract checker + strengthened baselines (frozen, content-hash-pinned).

SYSTEM UNDER TEST for Path B (real-bug prediction) and Path A (runtime outcome).
Frozen (git SHA pinned) BEFORE any contract is reconstructed, so the checker
cannot be fitted to the cases.

Architecture (deliberate, for honesty): every applicable check runs once and
produces a finding tagged with a `check_type`. A METHOD is simply a *filter* over
allowed check_types. This makes the strongest baseline non-strawman and makes the
two adversarial analyses computable directly:
  * Beh-non-QoS marginal = ECM findings whose check_type is a Beh check the
    QoS-aware baseline does NOT include (rate_starvation, precondition).
  * Ver-Sig-disjoint     = Ver findings on cases the schema-only (type) baseline
    does NOT already flag.

A module contract is a plain dict (parsed from YAML) over six dimensions:
Sig (msg type / frame / units), Beh (QoS, rate, pre/postconditions),
Res (exclusive locks), Perm (permission boundaries / limits),
Rec (recovery semantics), Ver (interface hash + semver + changed fields).

No ROS dependency: operates on declared contracts only.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Sequence, Set

from canonical import canon_frame, canon_units, units_conflict


class Severity(Enum):
    CRITICAL = "critical"   # composition will fail -> REJECT
    WARNING = "warning"     # conditional -> ACCEPT_WITH_CONDITIONS


@dataclass(frozen=True)
class Incompatibility:
    dimension: str       # Sig | Beh | Res | Perm | Rec | Ver
    check_type: str      # stable key used for method filtering + disjoint analysis
    severity: Severity
    detail: str


# Which dimension each check_type belongs to (single source of truth).
CHECK_DIM: Dict[str, str] = {
    "type_mismatch": "Sig", "frame_mismatch": "Sig", "unit_mismatch": "Sig",
    "qos_reliability": "Beh", "qos_durability": "Beh", "qos_deadline": "Beh",
    "rate_starvation": "Beh", "precondition": "Beh",
    "lock_conflict": "Res", "resource_unmet": "Res",
    "missing_permission": "Perm", "limit_exceeded": "Perm",
    "strategy_conflict": "Rec", "field_break": "Ver", "semver_major": "Ver",
}

# QoS sub-checks of Beh — the part a strong schema+QoS baseline ALSO has.
_BEH_QOS = {"qos_reliability", "qos_durability", "qos_deadline"}
# Beh checks a schema+QoS baseline structurally CANNOT express (Beh-disjoint).
_BEH_NONQOS = {"rate_starvation", "precondition"}

_TYPE_PROMOTIONS: Dict[str, Set[str]] = {
    "geometry_msgs/Pose2D": {"geometry_msgs/Pose", "geometry_msgs/PoseStamped"},
}


def _types_compatible(out_type: str, in_type: str) -> bool:
    return out_type == in_type or in_type in _TYPE_PROMOTIONS.get(out_type, set())


def _semver_tuple(v: str) -> tuple:
    parts = (v or "0.0.0").split("+")[0].split("-")[0].split(".")
    out: List[int] = []
    for p in parts[:3]:
        try:
            out.append(int(p))
        except ValueError:
            out.append(0)
    while len(out) < 3:
        out.append(0)
    return tuple(out)


def _pick(items: Sequence[dict], role: Optional[str]) -> Optional[dict]:
    if not items:
        return None
    if role is not None:
        for it in items:
            if it.get("role") == role:
                return it
    return items[0]


# --------------------------------------------------------------------------- #
# Checks. Each appends Incompatibility(check_type=...) findings.               #
# --------------------------------------------------------------------------- #
def _sig(out: dict, inp: dict, f: List[Incompatibility]) -> None:
    ot, it = out.get("msg_type"), inp.get("msg_type")
    if ot and it and not _types_compatible(ot, it):
        f.append(Incompatibility("Sig", "type_mismatch", Severity.CRITICAL,
                                 f"producer {ot} vs consumer {it}"))
    # frames compared by canonical token; per-message/none frames are NOT fixed
    # frames and cannot conflict (avoids prose-comparison false positives).
    ofc, ifc = canon_frame(out.get("frame")), canon_frame(inp.get("frame"))
    if ofc and ifc and ofc not in ("per_message", "none") \
            and ifc not in ("per_message", "none") and ofc != ifc:
        f.append(Incompatibility("Sig", "frame_mismatch", Severity.CRITICAL,
                                 f"frame '{ofc}' != '{ifc}'"))
    # units compared as canonical sets; only a real scale/convention clash
    # (rad vs deg, m vs cm) is a mismatch — subset/superset is compatible.
    ou, iu = canon_units(out.get("units")), canon_units(inp.get("units"))
    if units_conflict(ou, iu):
        f.append(Incompatibility("Sig", "unit_mismatch", Severity.CRITICAL,
                                 f"units {sorted(ou)} vs {sorted(iu)}"))


def _beh(out: dict, inp: dict, f: List[Incompatibility]) -> None:
    oq, iq = out.get("qos", {}) or {}, inp.get("qos", {}) or {}
    if oq.get("reliability") == "best_effort" and iq.get("reliability") == "reliable":
        f.append(Incompatibility("Beh", "qos_reliability", Severity.CRITICAL,
                                 "BEST_EFFORT pub vs RELIABLE sub -> no delivery"))
    if oq.get("durability") == "volatile" and iq.get("durability") == "transient_local":
        f.append(Incompatibility("Beh", "qos_durability", Severity.CRITICAL,
                                 "VOLATILE pub vs TRANSIENT_LOCAL sub -> late-joiner starves"))
    idl, rate = iq.get("deadline_ms"), out.get("rate_hz")
    if idl and rate and (1000.0 / rate) > idl:
        f.append(Incompatibility("Beh", "qos_deadline", Severity.CRITICAL,
                                 f"period {1000.0/rate:.0f}ms > deadline {idl}ms"))
    minr = inp.get("min_rate_hz")
    if rate and minr and rate < minr:
        f.append(Incompatibility("Beh", "rate_starvation", Severity.CRITICAL,
                                 f"pub {rate}Hz < required {minr}Hz"))
    # NOTE: free-text pre/postcondition matching was REMOVED — the blind contracts
    # express them in prose, so literal comparison over-fires (unreliable). Beh is
    # scored on the groundable numeric/enum properties: QoS + refresh-rate.


def _res(a: dict, b: dict, f: List[Incompatibility]) -> None:
    for r in sorted(set(a.get("exclusive", []) or []) & set(b.get("exclusive", []) or [])):
        f.append(Incompatibility("Res", "lock_conflict", Severity.CRITICAL,
                                 f"both claim exclusive '{r}'"))


def _perm(producer: dict, consumer: dict, f: List[Incompatibility]) -> None:
    grants = set(producer.get("perm_grants", []) or []) | set(consumer.get("perm_grants", []) or [])
    for p in consumer.get("perm_requires", []) or []:
        if p not in grants:
            f.append(Incompatibility("Perm", "missing_permission", Severity.CRITICAL,
                                     f"permission '{p}' not granted"))
    limits, req = producer.get("perm_limits", {}) or {}, consumer.get("perm_limits", {}) or {}
    for k, v in req.items():
        if k in limits and v > limits[k]:
            f.append(Incompatibility("Perm", "limit_exceeded", Severity.CRITICAL,
                                     f"{k}={v} exceeds limit {limits[k]}"))


_REC_CONFLICTS = {frozenset({"retry", "retreat"}), frozenset({"retry", "abort"})}


def _rec(a: dict, b: dict, f: List[Incompatibility]) -> None:
    ra, rb = a.get("recovery"), b.get("recovery")
    if ra and rb and ra != rb and frozenset({ra, rb}) in _REC_CONFLICTS:
        f.append(Incompatibility("Rec", "strategy_conflict", Severity.WARNING,
                                 f"recovery '{ra}' vs '{rb}'"))


def _ver(old: dict, new: dict, consumer_reads: Optional[Sequence[str]], f: List[Incompatibility]) -> None:
    hash_changed = old.get("interface_hash") != new.get("interface_hash")
    major = _semver_tuple(new.get("semver", "0"))[0] > _semver_tuple(old.get("semver", "0"))[0]
    if major:
        # semver-only baseline reasons with THIS signal alone.
        f.append(Incompatibility("Ver", "semver_major", Severity.CRITICAL,
                                 "major semver bump declared breaking"))
    for fld in sorted(set(new.get("changed_fields", []) or []) & set(consumer_reads or [])):
        f.append(Incompatibility("Ver", "field_break", Severity.CRITICAL,
                                 f"changed field '{fld}' is read by a consumer"))


def all_findings(case: dict) -> List[Incompatibility]:
    """Run EVERY applicable check once; methods filter this list afterwards."""
    f: List[Incompatibility] = []
    ctype = case.get("type", "PAIR")
    if ctype == "UPGRADE":
        _ver(case["old"], case["new"], case.get("consumer_reads"), f)
        return f
    producer, consumer = case["producer"], case["consumer"]
    out = _pick(producer.get("outputs", []), case.get("edge", {}).get("out_role"))
    inp = _pick(consumer.get("inputs", []), case.get("edge", {}).get("in_role"))
    if out is not None and inp is not None:
        _sig(out, inp, f)
        _beh(out, inp, f)
    _res(producer, consumer, f)
    _perm(producer, consumer, f)
    if ctype == "CONCURRENT":
        _rec(producer, consumer, f)
    return f


@dataclass(frozen=True)
class Method:
    name: str
    checks: Set[str]   # allowed check_types


# ECM-full = every check. Baselines are honest subsets (R2 anti-strawman fix):
#  schema-only  = pure rosidl message-type matching ONLY (no frame/units/QoS).
#  schema+QoS   = message-type + full DDS QoS compatibility (what ROS2 gives free).
#  semver-only  = trusts the version number (flags only a declared major bump).
ECM_FULL = Method("ECM-full", set(CHECK_DIM.keys()))
SCHEMA_ONLY = Method("schema-only", {"type_mismatch"})
SCHEMA_QOS = Method("schema+QoS", {"type_mismatch"} | _BEH_QOS)
SEMVER_ONLY = Method("semver-only", {"semver_major"})
ALL_METHODS = [ECM_FULL, SCHEMA_ONLY, SCHEMA_QOS, SEMVER_ONLY]


def method_findings(findings: List[Incompatibility], method: Method) -> List[Incompatibility]:
    return [x for x in findings if x.check_type in method.checks]


def predicts(case: dict, method: Method, findings: Optional[List[Incompatibility]] = None) -> dict:
    """Whether `method` predicts the case's documented failure, and how."""
    all_f = all_findings(case) if findings is None else findings
    mf = method_findings(all_f, method)
    dims_hit = {x.dimension for x in mf}
    gold = case.get("gold_dimension")
    gold_set = set(gold) if isinstance(gold, (list, set)) else {gold}
    return {
        "flagged": len(mf) > 0,
        "dims_hit": sorted(dims_hit),
        "attributed": bool(dims_hit & gold_set),
        "check_types": sorted({x.check_type for x in mf}),
    }
