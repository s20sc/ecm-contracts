"""Canonicalization of free-text contract fields into comparable tokens.

The blind-reconstructed contracts describe frames/units in rich prose ("none (the
message carries no frame)", "rad, rad/s, N*m (position, velocity, effort)"). Naive
string comparison produces spurious mismatches. This module maps prose to canonical
tokens so the checker compares MEANING, not wording.

Frame semantics:
  * "per_message" / "none" -> NOT a fixed frame; the checker must NOT flag a
    frame mismatch (a tf broadcaster's per-message frame is not a static frame
    that can conflict with a consumer's per-message frame).
Units: returned as a SET of canonical unit tokens; a real mismatch requires the
  two sets to be non-empty and DISJOINT (no shared physical unit). A subset/
  superset ("rad,rad/s,N*m" vs "rad,rad/s") is therefore NOT a mismatch.
"""
from __future__ import annotations

import re
from typing import Optional, Set

_FRAME_DYNAMIC = ("per-message", "per message", "header.frame_id", "any parent",
                  "consumes", "child_frame_id is the child", "frame tree", "parent->child",
                  "parent -> child", "argv")
_FRAME_NONE = ("no frame", "carries no frame", "has no frame", "by name", "name field")


def canon_frame(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    t = s.lower()
    if any(k in t for k in _FRAME_DYNAMIC):
        return "per_message"
    if t.strip() == "none" or any(k in t for k in _FRAME_NONE):
        return "none"
    for tok in ("base_footprint", "base_link", "base_scan", "gyro_link",
                "odom", "map", "world", "enu", "ned"):
        if tok in t:
            return tok
    # fall back to the first frame-like word
    m = re.search(r"[a-z][a-z0-9_]+", t)
    return m.group() if m else None


_UNIT_PATTERNS = [
    (r"\bm\s*/\s*s\b|meters?\s+per\s+second", "m_s"),
    (r"\brad\s*/\s*s\b|radians?\s+per\s+second", "rad_s"),
    (r"\bdeg\s*/\s*s\b", "deg_s"),
    (r"\bn\s*[*·.]?\s*m\b|newton[- ]?met", "Nm"),
    (r"\bquaternion\b", "quat"),
    (r"\brad\b|radians?\b", "rad"),
    (r"\bdeg(ree)?s?\b", "deg"),
    (r"\bcm\b|centimet", "cm"),
    (r"\bmm\b|millimet", "mm"),
    (r"\bm\b|meters?\b", "m"),
]


def canon_units(s: Optional[str]) -> Set[str]:
    if not s:
        return set()
    t = s.lower()
    found = set()
    for pat, tok in _UNIT_PATTERNS:
        if re.search(pat, t):
            found.add(tok)
    # collapse rad+rad_s etc. are distinct tokens on purpose (angle vs angular rate)
    return found


# unit pairs that are genuinely INCOMPATIBLE if one is expected and the other given
# (same physical quantity, different scale/convention).
_UNIT_CONFLICTS = [
    {"rad", "deg"}, {"rad_s", "deg_s"}, {"m", "cm"}, {"m", "mm"},
]


def units_conflict(a: Set[str], b: Set[str]) -> bool:
    """True iff a and b denote the SAME quantity with incompatible units.

    A subset/superset relation is NOT a conflict. Only an explicit scale/convention
    clash (rad vs deg, m vs cm) counts.
    """
    if not a or not b:
        return False
    for pair in _UNIT_CONFLICTS:
        if (a & pair) and (b & pair) and not (a & pair) == (b & pair):
            return True
    return False
