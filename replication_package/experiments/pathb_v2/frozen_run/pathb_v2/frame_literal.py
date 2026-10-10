"""Declared sensitivity analysis: frame values not written in the cited lines (DEVIATIONS.md, 2026-09-29).

The S2 instructions ask for a port's frame "exactly as the code declares or hard-codes it", with the
tokens `per_message` and `none` for run-time and non-spatial frames. Some runs wrote a description
instead ("ENU (ROS input) -> FCU frame via UAS::transform_frame_enu_ned"). The frozen checker's
canon_frame() maps any string to a frame token by substring, so a description can yield a frame
(`enu`, `ned`, or the first word) that no line of the unit names.

A frame value in an assembled unit is kept if it is `per_message` or `none`, or if it appears
verbatim in a line that its provenance cites, read from the unit's own task workspace (the same
reader as qos_literal.cited_text). Every other frame value is set to null, with the reason
`not_in_cited_lines` or `no_location` (the provenance cites no readable line).
"""
from __future__ import annotations

import copy
import os
from typing import List, Optional, Tuple

import qos_literal as Q

TOKENS = ("per_message", "none")


def classify(value, task_id: Optional[str], prov: Optional[str], tasks_dir: Optional[str] = None) -> str:
    """`literal` (or `token`), or the reason the value is nulled."""
    if value in TOKENS:
        return "token"
    text, _ = Q.cited_text(task_id, prov, tasks_dir)
    if text is None:
        return "no_location"
    return "literal" if str(value) in text else "not_in_cited_lines"


def null_unit(unit: dict, tasks_dir: Optional[str] = None) -> Tuple[dict, List[dict]]:
    """Copy of an assembled unit with non-literal frame values set to null, and the nulled values."""
    if unit.get("status") != "done" or unit.get("kind") not in ("edge", "pair_view"):
        return unit, []
    u = copy.deepcopy(unit)
    nulled = []
    for side, key in (("producer", "outputs"), ("consumer", "inputs")):
        for i, p in enumerate((u["encoding"].get(side) or {}).get(key) or []):
            v = p.get("frame")
            if v is None:
                continue
            path = f"{side}.{key}[{i}].frame"
            reason = classify(v, Q._task_of(u, side), u["provenance"].get(path), tasks_dir)
            if reason in ("literal", "token"):
                continue
            p["frame"] = None
            nulled.append({"path": path, "value": v, "reason": reason, "task_id": Q._task_of(u, side),
                           "element": u.get("element")})
    return u, nulled


def null_composition(comp: Optional[dict], tasks_dir: Optional[str] = None) -> Tuple[Optional[dict], List[dict]]:
    if comp is None:
        return None, []
    c = dict(comp)
    units, nulled = [], []
    for unit in comp.get("units") or []:
        nu, n = null_unit(unit, tasks_dir)
        units.append(nu)
        nulled.extend(n)
    c["units"] = units
    return c, nulled
