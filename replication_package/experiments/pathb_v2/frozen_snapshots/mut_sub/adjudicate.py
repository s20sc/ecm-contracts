"""Adjudication pipeline (PROTOCOL.md Section 11).

  python3 adjudicate.py items      -> adjudication/packets/A1_*.json, A2_*.json (neutral method labels)
  python3 adjudicate.py fold       -> adjudicated/overrides.json, provenance_verdicts.json, kappa.json

Two initial adjudicators (ADJ1, ADJ2) write adjudication/<who>/<item_id>.json; a third
(ADJ3) resolves splits. Records are never modified. `fold` applies the decision rules
deterministically and writes the adjudicated inputs that scoring.py --adjudicated reads.
"""
import glob
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ADJ = os.path.join(HERE, "adjudication")
OUT = os.path.join(HERE, "adjudicated")
METHODS = ["ECM", "NT", "DI", "DQ", "SV"]


def pilot_cases():
    """Quarantined pilot cases (PROTOCOL.md Section 14): adjudicated in the pilot, never as results."""
    f = os.path.join(HERE, "pilot", "PILOT_CASES.json")
    return set(json.load(open(f))["quarantined_pilot_cases"]) if os.path.exists(f) else set()


def extra_cases():
    """Cases added to A1 because another S1 judgment on the same or a same-mechanism source reached
    the opposite eligibility (ledger/a1_extra.json); added on top of the seeded sample, reported as such."""
    f = os.path.join(HERE, "ledger", "a1_extra.json")
    return [e["case_id"] for e in json.load(open(f))["cases"]] if os.path.exists(f) else []


def seed():
    f = os.path.join(HERE, "FREEZE.json")
    return json.load(open(f))["seed"] if os.path.exists(f) else 20260925


def load_dir(pattern):
    return {json.load(open(f))["item_id"]: json.load(open(f)) for f in sorted(glob.glob(pattern))}


def items():
    """Build A1 items (all eligible C3 and C3-neutral cases; all eligible C1/C2 failures; a seeded 20 %
    of E2 exclusions per corpus; then the cases in ledger/a1_extra.json not already present) and A2 items
    (every provisional right_reason finding and control false alarm). Pilot cases are left out."""
    rng = random.Random(f"{seed()}:adjudication")
    labels = METHODS[:]
    rng.shuffle(labels)
    label_of = {m: f"M{i + 1}" for i, m in enumerate(labels)}
    os.makedirs(os.path.join(ADJ, "packets"), exist_ok=True)
    for old in glob.glob(os.path.join(ADJ, "packets", "A*.json")):
        os.remove(old)  # packets are regenerated as a set; a stale one would be dispatched by mistake
    json.dump(label_of, open(os.path.join(HERE, "ledger", "method_labels.json"), "w"), indent=1)
    a1, a2 = [], []
    excl_by_corpus = {}
    ledger_path = os.path.join(HERE, "ledger", "tasks.json")
    ledger = json.load(open(ledger_path))["tasks"] if os.path.exists(ledger_path) else {}

    def case_tasks(cid):
        return [{"task_id": t, "unit": e["unit"], "revision": e["revision"], "resolved_commit": e.get("resolved_commit"),
                 "status": e["status"], "workspace": f"s2_work/tasks/{t}"} for t, e in sorted(ledger.items()) if cid in e.get("cases", [])]

    def evidence(cid, composition, method, finding):
        """Provenance entries behind the values that made the finding fire, from the assembled unit."""
        import scoring as S
        import baselines_v2 as B
        asm = json.load(open(os.path.join(HERE, "assembled", f"{cid}.json")))
        units = ((asm.get("compositions") or {}).get(composition) or {}).get("units") or []
        kind = finding.get("unit_kind")
        if kind == "upgrade":
            unit = next((u for u in units if u.get("kind") == "upgrade"), None)
        else:
            unit = next((u for u in units if u.get("kind") == kind and u.get("element") == finding.get("element")), None)
            if unit is None:
                unit = next((u for u in units if u.get("element") == finding.get("element")), None)
        paths = (S.ecm_trigger_paths(finding["rule"], finding.get("token")) if method == "ECM"
                 else B.trigger_paths(finding["rule"], "producer.outputs[0]", "consumer.inputs[0]"))
        prov = (unit or {}).get("provenance") or {}
        return {"unit_kind": (unit or {}).get("kind"), "unit_element": (unit or {}).get("element"),
                "trigger_paths": paths, "provenance": {p: prov.get(p) for p in paths},
                "encoding": (unit or {}).get("encoding")}
    pilot = pilot_cases()
    for f in sorted(glob.glob(os.path.join(HERE, "specs", "*.json"))):
        s = json.load(open(f))
        if s["case_id"] in pilot:
            continue
        if s.get("eligible"):
            # C3-neutral is adjudicated like C3: the enrichment comparison sets the two eligible shares side by side
            if s["corpus"] in ("C3", "C3N") or s.get("outcome_class") == "failure":
                a1.append({"item_id": f"A1-{s['case_id']}", "kind": "A1", "case_id": s["case_id"], "spec": f"specs/{s['case_id']}.json"})
        elif (s.get("eligibility") or {}).get("E2", {}).get("pass") is False:
            excl_by_corpus.setdefault(s["corpus"], []).append(s["case_id"])
    for corpus, ids in excl_by_corpus.items():
        rng.shuffle(ids)
        for cid in ids[:max(1, round(0.2 * len(ids)))]:
            a1.append({"item_id": f"A1-{cid}", "kind": "A1", "case_id": cid, "spec": f"specs/{cid}.json", "sample": "E2_exclusion_20pct"})
    have = {it["case_id"] for it in a1}
    for cid in extra_cases():
        if cid in have or cid in pilot:
            continue
        if not os.path.exists(os.path.join(HERE, "specs", f"{cid}.json")):
            raise SystemExit(f"ledger/a1_extra.json names {cid}, which has no spec")
        a1.append({"item_id": f"A1-{cid}", "kind": "A1", "case_id": cid, "spec": f"specs/{cid}.json", "sample": "added"})
        have.add(cid)
    for f in sorted(glob.glob(os.path.join(HERE, "scores", "*.json"))):
        r = json.load(open(f))
        if r["case_id"] in pilot:
            continue
        for m in METHODS:
            b = r["broken"].get(m, {})
            if b.get("state") == "right_reason":
                for k, mt in enumerate(b.get("matched", [])):
                    fi = next((x for x in b["findings"] if x["rule"] == mt["rule"] and x.get("token") == mt.get("token")), None)
                    a2.append({"item_id": f"A2-{r['case_id']}-broken-{label_of[m]}-{k}", "kind": "A2", "case_id": r["case_id"],
                               "composition": "broken", "method_label": label_of[m], "rule": mt["rule"], "element": mt.get("element"),
                               "token": mt.get("token"), "finding": fi, "assembled": f"assembled/{r['case_id']}.json",
                               "evidence": evidence(r["case_id"], "broken", m, fi), "tasks": case_tasks(r["case_id"])})
            if r.get("resolved") and r["resolved"].get(m, {}).get("state") == "reject":
                for k, fi in enumerate(r["resolved"][m].get("findings", [])):
                    a2.append({"item_id": f"A2-{r['case_id']}-resolved-{label_of[m]}-{k}", "kind": "A2", "case_id": r["case_id"],
                               "composition": "resolved", "method_label": label_of[m], "rule": fi["rule"], "element": fi.get("element"),
                               "token": fi.get("token"), "finding": fi, "assembled": f"assembled/{r['case_id']}.json",
                               "evidence": evidence(r["case_id"], "resolved", m, fi), "tasks": case_tasks(r["case_id"])})
    # One A2 item per distinct evidence: findings of one method that fire on the same triggering
    # values (a definition mismatch repeated on every field port of one message) are adjudicated
    # once; the item lists the elements it covers.
    merged, seen = [], {}
    for it in a2:
        key = (it["case_id"], it["composition"], it["method_label"], it["rule"],
               json.dumps((it.get("evidence") or {}).get("provenance"), sort_keys=True))
        if key in seen:
            seen[key].setdefault("also_covers", []).append({"item_id": it["item_id"], "element": it.get("element"), "token": it.get("token")})
            continue
        seen[key] = it
        merged.append(it)
    a2 = merged
    for k in range(0, len(a1), 10):
        json.dump(a1[k:k + 10], open(os.path.join(ADJ, "packets", f"A1_{k // 10:02d}.json"), "w"), indent=1)
    for k in range(0, len(a2), 15):
        json.dump(a2[k:k + 15], open(os.path.join(ADJ, "packets", f"A2_{k // 15:02d}.json"), "w"), indent=1)
    print(len(a1), "A1 items;", len(a2), "A2 items")


def agree(a, b, key):
    return (a or {}).get(key) == (b or {}).get(key)


def roles():
    """Adjudicator roles -> record directory names (ledger/adjudicators.json; defaults below)."""
    f = os.path.join(HERE, "ledger", "adjudicators.json")
    d = {"ADJ1": 'adj1', "ADJ2": 'withdrawn_google', "ADJ3": 'adj1_repeat'}
    if os.path.exists(f):
        d.update(json.load(open(f)))
    return d


def fold():
    os.makedirs(OUT, exist_ok=True)
    who = roles()
    r1, r2, r3 = (load_dir(os.path.join(ADJ, who[r], "*.json")) for r in ("ADJ1", "ADJ2", "ADJ3"))
    overrides, verdicts = {}, {}
    kappa_in = {"eligibility": [], "class": [], "loudness": [], "resolution": [], "provenance": [], "substance": []}
    substance_final = {}
    log, splits = [], []

    def split(iid, domain, detail=None):
        splits.append({"item": iid, "domain": domain, "detail": detail})
    for iid in sorted(set(r1) | set(r2)):
        a, b, c = r1.get(iid), r2.get(iid), r3.get(iid)
        if a is None or b is None:
            log.append({"item": iid, "decision": "incomplete"})
            continue
        if a["kind"] == "A1":
            cid = a["case_id"]
            spec = json.load(open(os.path.join(HERE, "specs", f"{cid}.json")))
            ov = {}
            va, vb = a["eligibility"]["verdict"], b["eligibility"]["verdict"]
            kappa_in["eligibility"].append((va, vb))
            final = va if va == vb else (c or {}).get("eligibility", {}).get("verdict")
            if va != vb and c is None:
                split(iid, "eligibility")
            if final == "disagree":
                ov["eligible"] = not spec.get("eligible")
                ov["ineligible_reason"] = (a if va == "disagree" else b)["eligibility"].get("reason_code")
            if not spec.get("eligible"):
                # An excluded case has no conditions, loudness, or resolution to review; records that
                # "agree" with those empty fields must not enter the kappa for them.
                if ov:
                    overrides[cid] = ov
                pending = [s for s in splits if s["item"] == iid]
                log.append({"item": iid, "decision": "split_pending" if pending else ("override" if ov else "confirmed"),
                            "override": ov, "splits": pending})
                continue
            la, lb = a["loudness"]["verdict"], b["loudness"]["verdict"]
            kappa_in["loudness"].append((la, lb))
            lf = la if la == lb else (c or {}).get("loudness", {}).get("verdict")
            if la != lb and c is None:
                split(iid, "loudness")
            if lf == "disagree":
                src = a if la == "disagree" else b
                ov["loudness"] = src["loudness"].get("proposed") or spec.get("loudness")
            conds = json.loads(json.dumps(spec.get("failed_conditions") or []))
            changed = False
            for i, cnd in enumerate(conds):
                fa = next((x for x in a.get("failed_conditions", []) if x.get("index") == i), {})
                fb = next((x for x in b.get("failed_conditions", []) if x.get("index") == i), {})
                kappa_in["class"].append((fa.get("class_verdict"), fb.get("class_verdict")))
                cv = fa.get("class_verdict") if fa.get("class_verdict") == fb.get("class_verdict") else\
                    next((x.get("class_verdict") for x in (c or {}).get("failed_conditions", []) if x.get("index") == i), None)
                if fa.get("class_verdict") != fb.get("class_verdict") and c is None:
                    split(iid, "class", i)
                if fa.get("elements_verdict") != fb.get("elements_verdict") and c is None:
                    split(iid, "elements", i)
                if cv == "disagree":
                    prop = (fa if fa.get("class_verdict") == "disagree" else fb).get("proposed_class")
                    if prop:
                        cnd["class"], changed = prop, True
                ev = fa.get("elements_verdict") if fa.get("elements_verdict") == fb.get("elements_verdict") else\
                    next((x.get("elements_verdict") for x in (c or {}).get("failed_conditions", []) if x.get("index") == i), None)
                if ev == "disagree":
                    prop = (fa if fa.get("elements_verdict") == "disagree" else fb).get("proposed_elements")
                    if prop:
                        cnd["implicated_elements"], changed = prop, True
            for m in (a.get("missed_conditions") or []):
                if any(n.get("class") == m.get("class") for n in (b.get("missed_conditions") or [])):
                    conds.append({"class": m["class"], "implicated_elements": m.get("implicated_elements", []),
                                  "quote": m.get("quote"), "url": m.get("url"), "added_by": "adjudication"})
                    changed = True
            if changed:
                ov["failed_conditions"] = conds
            ra, rb = a["resolution"]["verdict"], b["resolution"]["verdict"]
            kappa_in["resolution"].append((ra, rb))
            rf = ra if ra == rb else (c or {}).get("resolution", {}).get("verdict")
            if ra != rb and c is None:
                split(iid, "resolution")
            if rf == "disagree":
                prop = (a if ra == "disagree" else b)["resolution"].get("proposed")
                if prop:
                    ov["resolution"] = dict(spec.get("resolution") or {}, status=prop)
            if ov:
                overrides[cid] = ov
            pending = [s for s in splits if s["item"] == iid]
            log.append({"item": iid, "decision": "split_pending" if pending else ("override" if ov else "confirmed"),
                        "override": ov, "splits": pending})
        else:
            cid, compn = a["case_id"], a["composition"]
            for va in a.get("values", []):
                vb = next((x for x in b.get("values", []) if x["path"] == va["path"]), None)
                if vb is None:
                    continue
                kappa_in["provenance"].append((va["verdict"], vb["verdict"]))
                if va["verdict"] == vb["verdict"]:
                    final = va["verdict"]
                else:
                    vc = next((x for x in (c or {}).get("values", []) if x["path"] == va["path"]), None)
                    if vc is None:
                        split(iid, "provenance", va["path"])
                    final = vc["verdict"] if vc else "unverifiable"
                if final != "verified":
                    verdicts.setdefault(cid, {}).setdefault(compn, {})[va["path"]] = final
            # Substance of an UPGRADE signature change (question 4): a change that exists only in how
            # two S2 runs transcribed one declaration must not count as a changed field. A missing
            # answer counts as unverifiable; anything but `substantive` demotes the path.
            need = sorted({v.get("path") for v in (a.get("values") or []) + (b.get("values") or [])
                           if str(v.get("path", "")).startswith("ver_delta.changed_fields[")})
            for path in need:
                sa = next((x.get("verdict") for x in a.get("substance") or [] if x.get("path") == path), "unverifiable")
                sb = next((x.get("verdict") for x in b.get("substance") or [] if x.get("path") == path), "unverifiable")
                kappa_in["substance"].append((sa, sb))
                if sa == sb:
                    sf = sa
                else:
                    sc = next((x.get("verdict") for x in (c or {}).get("substance") or [] if x.get("path") == path), None)
                    if sc is None:
                        split(iid, "substance", path)
                    sf = sc or "unverifiable"
                substance_final.setdefault(cid, {}).setdefault(compn, {})[path] = sf
                if sf != "substantive":
                    cur = verdicts.setdefault(cid, {}).setdefault(compn, {})
                    if cur.get(path) != "wrong":
                        cur[path] = "wrong" if sf == "transcription_only" else "unverifiable"
            oa, ob = a.get("operation_edge", {}).get("verdict"), b.get("operation_edge", {}).get("verdict")
            if oa != ob and c is None:
                split(iid, "operation_edge")
            if oa == ob == "disagree" or (oa != ob and (c or {}).get("operation_edge", {}).get("verdict") == "disagree"):
                verdicts.setdefault(cid, {}).setdefault(compn, {})["_operation_edge"] = "disagree"
            pending = [s for s in splits if s["item"] == iid]
            log.append({"item": iid, "decision": "split_pending" if pending else "provenance_folded", "splits": pending})
    json.dump(overrides, open(os.path.join(OUT, "overrides.json"), "w"), indent=1)
    json.dump(verdicts, open(os.path.join(OUT, "provenance_verdicts.json"), "w"), indent=1)
    json.dump(substance_final, open(os.path.join(OUT, "substance_verdicts.json"), "w"), indent=1)
    json.dump({k: cohen_kappa(v) for k, v in kappa_in.items()}, open(os.path.join(OUT, "kappa.json"), "w"), indent=1)
    json.dump(log, open(os.path.join(OUT, "fold_log.json"), "w"), indent=1)
    json.dump(splits, open(os.path.join(OUT, "splits.json"), "w"), indent=1)
    print(len(overrides), "spec overrides;", sum(len(x) for v in verdicts.values() for x in v.values()), "provenance demotions;",
          len({s["item"] for s in splits}), "items split and pending the third adjudicator")


def third():
    """Steward: build the third adjudicator's packet from the pending splits (same item objects)."""
    splits = json.load(open(os.path.join(OUT, "splits.json")))
    want = {s["item"] for s in splits}
    items_ = []
    seen = set()
    for f in sorted(glob.glob(os.path.join(ADJ, "packets", "A[12]_*.json"))):
        for it in json.load(open(f)):
            if it["item_id"] in want and it["item_id"] not in seen:
                items_.append(it)
                seen.add(it["item_id"])
    out = os.path.join(ADJ, "packets", "A3_00.json")
    json.dump(items_, open(out, "w"), indent=1)
    print(len(items_), "split items ->", out)


def cohen_kappa(pairs):
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    n = len(pairs)
    if n == 0:
        return {"n": 0, "kappa": None}
    cats = sorted({x for p in pairs for x in p})
    po = sum(a == b for a, b in pairs) / n
    pe = sum((sum(a == k for a, _ in pairs) / n) * (sum(b == k for _, b in pairs) / n) for k in cats)
    return {"n": n, "observed_agreement": po, "kappa": (po - pe) / (1 - pe) if pe < 1 else None}


def build_workdir(packet, who):
    """An adjudicator's workspace holds only what its packet needs: the packet, the eligibility
    tree, the specs and artifacts of its cases, and for A2 the assembled compositions and the
    task workspaces (snapshot or artifact) the items cite. Scores, results, other adjudicators'
    records and the rest of the tree are outside it. Records are written inside the workspace
    and copied out by `collect` (never overwriting an existing record)."""
    import shutil
    items_ = json.load(open(os.path.join(ADJ, "packets", f"{packet}.json")))
    wd = os.path.join(ADJ, "work", f"{packet}.{who}")
    shutil.rmtree(wd, ignore_errors=True)
    os.makedirs(os.path.join(wd, "specs")); os.makedirs(os.path.join(wd, "artifacts")); os.makedirs(os.path.join(wd, "prompts"))
    os.makedirs(os.path.join(wd, "adjudication", "packets"))
    shutil.copy(os.path.join(HERE, "prompts", "S1_specify.md"), os.path.join(wd, "prompts", "S1_specify.md"))
    shutil.copy(os.path.join(ADJ, "packets", f"{packet}.json"), os.path.join(wd, "adjudication", "packets", f"{packet}.json"))
    os.makedirs(os.path.join(wd, "adjudication", who))  # records are written here, then collected
    for it in items_:
        cid = it["case_id"]
        for sub, name in (("specs", f"{cid}.json"), ("artifacts", f"{cid}.txt")):
            src = os.path.join(HERE, sub, name)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(wd, sub, name))
        if it["kind"] == "A2":
            os.makedirs(os.path.join(wd, "assembled"), exist_ok=True)
            shutil.copy(os.path.join(HERE, "assembled", f"{cid}.json"), os.path.join(wd, "assembled", f"{cid}.json"))
            for t in it.get("tasks", []):
                src = os.path.join(HERE, "s2_work", "tasks", t["task_id"])
                dst = os.path.join(wd, "s2_work", "tasks", t["task_id"])
                if os.path.isdir(src) and not os.path.exists(dst):
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("DISPATCHED", "S2_PROMPT.md"))
    shutil.copy(os.path.join(HERE, "definition_hash.py"), os.path.join(wd, "definition_hash.py"))
    return wd


def collect(packet, who):
    """Steward: copy the records an adjudicator wrote in its workspace into adjudication/<who>/.
    An existing record is never overwritten (records are immutable)."""
    import shutil
    src = os.path.join(ADJ, "work", f"{packet}.{who}", "adjudication", who)
    dst = os.path.join(ADJ, who)
    os.makedirs(dst, exist_ok=True)
    n = 0
    for f in sorted(glob.glob(os.path.join(src, "*.json"))):
        out = os.path.join(dst, os.path.basename(f))
        if os.path.exists(out):
            print("kept existing", os.path.basename(f))
            continue
        json.load(open(f))  # must parse
        shutil.copy(f, out)
        n += 1
    print(n, "records collected from", packet, who)


def prompt(packet, who):
    """Steward: build the adjudicator's workspace and fill the prompt for it; prints the prompt path."""
    # The real path: codex's sandbox refuses a writable root reached through a symlink
    # (adjudication/work points to local disk), so the prompt must name the resolved directory.
    wd = os.path.realpath(build_workdir(packet, who))
    os.makedirs(os.path.join(ADJ, "prompts"), exist_ok=True)
    text = open(os.path.join(HERE, "prompts", "A_adjudicate.md")).read()
    text = text.replace("{PB2}", wd).replace("{INPUT}", os.path.join(wd, "adjudication", "packets", f"{packet}.json")).replace("{WHO}", who)
    out = os.path.join(ADJ, "prompts", f"{packet}.{who}.md")
    open(out, "w").write(text)
    print(out)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "prompt":
        prompt(sys.argv[2], sys.argv[3])
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "collect":
        collect(sys.argv[2], sys.argv[3])
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "third":
        third()
        sys.exit(0)
    {"items": items, "fold": fold}[sys.argv[1]]()
