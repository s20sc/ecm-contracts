"""Declared sensitivity analysis: QoS values without a literal token (DEVIATIONS.md, 2026-09-27).

For reliability and durability, a QoS value is kept only if a line that its provenance cites, read from the
unit's own task workspace (`s2_work/tasks/<task_id>/snapshot/<path>` or, for an excerpt task,
`artifact.txt`), names that value literally. Every other QoS value is set to null. The check reads
the cited lines, never the provenance text, because S2 wrote the library default it looked up
(for example `RMW_QOS_POLICY_DURABILITY_VOLATILE`) into its explanation.

Each nulled value is recorded with a reason: `named_profile` (the cited lines select a named
profile such as `SensorDataQoS()` or `qos_profile_parameters`, whose value the library defines),
`no_token` (the cited lines hold no QoS token for the value, i.e. a library default),
`no_location` (the provenance cites no readable line). The breakdown is reported; the declared
rule treats all three alike.

Frozen limitation: the deadline branch checks only for the token "deadline", not the
encoded numeric value or units. No deadline values occur in the 2,144 nonpilot port
records. This branch is unexercised in the reported sensitivity and does not validate
deadline values. It is retained unchanged as part of the historical implementation.
"""
from __future__ import annotations

import copy
import os
import re
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, "s2_work", "tasks")

FIELDS = ("reliability", "durability", "deadline_ms")
_LINES = r"(\d+(?:\s*[-–]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–]\s*\d+)?)*)"
_SNAP = re.compile(r"snapshot:([^\s:|`'\"(),;]+):" + _LINES)
# A bare ":<lines>" after a space or "(" continues the last snapshot path ("...cpp:338 (...) and :70").
_REF = re.compile(r"snapshot:([^\s:|`'\"(),;]+):" + _LINES + r"|(?<=[\s(]):" + _LINES)
_ART = re.compile(r"artifact\.txt:" + _LINES)

# One pattern per (policy, value): the C macro, the rclcpp enum and builder, the rclpy enum, and a
# YAML or keyword assignment. Named profiles are deliberately absent (see NAMED_PROFILE).
TOKENS = {
    ("reliability", "reliable"): r"RELIABILITY_RELIABLE\b|ReliabilityPolicy(?:\.|::)(?:RELIABLE|Reliable)\b"
                                 r"|\.reliable\(\)|\breliability\s*[:=]\s*['\"]?reliable\b",
    ("reliability", "best_effort"): r"RELIABILITY_BEST_EFFORT\b|ReliabilityPolicy(?:\.|::)(?:BEST_EFFORT|BestEffort)\b"
                                    r"|\.best_effort\(\)|\breliability\s*[:=]\s*['\"]?best_effort\b",
    ("durability", "volatile"): r"DURABILITY_VOLATILE\b|DurabilityPolicy(?:\.|::)(?:VOLATILE|Volatile)\b"
                                r"|\.durability_volatile\(\)|\bdurability\s*[:=]\s*['\"]?volatile\b",
    ("durability", "transient_local"): r"DURABILITY_TRANSIENT_LOCAL\b|DurabilityPolicy(?:\.|::)(?:TRANSIENT_LOCAL|TransientLocal)\b"
                                       r"|\.transient_local\(\)|\bdurability\s*[:=]\s*['\"]?transient_local\b",
}
# In an excerpt artifact the source is prose (a report or a quoted command), so the value's words count.
PROSE = {
    ("reliability", "reliable"): r"(?<!un)\breliable\b",
    ("reliability", "best_effort"): r"\bbest[ _-]?effort\b",
    ("durability", "volatile"): r"\bvolatile\b",
    ("durability", "transient_local"): r"\btransient[ _-]?local\b",
}
DEADLINE = r"\bdeadline\b"
NAMED_PROFILE = re.compile(r"\b(?:SensorDataQoS|SystemDefaultsQoS|ServicesQoS|ParametersQoS|ParameterEventsQoS|ClockQoS"
                           r"|RosoutQoS|BestAvailableQoS|QoSPresetProfiles|(?:rmw_)?qos_profile_[a-z_]+)\b")


def _line_ranges(spec: str) -> List[Tuple[int, int]]:
    out = []
    for part in spec.split(","):
        a, _, b = part.replace("–", "-").partition("-")
        a = int(a.strip())
        out.append((a, int(b.strip()) if b.strip() else a))
    return out


def _read_lines(path: str, spec: str) -> Optional[str]:
    if not os.path.isfile(path):
        return None
    lines = open(path, errors="replace").read().splitlines()
    return "\n".join("\n".join(lines[a - 1:b]) for a, b in _line_ranges(spec) if a >= 1)


def cited_text(task_id: Optional[str], prov: Optional[str], tasks_dir: Optional[str] = None) -> Tuple[Optional[str], bool]:
    """Text of every line the provenance cites inside the task workspace, and whether any cited
    location is the excerpt artifact. None when no cited location can be read."""
    if not task_id or not prov:
        return None, False
    base = os.path.realpath(os.path.join(tasks_dir or TASKS, task_id))
    snap = os.path.join(base, "snapshot")
    parts, from_artifact = [], False
    refs, last = [], None
    for m in _REF.finditer(prov):
        if m.group(1):
            last = m.group(1)
            refs.append((last, m.group(2)))
        elif last is not None:
            refs.append((last, m.group(3)))
    for rel, spec in refs:
        f = os.path.realpath(os.path.join(snap, rel))
        if not f.startswith(snap + os.sep):
            continue  # a location outside the unit's own snapshot is not evidence
        t = _read_lines(f, spec)
        if t is not None:
            parts.append(t)
    for spec in _ART.findall(prov):
        t = _read_lines(os.path.join(base, "artifact.txt"), spec)
        if t is not None:
            parts.append(t)
            from_artifact = True
    return ("\n".join(parts) if parts else None), from_artifact


def classify(field: str, value, task_id: Optional[str], prov: Optional[str], tasks_dir: Optional[str] = None) -> str:
    """`literal`, or the reason the value is nulled: `named_profile`, `no_token`, `no_location`."""
    text, from_artifact = cited_text(task_id, prov, tasks_dir)
    if text is None:
        return "no_location"
    if field == "deadline_ms":
        pat = DEADLINE
    else:
        pat = TOKENS.get((field, value))
        if pat is None:
            return "no_token"
        if from_artifact:
            pat = pat + "|" + PROSE[(field, value)]
    if re.search(pat, text, flags=re.I if from_artifact else 0):
        return "literal"
    return "named_profile" if NAMED_PROFILE.search(text) else "no_token"


def _task_of(unit: dict, side: str) -> Optional[str]:
    return (unit.get("tasks") or {}).get(side)


def null_unit(unit: dict, keep_named_profiles: bool = False, tasks_dir: Optional[str] = None) -> Tuple[dict, List[dict]]:
    """Copy of an assembled unit with non-literal QoS values set to null, and the nulled values.
    `keep_named_profiles` gives the exploratory variant that was not declared in advance."""
    if unit.get("status") != "done" or unit.get("kind") not in ("edge", "pair_view"):
        return unit, []
    u = copy.deepcopy(unit)
    nulled = []
    for side, key in (("producer", "outputs"), ("consumer", "inputs")):
        for i, p in enumerate((u["encoding"].get(side) or {}).get(key) or []):
            q = p.get("qos") or {}
            for fld in FIELDS:
                v = q.get(fld)
                if v is None:
                    continue
                path = f"{side}.{key}[{i}].qos.{fld}"
                reason = classify(fld, v, _task_of(u, side), u["provenance"].get(path), tasks_dir)
                if reason == "literal" or (keep_named_profiles and reason == "named_profile"):
                    continue
                q[fld] = None
                nulled.append({"path": path, "value": v, "reason": reason, "task_id": _task_of(u, side),
                               "element": u.get("element")})
    return u, nulled


def null_composition(comp: Optional[dict], keep_named_profiles: bool = False,
                     tasks_dir: Optional[str] = None) -> Tuple[Optional[dict], List[dict]]:
    if comp is None:
        return None, []
    c = dict(comp)
    units, nulled = [], []
    for unit in comp.get("units") or []:
        nu, n = null_unit(unit, keep_named_profiles, tasks_dir)
        units.append(nu)
        nulled.extend(n)
    c["units"] = units
    return c, nulled
