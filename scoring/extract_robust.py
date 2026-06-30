"""Extract integration-relevant Path-B cases from the ROBUST dataset.

Adversarial fix #1 (blind, third-party labeling): we assign each bug's ECM gold
dimension(s) by mapping ROBUST's OWN third-party `fault-codes` taxonomy through a
FROZEN, published crosswalk defined by the MEANING of each fault code — never by
whether the ECM checker happens to flag the case. The crosswalk below is the
labeling instrument; it is committed before any checker is run on the cases.

Usage: python3 extract_robust.py <robust_repo_dir> <out_cases.json>
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import sys

import yaml

# --- FROZEN crosswalk: ROBUST third-party fault-code -> ECM dimension(s) -----
# Include = the code denotes a cross-component integration/composition/version
# concern an inter-module contract could reason about. Exclude = single-module
# logic or pure build-time. Defined by code semantics, blind to checker outcomes.
CROSSWALK = {
    # version evolution -> Ver
    "EVOLUTION:PACKAGE": ["Ver"], "EVOLUTION:LIBRARY": ["Ver"],
    "EVOLUTION:DEPRECATION": ["Ver"], "EVOLUTION:API": ["Ver"],
    "EVOLUTION:MESSAGE": ["Ver", "Sig"], "EVOLUTION:PARAMETER": ["Ver"],
    # NOTE: BDO:DEPENDENCY is deliberately EXCLUDED — it is a build/packaging
    # (catkin/rosdep) dependency concern, not a runtime composition/version
    # contract ECM reasons about. Including it inflated Ver with build-time noise.
    # wiring / types / frames -> Sig
    "CONFIG:NAMESPACE": ["Sig"], "CONFIG:REMAPPING": ["Sig"],
    "PROGRAMMING:DATATYPE": ["Sig"],
    "MODELS:ROBOT": ["Sig"], "MODELS:TRANSFORMATIONS": ["Sig"],
    "MODELS:WORLD": ["Sig"], "MODELS:SENSORS": ["Sig"],
    # behavior / timing / params / broken contract -> Beh
    "CONFIG:PARAM": ["Beh"], "CONFIG:PARAMETER": ["Beh"], "CONFIG:OTHER": ["Beh"],
    "CONCURRENCY:NO-SYNC": ["Beh"], "CONCURRENCY:TIMING": ["Beh"],
    "CONCURRENCY:RACE": ["Beh"], "CONCURRENCY:ORDER": ["Beh"],
    "PROGRAMMING:BROKEN-CONTRACT": ["Beh"],
    # system resources -> Res
    "SYSTEMS:RESOURCES": ["Res"], "SYSTEMS:NETWORK": ["Res"], "SYSTEMS:OTHER": ["Res"],
}
# classification-string hashtag fallback (older records use `classification` not fault-codes)
TAG_MAP = {
    "EVOLUTION": ["Ver"], "CONFIGURATION": ["Beh"],
    "CONCURRENCY": ["Beh"], "MODELS": ["Sig"],
}
# explicitly excluded codes (single-module logic, pure build, or build-dependency).
# BDO:DEPENDENCY excluded: build/packaging dependency, not a runtime contract.
EXCLUDE = {"BDO:BUILD", "BDO:ORCHESTRATION", "BDO:DEPENDENCY"}


def fault_codes(d: dict) -> list:
    fc = d.get("fault-codes") or d.get("fault_codes")
    if isinstance(fc, dict):
        return list(fc.keys())
    if isinstance(fc, list):
        return [str(x) for x in fc]
    return []


def class_tags(d: dict) -> list:
    c = d.get("classification")
    if isinstance(c, str):
        return re.findall(r"#([A-Z\-]+)", c)
    return []


def gold_dims(codes: list, tags: list) -> list:
    dims: list = []
    for c in codes:
        if c in EXCLUDE:
            continue
        for x in CROSSWALK.get(c, []):
            if x not in dims:
                dims.append(x)
    if not dims:  # fallback to classification hashtags
        for t in tags:
            for x in TAG_MAP.get(t, []):
                if x not in dims:
                    dims.append(x)
    return dims


def main() -> None:
    repo, out = sys.argv[1], sys.argv[2]
    cases, dist = [], collections.Counter()
    total = integ = 0
    for f in glob.glob(os.path.join(repo, "**/*.bug"), recursive=True):
        try:
            d = yaml.safe_load(open(f))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        total += 1
        codes, tags = fault_codes(d), class_tags(d)
        dims = gold_dims(codes, tags)
        if not dims:
            continue
        integ += 1
        for x in dims:
            dist[x] += 1
        bug = d.get("bug", {}) or {}
        fix = d.get("fix", {}) or {}
        cases.append({
            "case_id": "robust_" + str(d.get("id") or os.path.basename(f)).strip(),
            "system": d.get("system"),
            "title": d.get("title"),
            "description": (d.get("description") or "")[:600],
            "issue_url": bug.get("issue"),
            "fix_commits": fix.get("commits"),
            "package": bug.get("package"),
            "subsystem": bug.get("subsystem"),
            "fault_codes": codes,
            "gold_dimension": dims,
            "source": "ROBUST (Timperley et al. 2024, arXiv:2404.03629)",
        })
    json.dump(cases, open(out, "w"), indent=2)
    print(f"parsed={total} integration_relevant={integ}")
    print("per-ECM-dimension (multi-label):", dict(dist.most_common()))
    bysys = collections.Counter(c["system"] for c in cases)
    print("by system:", dict(bysys.most_common()))
    print(f"wrote {len(cases)} cases -> {out}")


if __name__ == "__main__":
    main()
