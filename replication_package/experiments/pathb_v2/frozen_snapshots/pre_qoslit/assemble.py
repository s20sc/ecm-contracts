"""Assemble compositions from per-unit descriptions (PROTOCOL.md Section 7). Deterministic.

  python3 assemble.py [--write]

Reads specs/*.json, ledger/tasks.json and s2_work/tasks/<task_id>/recon/<task_id>.json; writes
assembled/<case_id>.json. No agent sees a pairing: this script pairs a provider's
`provides` port with a consumer's `consumes` port per inventory element, and computes
UPGRADE deltas as a textual diff of declaration signatures between two provider
revisions. Provenance is carried per value and per token.

An assembled case:
  {"case_id", "corpus", "operation", "status": "done|unassessable", "reason",
   "compositions": {"broken": COMP, "resolved": COMP|null}}
COMP = {"status", "reason", "units": [UNIT]}
UNIT = {"kind": "edge|upgrade|pair_view", "element", "encoding", "provenance"}
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, "s2_work", "tasks")


def load_json(path):
    return json.load(open(path)) if os.path.exists(path) else None


def recon_for(ledger: dict, unit: str, rev: str) -> Tuple[Optional[dict], str]:
    tid = ledger["by_key"].get(f"{unit}@{rev}")
    if tid is None:
        return None, "revision_unresolved"
    entry = ledger["tasks"][tid]
    if entry["status"] not in ("done", "excerpt"):
        return None, entry["status"]
    r = load_json(os.path.join(TASKS, tid, "recon", f"{tid}.json"))
    if r is None:
        return None, "recon_missing"
    if r.get("status") in ("evidence_inadequate", "source_unavailable", "tool_failure", "budget_exhausted"):
        return None, r["status"]
    r["_task_id"] = tid
    return r, "done"


def canonical_type(t: Optional[str]) -> Optional[str]:
    """One spelling per interface type, so that two S2 runs naming the same type differently do not
    compare as different types: `pkg/msg/Type`, `pkg/srv/Type`, `pkg/action/Type` and the C++ form
    `pkg::msg::Type` all become `pkg/Type`. A different package or type name still differs."""
    if not t:
        return t
    s = str(t).strip().replace("::", "/")
    parts = [x for x in s.split("/") if x]
    if len(parts) == 3 and parts[1] in ("msg", "srv", "action"):
        parts = [parts[0], parts[2]]
    return "/".join(parts)


def port_of(desc: dict, element: str, side: str) -> Tuple[Optional[dict], Optional[int]]:
    for i, p in enumerate(desc.get("ports") or []):
        if p.get("element") == element and p.get("side") == side:
            q = p.get("qos") or {}
            return ({"role": element, "msg_type": canonical_type(p.get("msg_type")), "frame": p.get("frame"), "units": p.get("units"),
                     "qos": {"reliability": q.get("reliability"), "durability": q.get("durability"),
                             "deadline_ms": q.get("deadline_ms")},
                     "rate_hz": p.get("rate_hz"), "min_rate_hz": p.get("min_rate_hz"),
                     "definition_id": p.get("definition_id")}, i)
    return None, None


def copy_prov(desc: dict, src_prefix: str, dst_prefix: str, prov: Dict[str, str]) -> None:
    for k, v in (desc.get("provenance") or {}).items():
        if k == src_prefix or k.startswith(src_prefix + "."):
            prov[dst_prefix + k[len(src_prefix):]] = v


def side_block(desc: dict, prefix: str, prov: Dict[str, str]) -> dict:
    block = {"outputs": [], "inputs": [], "exclusive": list(desc.get("exclusive") or []),
             "perm_requires": [], "perm_grants": [], "perm_limits": {}, "recovery": None,
             "_states": {}}
    for tok in block["exclusive"]:
        v = (desc.get("provenance") or {}).get(f"exclusive[{tok}]")
        if v:
            prov[f"{prefix}.exclusive[{tok}]"] = v
    for fld in ("perm_requires", "perm_grants"):
        rec = desc.get(fld) or {}
        block["_states"][fld] = rec.get("state", "unknown")
        if rec.get("state") == "present":
            block[fld] = list(rec.get("values") or [])
            for tok in block[fld]:
                v = (desc.get("provenance") or {}).get(f"{fld}[{tok}]")
                if v:
                    prov[f"{prefix}.{fld}[{tok}]"] = v
    rec = desc.get("recovery") or {}
    block["_states"]["recovery"] = rec.get("state", "unknown")
    if rec.get("state") == "present":
        block["recovery"] = rec.get("value")
        v = (desc.get("provenance") or {}).get("recovery")
        if v:
            prov[f"{prefix}.recovery"] = v
    return block


def edge_units(spec: dict, producer: dict, consumer: dict, ctype: str,
               producer_name: Optional[str] = None, consumer_name: Optional[str] = None) -> List[dict]:
    units = []
    for inv in spec.get("inventory") or []:
        el = inv["element"]
        sides = inv.get("sides") or {}
        p_desc, c_desc, p_name, c_name = producer, consumer, producer_name, consumer_name
        # The element's own sides fix the edge direction: a service request field flows from the
        # client (which the inventory marks as providing it) to the server, against the case roles.
        if p_name and c_name and sides.get(p_name) == "consumes" and sides.get(c_name) == "provides":
            p_desc, c_desc, p_name, c_name = consumer, producer, consumer_name, producer_name
        prov: Dict[str, str] = {}
        p_block = side_block(p_desc, "producer", prov)
        c_block = side_block(c_desc, "consumer", prov)
        po, pi_ = port_of(p_desc, el, "provides")
        ci, ci_ = port_of(c_desc, el, "consumes")
        if po is None or ci is None:
            units.append({"kind": "edge", "element": el, "status": "unassessable_edge",
                          "reason": "port_missing_" + ("producer" if po is None else "consumer"),
                          "direction": {"producer": p_name, "consumer": c_name}, "encoding": None, "provenance": {}})
            continue
        copy_prov(p_desc, f"ports[{pi_}]", "producer.outputs[0]", prov)
        copy_prov(c_desc, f"ports[{ci_}]", "consumer.inputs[0]", prov)
        p_block["outputs"] = [po]
        c_block["inputs"] = [ci]
        enc = {"type": ctype, "producer": p_block, "consumer": c_block, "edge": {"out_role": el, "in_role": el}}
        units.append({"kind": "edge", "element": el, "status": "done", "direction": {"producer": p_name, "consumer": c_name},
                      "encoding": enc, "provenance": prov})
    return units


_SIG_LABEL = re.compile(r"^(?:api|field|msg|topic|param|service|srv|action)\s+.*?:\s")
_SIG_ATTR = re.compile(r"\b(?:[A-Z][A-Z0-9]*_(?:[A-Z0-9]+_)*(?:PUBLIC|EXPORT|LOCAL|API|UNUSED|DEPRECATED|INLINE|VISIBILITY)(?:_[A-Z0-9]+)*"
                       r"|attribute_deprecated)\b|__attribute__\s*\(\([^()]*\)\)")
_SIG_PUNCT = re.compile(r"\s*([(),*&<>\[\];{}=])\s*")


def canonical_sig(s) -> str:
    """Transcription-neutral form of a `declares` entry, so that two S2 runs describing the same
    declaration compare equal: whitespace collapsed, the leading `<kind> <symbol>: ` label dropped,
    visibility and attribute macros dropped, spaces around punctuation removed, a trailing `;` or
    `{` dropped. Types, parameters, defaults and values are kept, so a real change still differs;
    differences a canonical form cannot settle (another line of the same declaration, another
    representation of the same definition) are left to the A2 substance check."""
    s = " ".join(str(s).split())
    s = _SIG_LABEL.sub("", s, count=1)
    s = _SIG_ATTR.sub(" ", s)
    s = _SIG_PUNCT.sub(r"\1", s)
    return " ".join(s.rstrip(";{ ").split())


def upgrade_units(spec: dict, prov_built: dict, prov_running: dict, consumer: dict) -> List[dict]:
    def norm_sig(d):
        return {k: canonical_sig(v) for k, v in (d or {}).items()}
    d_old, d_new = norm_sig(prov_built.get("declares")), norm_sig(prov_running.get("declares"))
    nd_old, nd_new = set(prov_built.get("not_declared") or []), set(prov_running.get("not_declared") or [])

    def state(el, d, nd):
        """declared signature, "absent" (positively not declared), or None (undetermined)."""
        if el in d:
            return d[el]
        return "absent" if el in nd else None

    changed, unknown = [], []
    for el in sorted(set(d_old) | set(d_new) | nd_old | nd_new):
        so, sn = state(el, d_old, nd_old), state(el, d_new, nd_new)
        if so is None or sn is None:
            if so != sn:
                unknown.append(el)  # declared on one side, undetermined on the other
            continue
        if so != sn:
            changed.append(el)
    reads = sorted(set(consumer.get("references") or []))
    prov: Dict[str, str] = {}
    for el in changed:
        parts = []
        for tag, d in (("built", prov_built), ("running", prov_running)):
            pv = d.get("provenance") or {}
            v = pv.get(f"declares[{el}]") or pv.get(f"not_declared[{el}]")
            if v:
                parts.append(f"{tag}: {v}")
        if len(parts) == 2:
            prov[f"ver_delta.changed_fields[{el}]"] = " || ".join(parts)
    for el in reads:
        v = (consumer.get("provenance") or {}).get(f"references[{el}]")
        if v:
            prov[f"ver_delta.consumer_reads[{el}]"] = v
    for key, d in (("semver_old", prov_built), ("semver_new", prov_running)):
        v = (d.get("provenance") or {}).get("manifest_version")
        if v:
            prov[f"ver_delta.{key}"] = v
    enc = {"type": "UPGRADE",
           "ver_delta": {"changed_fields": changed, "consumer_reads": reads,
                         "semver_old": prov_built.get("manifest_version"),
                         "semver_new": prov_running.get("manifest_version")}}
    units = [{"kind": "upgrade", "element": None, "status": "done", "encoding": enc, "provenance": prov,
              "unknown_delta": unknown}]
    # Pair views: the consumer as built against the old provider definition vs the running provider.
    for inv in spec.get("inventory") or []:
        el = inv["element"]
        pv: Dict[str, str] = {}
        p_run, i_run = port_of(prov_running, el, "provides")
        p_old, i_old = port_of(prov_built, el, "provides")
        c_port, i_c = port_of(consumer, el, "consumes")
        if p_run is None or p_old is None or c_port is None:
            units.append({"kind": "pair_view", "element": el, "status": "unassessable_edge",
                          "reason": "port_missing", "encoding": None, "provenance": {}})
            continue
        built_view = dict(c_port)
        built_view["msg_type"] = p_old.get("msg_type")
        built_view["definition_id"] = p_old.get("definition_id")
        copy_prov(prov_running, f"ports[{i_run}]", "producer.outputs[0]", pv)
        copy_prov(consumer, f"ports[{i_c}]", "consumer.inputs[0]", pv)
        for fld in ("msg_type", "definition_id"):
            v = (prov_built.get("provenance") or {}).get(f"ports[{i_old}].{fld}")
            if v:
                pv[f"consumer.inputs[0].{fld}"] = "built-against provider: " + v
        enc_pv = {"type": "PAIR", "producer": {"outputs": [p_run], "inputs": [], "exclusive": [], "perm_requires": []},
                  "consumer": {"outputs": [], "inputs": [built_view], "exclusive": [], "perm_requires": []},
                  "edge": {"out_role": el, "in_role": el}}
        units.append({"kind": "pair_view", "element": el, "status": "done", "encoding": enc_pv, "provenance": pv})
    return units


def roles(spec: dict) -> Tuple[Optional[dict], Optional[dict]]:
    us = spec["units"]
    prov = next((u for u in us if u.get("role") in ("provider", "producer")), None)
    cons = next((u for u in us if u.get("role") == "consumer"), None)
    if prov is None or cons is None:
        if len(us) == 2:  # peers: order as listed
            return us[0], us[1]
        return None, None
    return prov, cons


def build_composition(spec: dict, ledger: dict, which: str) -> dict:
    op = spec["operation"]
    pu, cu = roles(spec)
    if pu is None:
        return {"status": "unassessable", "reason": "roles_unidentified", "units": []}
    p_desc, p_st = recon_for(ledger, pu["name"], pu.get(f"{which}_rev"))
    c_desc, c_st = recon_for(ledger, cu["name"], cu.get(f"{which}_rev"))
    if p_desc is None or c_desc is None:
        return {"status": "unassessable", "reason": f"{'producer' if p_desc is None else 'consumer'}:{p_st if p_desc is None else c_st}", "units": []}
    if op in ("PAIR", "CONCURRENT", "SWITCH"):
        units = edge_units(spec, p_desc, c_desc, "CONCURRENT" if op == "CONCURRENT" else "PAIR", pu["name"], cu["name"])
    elif op == "UPGRADE":
        built_rev = (spec.get("consumer_built_against") or {}).get(which)
        if not built_rev:
            return {"status": "unassessable", "reason": "built_against_unknown", "units": []}
        b_desc, b_st = recon_for(ledger, pu["name"], built_rev)
        if b_desc is None:
            return {"status": "unassessable", "reason": f"provider_built:{b_st}", "units": []}
        units = upgrade_units(spec, b_desc, p_desc, c_desc)
    else:
        return {"status": "unassessable", "reason": "operation_unknown", "units": []}
    if not any(u["status"] == "done" for u in units):
        return {"status": "unassessable", "reason": "no_assessable_unit", "units": units}
    return {"status": "done", "reason": None, "units": units}


def assemble_case(spec: dict, ledger: dict) -> dict:
    out = {"case_id": spec["case_id"], "corpus": spec["corpus"], "operation": spec["operation"],
           "status": "done", "reason": None, "compositions": {}}
    out["compositions"]["broken"] = build_composition(spec, ledger, "broken")
    if (spec.get("resolution") or {}).get("status") in ("observed", "recommended"):
        out["compositions"]["resolved"] = build_composition(spec, ledger, "resolved")
    else:
        out["compositions"]["resolved"] = None
    if out["compositions"]["broken"]["status"] != "done":
        out["status"], out["reason"] = "unassessable", out["compositions"]["broken"]["reason"]
    return out


def main(write: bool) -> None:
    ledger = load_json(os.path.join(HERE, "ledger", "tasks.json")) or {"tasks": {}, "by_key": {}}
    n_done = n_un = 0
    os.makedirs(os.path.join(HERE, "assembled"), exist_ok=True)
    for f in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        spec = json.load(open(f))
        if not spec.get("eligible"):
            continue
        a = assemble_case(spec, ledger)
        n_done += a["status"] == "done"
        n_un += a["status"] != "done"
        if write:
            json.dump(a, open(os.path.join(HERE, "assembled", f"{spec['case_id']}.json"), "w"), indent=1)
    print(f"assembled: {n_done} done, {n_un} unassessable")


if __name__ == "__main__":
    main("--write" in sys.argv)
