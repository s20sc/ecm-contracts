"""Mutation inventory for the v2.1 scoring package (PROTOCOL.md Section 14).

  python3 mutation_probe.py [--report MUTATIONS.md]

Copies the package into a temporary tree next to the frozen checker, applies one
mutation at a time to the copy, runs the test suite, and records the result. A mutation
counts as killed only when a test fails on an assertion; a run that fails for another
reason (an exception from the code under test, a syntax, import, or collection error)
is reported as `error`, not as a kill, because it would fail whatever the tests check. The unmutated baseline must pass,
or the run stops. A surviving or erroring mutation is a test gap; the report lists all
of them with the code hash.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PB = os.path.join(os.path.dirname(HERE), "pathb")
CODE_FILES = ("scoring.py", "baselines_v2.py", "assemble.py", "build_packets.py", "materialize.py", "adjudicate.py",
              "qos_literal.py", "frame_literal.py", "freeze.py", "report_extra.py", "exploratory_consumer_blind.py")

MUTATIONS = [
    ("report.distinct_counts_occurrences", "report_extra.py",
     '        keys.setdefault((x["task_id"], idx if idx is not None else x["element"], field), x["reason"])',
     '        keys.setdefault((x["task_id"], idx if idx is not None else x["element"], field, x["element"], x.get("composition")), x["reason"])'),
    ("report.strata_pooled", "report_extra.py",
     '                agg = S.aggregate([r for r in of(rs, c) if str(r[key]) == v])\n                rr = agg["methods"]["ECM"]["right_reason"]',
     '                agg = S.aggregate([r for r in rs if str(r[key]) == v])\n                rr = agg["methods"]["ECM"]["right_reason"]'),
    ("report.alert_counts_unassessable_control", "report_extra.py",
     '                ctl_find += st == "reject"',
     '                ctl_find += st in ("reject", "unassessable")'),
    ("ablation.added_reads_unverified", "exploratory_consumer_blind.py",
     '            prov[f"ver_delta.consumer_reads[{x}]"] = NOT_REQUIRED',
     '            pass'),
    ("ablation.mutates_input", "exploratory_consumer_blind.py",
     '    c = copy.deepcopy(comp)',
     '    c = comp'),
    ("adj.control_version_finding_to_pair_view", "adjudicate.py",
     '    kind = finding.get("unit_kind") or ("upgrade" if finding.get("rule") in VER_RULES else None)',
     '    kind = finding.get("unit_kind")'),
    ("adj.version_evidence_unchecked", "adjudicate.py",
     '    if method == "ECM" and finding["rule"] in VER_RULES and (unit or {}).get("kind") != "upgrade":',
     '    if False:'),
    ("asm.permission_provenance_old_key_only", "assemble.py",
     '                v = dp.get(f"{fld}.values[{tok}]") or dp.get(f"{fld}[{tok}]")',
     '                v = dp.get(f"{fld}[{tok}]")'),
    ("ablation.breaking_only_keeps_additions", "exploratory_consumer_blind.py",
     '            changed = [x for x in changed if x in built]',
     '            changed = [x for x in changed if x in built or x]'),
    ("ablation.breaking_only_keeps_added_elements_in_delta", "exploratory_consumer_blind.py",
     '            vd["changed_fields"] = changed\n',
     '\n'),
    ("ablation.breaking_only_counts_empty_declaration", "exploratory_consumer_blind.py",
     '    return {e for e, d in (recon.get("declares") or {}).items() if d}',
     '    return set(recon.get("declares") or {})'),
    ("ablation.breaking_only_missing_description_is_empty", "exploratory_consumer_blind.py",
     '    with open(os.path.join(tasks_dir, t, "recon", f"{t}.json")) as fh:\n        recon = json.load(fh)',
     '    p = os.path.join(tasks_dir, t, "recon", f"{t}.json")\n    recon = json.load(open(p)) if os.path.exists(p) else {}'),
    ("report.cause_share_drops_warning_cause", "report_extra.py",
     '                  "binary_ppv": [rej, den], "cause_correct_share": [rr + warn_cause, den]}',
     '                  "binary_ppv": [rej, den], "cause_correct_share": [rr, den]}'),
    ("report.stage_double_counts_unknown", "report_extra.py",
     '            sub = [r for r in fails if r.get("detection_stage") == key and r["loudness"] != "unknown"]',
     '            sub = [r for r in fails if r.get("detection_stage") == key]'),
    ("agg.by_class_every_carried_class", "scoring.py",
     '                out["by_class"][c][m] += st(r, m) == "right_reason" and c in {x.get("class") for x in r["broken"][m].get("matched") or []}',
     '                out["by_class"][c][m] += st(r, m) == "right_reason"'),
    ("stats.mcnemar_constant", "scoring.py", "    return min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) * 0.5 ** n)", "    return 0.0"),
    ("stats.wilson_vacuous", "scoring.py", "    return [max(0.0, c - h), min(1.0, c + h)]", "    return [0.0, 1.0]"),
    ("stats.zero_n_as_zero", "scoring.py", '    return {"k": k, "n": n, "rate": (k / n if n else None), "wilson95": wilson(k, n),', '    return {"k": k, "n": n, "rate": (k / n if n else 0.0), "wilson95": wilson(k, n),'),
    ("match.frame_to_qos", "scoring.py", '    "frame_mismatch": [("ECM", "frame_mismatch", "edge")],', '    "frame_mismatch": [("ECM", "qos_reliability", "edge")],'),
    ("match.token_ignored", "scoring.py", '                        ok = (token_matches(f.get("token") or "", c["implicated_elements"], c["class"]) if how == "token"', '                        ok = (True if how == "token"'),
    ("match.semver_counts", "scoring.py", '    "element_removed_or_renamed": [("ECM", "field_break", "token")],', '    "element_removed_or_renamed": [("ECM", "field_break", "token"), ("ECM", "semver_major", "edge")],'),
    ("prov.always_verified", "scoring.py", '        if not prov.get(p):\n            return "unverified"', '        if False:\n            return "unverified"'),
    ("prov.ignore_adjudication", "scoring.py", '        if verdicts.get(p) in ("wrong", "unverifiable"):\n            return "unverified"', '        if False:\n            return "unverified"'),
    ("prov.grants_open_world", "scoring.py", '            if ((enc.get(side) or {}).get("_states") or {}).get("perm_grants") != "absent":\n                return "unverified"', '            if False:\n                return "unverified"'),
    ("wrapper.invent_semver", "scoring.py", "        if so is None or sn is None:\n            so = sn = None", "        if False:\n            so = sn = None"),
    ("switch.scored", "scoring.py", '        if operation == "SWITCH":\n            state = "not_supported"', '        if False:\n            state = "not_supported"'),
    ("agg.unassessable_dropped", "scoring.py", '    fails = [r for r in rows if r["outcome_class"] == "failure"]\n    if complete_case:', '    fails = [r for r in rows if r["outcome_class"] == "failure" and r["assembled_status"] == "done"]\n    if complete_case:'),
    ("agg.false_alarm_on_broken", "scoring.py", '        fa_obs = [r["case_id"] for r in ctl_obs if r["resolved"][m]["state"] in ("reject", "unassessable")]', '        fa_obs = [r["case_id"] for r in ctl_obs if r["broken"][m]["state"] != "accept"]'),
    ("agg.unassessable_control_not_fp", "scoring.py", '        fa_obs = [r["case_id"] for r in ctl_obs if r["resolved"][m]["state"] in ("reject", "unassessable")]', '        fa_obs = [r["case_id"] for r in ctl_obs if r["resolved"][m]["state"] == "reject"]'),
    ("agg.unassessable_warning_not_fp", "scoring.py", '                   if st(r, m) in ("right_reason", "unverified", "wrong_reason", "unassessable")]', '                   if st(r, m) in ("right_reason", "unverified", "wrong_reason")]'),
    ("agg.no_nesting", "scoring.py", '                nested = (a == "ECM" and bname in B.NESTED_IN_ECM)', '                nested = False'),
    ("agg.warning_not_fp", "scoring.py", '        fp = len(fa_obs) + len(fa_warn)', '        fp = len(fa_obs)'),
    ("base.nt_no_promotion", "baselines_v2.py", "            and not _types_compatible(out[\"msg_type\"], inp[\"msg_type\"]):", "            and out[\"msg_type\"] != inp[\"msg_type\"]:"),
    ("base.dq_no_durability", "baselines_v2.py", '            findings.append(_finding("dq_qos_durability", inp.get("role"), producer="volatile", consumer="transient_local"))', "            pass"),
    ("base.dq_no_deadline", "baselines_v2.py", "        if od is not None and idl is not None and od > idl:", "        if False:"),
    ("base.di_wildcard_rejects", "baselines_v2.py", '    if "*" in (a["value"], b["value"]):\n        return []', '    if False:\n        return []'),
    ("base.di_mixed_algorithms", "baselines_v2.py", '    if a.get("algorithm") != b.get("algorithm") or a.get("kind") != b.get("kind"):\n        return []', '    if False:\n        return []'),
    ("asm.ignore_element_sides", "assemble.py", '        if p_name and c_name and sides.get(p_name) == "consumes" and sides.get(c_name) == "provides":', '        if False:'),
    ("asm.pair_first_port", "assemble.py", '        if p.get("element") == element and p.get("side") == side:', '        if p.get("side") == side:'),
    ("asm.undetermined_as_absent", "assemble.py", '        return "absent" if el in nd else None', '        return "absent"'),
    ("asm.signature_not_normalised", "assemble.py", '        return {k: canonical_sig(v) for k, v in (d or {}).items()}', '        return {k: str(v) for k, v in (d or {}).items()}'),
    ("asm.canonical_keeps_macros", "assemble.py", '    s = _SIG_ATTR.sub(" ", s)', '    s = s'),
    ("asm.canonical_erases_everything", "assemble.py", '    return " ".join(s.rstrip(";{ ").split())', '    return ""'),
    ("asm.type_spelling_kept", "assemble.py", '"msg_type": canonical_type(p.get("msg_type"))', '"msg_type": p.get("msg_type")'),
    ("asm.consumer_task_is_producer", "assemble.py", '        tasks = {"producer": tid(p_desc), "consumer": tid(c_desc)}', '        tasks = {"producer": tid(p_desc), "consumer": tid(p_desc)}'),
    ("fold.substance_ignored", "adjudicate.py", '            if sf != "substantive" and not no_substance:', '            if False:'),
    ("fold.substance_split_counts", "adjudicate.py", '                sf = sc or "unverifiable"', '                sf = sc or "substantive"'),
    ("a1.packets_reshuffled", "adjudicate.py", '    if old_a1 and old_a1 != new_a1:', '    if False:'),
    ("a1.guard_after_delete", "adjudicate.py",
     '    old_a1 = {os.path.basename(f): json.load(open(f)) for f in glob.glob(os.path.join(ADJ, "packets", "A1_*.json"))}',
     '    [os.remove(f) for f in glob.glob(os.path.join(ADJ, "packets", "A*.json"))]\n    old_a1 = {}'),
    ("c3.adjudicated_walk", "scoring.py", '    sel = c3_selection(load_specs(False) if adjudicated else specs)', '    sel = c3_selection(specs)'),
    ("fold.missed_single_dropped", "adjudicate.py", '                elif c is None:\n                    split(iid, "missed", cls)\n                    add = False',
     '                elif True:\n                    add = False'),
    ("fold.missed_third_ignored", "adjudicate.py", '                    add = any(n.get("class") == cls for n in (c.get("missed_conditions") or []))', '                    add = True'),
    ("a3.one_packet", "adjudicate.py", '    for k in range(0, len(items_), 10):\n        out = os.path.join(ADJ, "packets", f"A3_{k // 10:02d}.json")\n        json.dump(items_[k:k + 10], open(out, "w"), indent=1)',
     '    for k in range(0, 1):\n        out = os.path.join(ADJ, "packets", "A3_00.json")\n        json.dump(items_, open(out, "w"), indent=1)'),
    ("a3.stale_kept", "adjudicate.py", '    for old in glob.glob(os.path.join(ADJ, "packets", "A3_*.json")):\n        os.remove(old)', '    for old in []:\n        os.remove(old)'),
    ("fold.adj1only_keeps_adj2", "adjudicate.py", '        r2, r3 = r1, {}', '        r3 = {}'),
    ("fold.adj1only_overwrites_primary", "adjudicate.py", '    out = os.path.join(HERE, NO_SUBSTANCE) if no_substance else (os.path.join(HERE, ADJ1_ONLY) if adj1_only else OUT)', '    out = OUT'),
    ("a2.positional_ids", "adjudicate.py", "        it = dict(it, item_id=f\"A2-{it['case_id']}-{it['composition']}-{it['method_label']}-{item_digest(it)}\")\n", ""),
    ("a2.single_score_dir", "adjudicate.py", 'SCORE_DIRS = ("scores_adjudicated", "scores_adjudicated_adj1only")', 'SCORE_DIRS = ("scores_adjudicated",)'),
    ("score.shared_dir", "scoring.py", '        score_dir = f"scores_{adj_dir}" if adjudicated else "scores"', '        score_dir = "scores"'),
    ("score.variant_reads_primary_overrides", "scoring.py", '        ov = os.path.join(HERE, adj_dir, "overrides.json")', '        ov = os.path.join(HERE, "adjudicated", "overrides.json")'),
    ("strata.same_repo_any", "scoring.py", '    return len(repos) >= 2 and all(repos) and len(set(repos)) == 1', '    return len(repos) >= 2 and len(set(repos)) == 1'),
    ("strata.same_repo_git_suffix", "scoring.py", '    repos = [r[:-4] if r.endswith(".git") else r for r in repos]', '    repos = list(repos)'),
    ("a1.pilot_included", "adjudicate.py", '        if s["case_id"] in pilot:\n            continue', '        if False:\n            continue'),
    ("freeze.ledger_by_basename", "freeze.py", '    rel = os.path.relpath(path, HERE)', '    rel = os.path.basename(path)'),
    ("qos.reads_explanation", "qos_literal.py", "    text, from_artifact = cited_text(task_id, prov, tasks_dir)\n",
     "    text, from_artifact = cited_text(task_id, prov, tasks_dir)\n    text = text + (prov or '') if text is not None else text\n"),
    ("qos.named_profile_literal", "qos_literal.py", '    return "named_profile" if NAMED_PROFILE.search(text) else "no_token"', '    return "literal" if NAMED_PROFILE.search(text) else "no_token"'),
    ("qos.producer_task_both_sides", "qos_literal.py", 'reason = classify(fld, v, _task_of(u, side), u["provenance"].get(path), tasks_dir)',
     'reason = classify(fld, v, _task_of(u, "producer"), u["provenance"].get(path), tasks_dir)'),
    ("qos.outside_snapshot", "qos_literal.py", "        if not f.startswith(snap + os.sep):\n            continue", "        if False:\n            continue"),
    ("qos.no_prose_in_artifacts", "qos_literal.py", '            pat = pat + "|" + PROSE[(field, value)]', '            pass'),
    ("qos.unit_changed_in_place", "qos_literal.py", "    u = copy.deepcopy(unit)", "    u = unit"),
    ("sens.excerpt_not_excluded", "scoring.py", '    rx = [r for r in rows if not r["excerpt_based"]]', '    rx = list(rows)'),
    ("sens.qos_reuses_primary", "scoring.py",
     '        rq, nulled = build_rows(specs, verdicts_all, pilot, s1_models, sel,\n'
     '                                transform=lambda comp, keep=keep: Q.null_composition(comp, keep, os.path.join(HERE, "s2_work", "tasks")))',
     '        rq, nulled = rows, []'),
    ("sens.qos_ignores_here", "scoring.py", 'Q.null_composition(comp, keep, os.path.join(HERE, "s2_work", "tasks"))', 'Q.null_composition(comp, keep)'),
    ("asm.pair_view_running_did", "assemble.py", '        built_view["definition_id"] = p_old.get("definition_id")', '        built_view["definition_id"] = p_run.get("definition_id")'),
    ("mat.excerpt_by_case", "materialize.py", '    return bool(unit.get("excerpt")) if unit.get("excerpt") is not None else unit.get("repo") is None', '    return True'),
    ("mat.refresh_dispatched", "materialize.py", '            if e["status"] in ("excerpt", "evidence_inadequate") and not _dispatched(tid):', '            if e["status"] in ("excerpt", "evidence_inadequate"):'),
    ("mat.drop_resolved_commit", "materialize.py", '                entry = {"task_id": tid, "unit": unit, "repo": repo, "revision": rev, "resolved_commit": commit,', '                entry = {"task_id": tid, "unit": unit, "repo": repo, "revision": rev, "resolved_commit": None,'),
    ("fold.third_ignored", "adjudicate.py", '            lf = la if la == lb else (c or {}).get("loudness", {}).get("verdict")', '            lf = la if la == lb else None'),
    ("fold.split_as_agree", "adjudicate.py", '            if la != lb and c is None:\n                split(iid, "loudness")', '            if False:\n                split(iid, "loudness")'),
    ("c3.no_cap", "scoring.py", '        if per_repo.get(repo, 0) >= C3_PER_REPO_CAP:', '        if False:'),
    ("c3.skip_gaps", "scoring.py", '        if spec is None:\n            first_missing = cid\n            break', '        if spec is None:\n            continue'),
    ("c3.h1_all_failures", "scoring.py", 'r["outcome_class"] == "failure" and r.get("c3_selected")]', 'r["outcome_class"] == "failure"]'),
    ("pilot.included", "scoring.py", '        if cid in pilot:\n            continue', '        if False:\n            continue'),
    ("mat.follow_symlinks", "materialize.py", '            if os.path.islink(p):\n                h.update(b"L" + os.readlink(p).encode())\n            else:\n                h.update(open(p, "rb").read())', '            if os.path.islink(p) and not os.path.exists(p):\n                h.update(b"L" + os.readlink(p).encode())\n            else:\n                h.update(open(p, "rb").read())'),
    ("qos.bare_ref_ignored", "qos_literal.py", "        elif last is not None:\n            refs.append((last, m.group(3)))", "        elif last is not None:\n            pass"),
    ("qos.bare_ref_no_boundary", "qos_literal.py", '_LINES + r"|(?<=[\\s(]):" + _LINES)', '_LINES + r"|:" + _LINES)'),
    ("frame.description_kept", "frame_literal.py", '    return "literal" if str(value) in text else "not_in_cited_lines"', '    return "literal"'),
    ("frame.tokens_nulled", "frame_literal.py", '    if value in TOKENS:\n        return "token"', '    if False:\n        return "token"'),
    ("frame.never_nulls", "frame_literal.py", '            p["frame"] = None\n', '            pass\n'),
    ("frame.unit_changed_in_place", "frame_literal.py", "    u = copy.deepcopy(unit)", "    u = unit"),
    ("sens.frame_reuses_primary", "scoring.py",
     '    rf, fnulled = build_rows(specs, verdicts_all, pilot, s1_models, sel,\n'
     '                             transform=lambda comp: FL.null_composition(comp, os.path.join(HERE, "s2_work", "tasks")))',
     '    rf, fnulled = rows, []'),
    ("fold.nosubstance_ignored", "adjudicate.py", '                if sf != "substantive" and not no_substance:', '                if sf != "substantive":'),
    ("fold.nosubstance_same_dir", "adjudicate.py", '    out = os.path.join(HERE, NO_SUBSTANCE) if no_substance else (os.path.join(HERE, ADJ1_ONLY) if adj1_only else OUT)', '    out = os.path.join(HERE, ADJ1_ONLY) if adj1_only else OUT'),
    ("pkt.drop_confidential", "build_packets.py", '    if isinstance(raw, str):\n        return [], raw.strip().lower() or "unspecified"', '    if isinstance(raw, str):\n        return None, "dropped"'),
]


def run_tests(pkg_dir):
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "test_scoring.py"],
                       cwd=pkg_dir, capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    last = (r.stdout.strip().splitlines() or [""])[-1]
    return r.returncode, last, r.stdout


def classify_run(rc: int, out: str) -> str:
    """killed only when a test's own expectation fails (an assert, or pytest.raises that did not
    raise); an exception from the code under test, a syntax, import or collection error is an error."""
    if rc == 0:
        return "SURVIVED"
    last = (out.strip().splitlines() or [""])[-1]
    asserted = re.search(r"^E\s+(assert\b|AssertionError|Failed: DID NOT RAISE)", out, re.M) is not None
    return "killed" if asserted and " error" not in last else "ERROR"


def main():
    # Without --report nothing is written (R3, peer review m9: the old default wrote MUTATIONS.md into whatever
    # directory the probe ran from, which is how a seat overwrote the project's copy in R2).
    report = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    root = tempfile.mkdtemp(prefix="pbv2_mut_")
    base = os.path.join(root, "base", "pathb_v2")
    shutil.copytree(HERE, base, symlinks=True,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "s2_work", "snapshots"))
    os.symlink(PB, os.path.join(root, "base", "pathb"))
    code_hash = hashlib.sha256(b"".join(open(os.path.join(HERE, f), "rb").read()
                                        for f in CODE_FILES)).hexdigest()
    rc, last, _ = run_tests(base)
    if rc != 0:
        shutil.rmtree(root, ignore_errors=True)
        raise SystemExit(f"baseline fails ({last}); no mutation result would mean anything")
    lines = [f"# Mutation inventory\n\nCode hash ({', '.join(CODE_FILES)}): `{code_hash}`\n",
             f"Baseline: pass ({last})\n", "Killed means a test failed on an assertion; ERROR means the run failed some other way and is not a kill.\n",
             "| mutation | file | result | tests |", "|---|---|---|---|"]
    killed = survived = errored = 0
    for name, fn, a, b in MUTATIONS:
        d = os.path.join(root, name)
        shutil.copytree(os.path.join(root, "base"), d, symlinks=True)
        p = os.path.join(d, "pathb_v2", fn)
        s = open(p).read()
        if s.count(a) != 1:
            lines.append(f"| {name} | {fn} | NOT APPLIED (anchor {s.count(a)}x) | |")
            continue
        open(p, "w").write(s.replace(a, b))
        rc, last, out = run_tests(os.path.join(d, "pathb_v2"))
        status = classify_run(rc, out)
        killed += status == "killed"
        survived += status == "SURVIVED"
        errored += status == "ERROR"
        lines.append(f"| {name} | {fn} | {status} | {last} |")
    not_applied = len(MUTATIONS) - killed - survived - errored
    lines.append(f"\n{killed} killed, {survived} survived, {errored} error, {not_applied} not applied, {len(MUTATIONS)} mutations.\n")
    if report:
        open(report, "w").write("\n".join(lines))
    shutil.rmtree(root, ignore_errors=True)
    print("\n".join(lines if report is None else lines[-1:]))
    sys.exit(1 if (survived or errored or not_applied) else 0)


if __name__ == "__main__":
    main()
