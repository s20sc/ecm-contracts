"""Coordinator-built, unblinded, late source-slice replay; never original S2."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from types import ModuleType

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BLOCKED = {"evidence_inadequate", "source_unavailable", "tool_failure", "budget_exhausted"}
LABEL = "coordinator-built / unblinded / late / post-outcome"
FAILURE_ANCHORS = {"C3-053": ["nan_outcome", "nan_error"], "C3-127": ["tf_outcome"],
                   "C3-136": ["rclcpp_outcome", "rclcpp_timer_stall"], "C3N-006": ["moveit_outcome"]}
EXPECTED = {"robust_84264f0", "robust_b166c93", "robust_ff581a0", "C3-053", "C3-127", "C3-136", "C3N-006"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frozen_modules() -> tuple[ModuleType, ModuleType, dict]:
    base = ROOT / "experiments/pathb_v2"
    freeze = read(base / "FREEZE.json")
    hashes = {}
    for rel in ("assemble.py", "scoring.py", "baselines_v2.py", "../pathb/checker/contract_checker.py", "../pathb/checker/canonical.py"):
        hashes[rel] = sha(base / rel)
        if hashes[rel] != freeze["files"][rel]:
            raise ValueError(f"Frozen code mismatch: {rel}")
    for rel in ("qos_literal.py", "frame_literal.py"):
        hashes[rel] = sha(base / rel)
        if hashes[rel] != freeze["ledgers"][rel]["sha256"]:
            raise ValueError(f"Frozen dependency mismatch: {rel}")
    hashes["FREEZE.json"] = sha(base / "FREEZE.json")
    sys.path.insert(0, str(base))
    return load_module("late_assemble", base / "assemble.py"), load_module("late_scoring", base / "scoring.py"), hashes


def verify_inputs(data: dict) -> None:
    if {c["spec"]["case_id"] for c in data["cases"]} != EXPECTED or len(data["cases"]) != 7:
        raise ValueError("Seven distinct admissions required")
    for rel, expected in data["protected_sha256"].items():
        if sha(ROOT / rel) != expected:
            raise ValueError(f"Protected file changed: {rel}")
    for source in data["sources"].values():
        if sha(ROOT / source["path"]) != source["sha256"]:
            raise ValueError(f"Source changed: {source['path']}")
    for aid, anchor in data["anchors"].items():
        source = data["sources"][anchor["source_id"]]
        raw = (ROOT / source["path"]).read_text(encoding="utf-8")
        if anchor["json_pointer"] is None:
            quote = anchor["quote"]
            lines = raw.splitlines()
            selected = "\n".join(lines[anchor["line"] - 1:anchor["end_line"]])
            if quote not in selected:
                raise ValueError(f"Verbatim anchor mismatch: {aid}")
        else:
            obj = json.loads(raw)
            for part in anchor["json_pointer"].strip("/").split("/"):
                obj = obj[int(part)] if isinstance(obj, list) else obj[part]
            if anchor["quote"] not in obj or anchor["raw_verbatim"] not in raw.splitlines()[anchor["line"] - 1]:
                raise ValueError(f"JSON verbatim anchor mismatch: {aid}")
    for case in data["cases"]:
        spec = case["spec"]
        expected_anchors = FAILURE_ANCHORS.get(spec["case_id"], [])
        if spec["outcome_class"] != ("failure" if expected_anchors else "undocumented") or spec["outcome_evidence"] != expected_anchors:
            raise ValueError("Reviewed per-case outcome census or outcome anchors changed")
        if spec["specific_cause"] is not None or spec["resolution_status"] != "unknown" or spec["observed_success_control"]:
            raise ValueError("No demonstrated specific cause or observed-success control")
        if bool(spec["failed_conditions"]) != bool(expected_anchors):
            raise ValueError("Reviewed condition list changed")
        for condition in spec["failed_conditions"]:
            if condition["class"] != "other" or condition["evidence"] != expected_anchors:
                raise ValueError("Only reviewed generic-other conditions admitted")
        if spec["outcome_class"] == "failure" and not spec["outcome_evidence"]:
            raise ValueError("Failure without quoted outcome")
        if spec["outcome_class"] not in {"failure", "undocumented"}:
            raise ValueError("No observed-success controls authorized")
        for aid in spec["outcome_evidence"]:
            if aid not in data["anchors"]:
                raise ValueError(f"Unknown outcome anchor {aid}")
        for desc in case["descriptions"].values():
            own_anchors = {aid for aids in desc["evidence_map"].values() for aid in aids}
            if not own_anchors.issubset(data["anchors"]):
                raise ValueError("Unknown descriptor anchor")
            own_revisions = {data["sources"][data["anchors"][aid]["source_id"]]["revision"] for aid in own_anchors}
            if desc["revision"] is not None and desc["revision"] not in own_revisions:
                raise ValueError("Revision is not retained in source metadata")
            for declaration, value in desc["declares"].items():
                aids = desc["evidence_map"].get(f"declares[{declaration}]") or []
                if not any(value == data["anchors"][aid]["quote"] for aid in aids):
                    raise ValueError("Declaration lacks literal source quote")
            if desc["exclusive"]:
                raise ValueError("No source-bound exclusive resources admitted")
            for field in ("perm_requires", "perm_grants"):
                if desc[field] != {"state": "unknown", "values": None}:
                    raise ValueError("Unknown permission payload must be null")
            if desc["recovery"] != {"state": "unknown", "value": None}:
                raise ValueError("Unknown recovery payload must be null")
            for i, port in enumerate(desc["ports"]):
                if not desc["evidence_map"].get(f"ports[{i}].binding"):
                    raise ValueError("Port binding lacks source anchor")
                for field in ("msg_type", "frame", "units", "rate_hz", "min_rate_hz", "definition_id"):
                    if port[field] is not None:
                        aids = desc["evidence_map"].get(f"ports[{i}].{field}")
                        if not aids:
                            raise ValueError(f"Non-null attribute without source: {field}")
                        quotes = [data["anchors"][aid]["quote"] for aid in aids]
                        if field == "msg_type" and not any(port[field] in quote for quote in quotes):
                            raise ValueError("Nominal type not literal in cited source")
                        if field == "rate_hz" and not any(re.search(r"Rate\s+\w+\(" + re.escape(str(port[field])) + r"\)", quote) for quote in quotes):
                            raise ValueError("Rate not literal in cited source")
                        if field not in {"msg_type", "rate_hz"}:
                            raise ValueError("Other non-null attributes require a new reviewed evidence policy")
                if any(value is not None for value in port["qos"].values()):
                    raise ValueError("No source-bound QoS values admitted in this replay")
            for aids in desc["evidence_map"].values():
                if any(aid not in data["anchors"] for aid in aids):
                    raise ValueError("Unknown descriptor source anchor")
            if desc["not_declared"] or any(desc[field]["state"] != "unknown" for field in ("perm_requires", "perm_grants", "recovery")):
                raise ValueError("Source slices cannot prove package-wide absence")


def composition(case: dict, assembler: ModuleType) -> dict:
    descriptions = case["descriptions"]
    for side in ("producer", "consumer"):
        desc = descriptions[side]
        if desc["status"] in BLOCKED:
            return {"status": "unassessable", "reason": f"{side}:{desc['status']}:{desc['reason']}", "units": []}
    units = assembler.edge_units(case["spec"], descriptions["producer"], descriptions["consumer"], "PAIR", "producer", "consumer")
    if not units or not any(u["status"] == "done" for u in units):
        return {"status": "unassessable", "reason": "No two-sided source-bound edge", "units": units}
    return {"status": "done", "reason": None, "units": units}


def evaluate(data: dict) -> dict:
    verify_inputs(data)
    assembler, scorer, binding = frozen_modules()
    rows = []
    for case in data["cases"]:
        spec = case["spec"]
        comp = composition(case, assembler)
        scores = scorer.score_composition(comp, spec["failed_conditions"], "PAIR", {})
        missing_edges = [{"element": u["element"], "reason": u["reason"]} for u in comp["units"] if u["status"] != "done"]
        rows.append({"case_id": spec["case_id"], "corpus": spec["corpus"], "label": LABEL,
                     "outcome_class": spec["outcome_class"], "outcome_basis": spec["outcome_basis"],
                     "outcome_evidence": spec["outcome_evidence"], "loudness": "unknown",
                     "classes": sorted({c["class"] for c in spec["failed_conditions"]}),
                     "assembled_status": comp["status"], "composition": comp, "broken": scores,
                     "resolved": None, "resolution_status": "unknown", "observed_success_control": False,
                     "missing_edges": missing_edges, "missingness": case["missingness"],
                     "interpretation": "Raw accept does not establish coverage or runtime success; not_supported denotes no implemented matching rule; unassessable denotes missing source evidence."})
    census = {label: [r["case_id"] for r in rows if r["outcome_class"] == label] for label in ("failure", "undocumented")}
    out = {"label": LABEL, "original_S2": False, "independent_human_labels": False,
           "complete_expanded_boundary_results": False, "n_tracked": len(rows), "outcome_census": census,
           "frozen_rule_binding": binding, "rows": rows, "aggregate_source_reported_failures": scorer.aggregate(rows, complete_case=False),
           "statistical_interpretation": "Late descriptive replay only. Aggregate excludes three undocumented C1 outcomes; no H1 expansion or inference is warranted."}
    verify_inputs(data)
    return out


def main() -> None:
    data = read(HERE / "inputs.json")
    out = evaluate(data)
    (HERE / "results.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
