"""Exploratory ablation, decided after unsealing (DEVIATIONS.md, 2026-09-30): the version rule
without its consumer condition.

The frozen checker flags an upgrade when a changed element of the provider is one the consumer
references (field_break on changed_fields & consumer_reads). The consumer-blind variant flags an
upgrade whenever any element changed. It is computed with the frozen checker and scorer unchanged:
each assembled upgrade unit's consumer_reads is replaced by changed_fields | consumer_reads, so
field_break fires on every changed element. A consumer-blind rule does not rely on the consumer's
reference, so the provenance of each added reference is marked as not required and the credit of a
finding rests on the provenance of the changed element alone. Every other method, composition kind
and rule is scored as in the primary analysis.

A second variant (pre-R3 audit, 2026-09-30) restricts the changed set to the elements that the built-against
provider's description declares, that is removals and modifications, and widens the references with those
alone, so no addition is flagged, which an API-diff tool would not report as breaking. The declaration comes
from the task's recon file.

Read-only by default; `--write` writes report/exploratory_consumer_blind.json.
"""
import argparse
import copy
import json
import os
from typing import List, Optional, Tuple

import scoring as S

HERE = os.path.dirname(os.path.abspath(__file__))
NOT_REQUIRED = "consumer-blind ablation: no consumer reference required"


def declared_at_built(unit: dict, tasks_dir: str) -> set:
    """Elements the built-against provider description declares; a missing recon file is an error."""
    t = (unit.get("tasks") or {}).get("built")
    if not t:
        raise ValueError(f"upgrade unit without a built-against task: {unit.get('tasks')}")
    with open(os.path.join(tasks_dir, t, "recon", f"{t}.json")) as fh:
        recon = json.load(fh)
    return {e for e, d in (recon.get("declares") or {}).items() if d}


def consumer_blind(comp: Optional[dict], tasks_dir: Optional[str] = None) -> Tuple[Optional[dict], List[dict]]:
    """Return the composition with every upgrade unit's reads widened to its changed elements; with
    `tasks_dir`, only to the changed elements the built-against provider declares (no additions)."""
    if comp is None:
        return None, []
    c = copy.deepcopy(comp)
    changes = []
    for unit in c.get("units") or []:
        if unit.get("kind") != "upgrade" or unit.get("status") != "done":
            continue
        vd = (unit.get("encoding") or {}).get("ver_delta") or {}
        changed = list(vd.get("changed_fields") or [])
        if tasks_dir is not None:
            # The changed set itself is restricted, not only the added references: a consumer can already
            # reference an element the release added (C3-046, C3-135), and field_break would then flag the
            # addition (R3, external review F2).
            built = declared_at_built(unit, tasks_dir)
            changed = [x for x in changed if x in built]
            vd["changed_fields"] = changed
        reads = list(vd.get("consumer_reads") or [])
        added = [x for x in changed if x not in reads]
        vd["consumer_reads"] = reads + added
        prov = unit.setdefault("provenance", {})
        for x in added:
            prov[f"ver_delta.consumer_reads[{x}]"] = NOT_REQUIRED
        if added:
            changes.append({"added_reads": added})
    return c, changes


def controls(rows: List[dict]) -> dict:
    """Checker verdict on every control composition, keyed by case."""
    out = {}
    for r in rows:
        if r["resolved"]:
            out[(r["case_id"], "resolved")] = r["resolved"]["ECM"]["state"]
        if r["outcome_class"] == "warning_only":
            out[(r["case_id"], "warning_only")] = r["broken"]["ECM"]["state"]
    return out


def summary(agg: dict) -> dict:
    m = agg["methods"]["ECM"]
    pick = lambda k: {"k": m[k]["k"], "n": m[k]["n"], "cases": m[k]["cases"]}
    return {"right_reason": pick("right_reason"), "binary_reject": pick("binary_reject"),
            "false_alarm_fixed_observed": pick("false_alarm_fixed_observed"),
            "false_alarm_fixed_recommended": pick("false_alarm_fixed_recommended"),
            "false_alarm_warning_only": pick("false_alarm_warning_only")}


def main(write: bool) -> dict:
    specs = S.load_specs(True, "adjudicated")
    verdicts_all = json.load(open(os.path.join(HERE, "adjudicated", "provenance_verdicts.json")))
    pilot = set(json.load(open(os.path.join(HERE, "pilot", "PILOT_CASES.json")))["quarantined_pilot_cases"])
    s1_models = json.load(open(os.path.join(HERE, "ledger", "s1_models.json")))
    sel = S.c3_selection(S.load_specs(False))
    primary, _ = S.build_rows(specs, verdicts_all, pilot, s1_models, sel)
    blind, added = S.build_rows(specs, verdicts_all, pilot, s1_models, sel, transform=consumer_blind)
    tasks_dir = os.path.join(HERE, "s2_work", "tasks")
    breaking, added_b = S.build_rows(specs, verdicts_all, pilot, s1_models, sel,
                                     transform=lambda comp: consumer_blind(comp, tasks_dir))
    out = {"what": "consumer-blind version rule, exploratory, decided after unsealing",
           "compositions_with_added_reads": len(added),
           "compositions_with_added_reads_breaking_only": len(added_b), "by_corpus": {}}
    for corpus in sorted({r["corpus"] for r in primary}):
        p = [r for r in primary if r["corpus"] == corpus]
        up_p = [r for r in p if r["operation"] == "UPGRADE"]
        cp = controls(up_p)
        d = out["by_corpus"][corpus] = {"all_cases": {"primary": summary(S.aggregate(p))},
                                        "upgrade_cases": {"n_rows": len(up_p), "primary": summary(S.aggregate(up_p))}}
        for name, rows, suffix in (("consumer_blind", blind, ""), ("consumer_blind_breaking_only", breaking, "_breaking_only")):
            b = [r for r in rows if r["corpus"] == corpus]
            up_b = [r for r in b if r["operation"] == "UPGRADE"]
            cb = controls(up_b)
            d["all_cases"][name] = summary(S.aggregate(b))
            d["upgrade_cases"][name] = summary(S.aggregate(up_b))
            d["failure_state_changes" + suffix] = S.state_changes(p, b)
            d["control_state_changes" + suffix] = [{"case_id": k[0], "composition": k[1], "primary": cp[k], name: cb[k]}
                                                   for k in sorted(cp) if cp[k] != cb.get(k)]
    if write:
        path = os.path.join(HERE, "report", "exploratory_consumer_blind.json")
        with open(path, "w") as fh:
            json.dump(out, fh, indent=1, sort_keys=True)
        print(f"wrote {path}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="write report/exploratory_consumer_blind.json")
    res = main(ap.parse_args().write)
    for corpus, d in res["by_corpus"].items():
        for scope in ("all_cases", "upgrade_cases"):
            for variant in ("primary", "consumer_blind", "consumer_blind_breaking_only"):
                s = d[scope][variant]
                print(f"{corpus} {scope:13s} {variant:14s} RR {s['right_reason']['k']}/{s['right_reason']['n']}"
                      f"  binary {s['binary_reject']['k']}  FA obs {s['false_alarm_fixed_observed']['k']}/{s['false_alarm_fixed_observed']['n']}"
                      f"  rec {s['false_alarm_fixed_recommended']['k']}/{s['false_alarm_fixed_recommended']['n']}"
                      f"  warn {s['false_alarm_warning_only']['k']}/{s['false_alarm_warning_only']['n']}")
        for suffix in ("", "_breaking_only"):
            print(f"{corpus} failure state changes{suffix}: {d['failure_state_changes' + suffix]}")
            print(f"{corpus} control state changes{suffix}: {d['control_state_changes' + suffix]}")
