"""Audit of the S2 description runs' use of the shared scratch directory (DEVIATIONS.md, 2026-09-29).

  python3 audit_s2_scratch.py <transcript_dir>

The agent harness gives every run of a session one scratch directory, which also held material from
the specification stage. This script reads each S2 transcript (JSON lines, plain or gzip), keeps only
the inputs of the tool calls the run made (never the prompt text or tool results), and reports every
reference to the scratch directory by its first path component. A reference counts as the run's own
when that component contains the run's task id; a listing or search command aimed at the scratch
root is reported separately. The output is the evidence behind the threats paragraph.
"""
from __future__ import annotations

import collections
import glob
import gzip
import json
import os
import re
import sys

REF = re.compile(r'scratchpad(/[^\s"\'\\;|&)]*)?')
LIST_ROOT = re.compile(r'\b(ls|find|grep|rg|tree|du)\b[^|;&"]*scratchpad/?(?:"|\s|$)')
CD_ROOT_THEN_LIST = re.compile(r'\bcd\s+"?[^;&|"]*scratchpad/?"?\s*(?:&&|;)\s*(ls|find|grep|rg|tree|du)\b')
TASK = re.compile(r"s2_work/tasks/(u\d{4})/S2_PROMPT\.md")
# Directories in the scratch root that no S2 run created (specification-stage material and pilot
# clones, listed from the root on 2026-09-29); a tool call naming one, by any path, is reported.
# Only names specific to that material; generic ones (src, repos, gh, snap) occur inside every snapshot and
# are reachable in the scratch root only through a scratchpad path, which REF already reports.
UPSTREAM = ("robust", "s108", "S1_C1_04", "S1_C1_05", "s1c103", "icloud_dups")
UPSTREAM_REF = re.compile(r"(?<![\w.-])(" + "|".join(map(re.escape, UPSTREAM)) + r")/[\w.-]")


def lines(path: str):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", errors="ignore") as f:
        for line in f:
            yield line


def audit(paths) -> dict:
    per_task, foreign, root_lists, upstream = {}, [], [], []
    for p in paths:
        text = "".join(lines(p))
        m = TASK.search(text)
        if not m:
            continue
        tid = m.group(1)
        refs = collections.Counter()
        for line in text.splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            content = (d.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for x in content:
                if x.get("type") != "tool_use":
                    continue
                s = json.dumps(x.get("input"))
                for r in REF.finditer(s):
                    first = (r.group(1) or "").strip("/").split("/")[0].rstrip("\\")
                    refs[first or "<root>"] += 1
                    if first and tid not in first:
                        foreign.append({"task": tid, "component": first})
                for u in UPSTREAM_REF.finditer(s):
                    upstream.append({"task": tid, "name": u.group(1), "context": s[max(0, u.start() - 60):u.end() + 40]})
                if LIST_ROOT.search(s) or CD_ROOT_THEN_LIST.search(s):
                    root_lists.append({"task": tid, "command": s[:200]})
        per_task.setdefault(tid, collections.Counter()).update(refs)
    return {"n_tasks": len(per_task), "n_refs": sum(sum(c.values()) for c in per_task.values()),
            "foreign_components": foreign, "root_listings": root_lists, "upstream_name_refs": upstream}


if __name__ == "__main__":
    d = sys.argv[1]
    files = sorted(glob.glob(os.path.join(d, "*.jsonl.gz")) + glob.glob(os.path.join(d, "*.jsonl"))
                   + glob.glob(os.path.join(d, "*.output")))
    print(json.dumps(audit(files), indent=1))
