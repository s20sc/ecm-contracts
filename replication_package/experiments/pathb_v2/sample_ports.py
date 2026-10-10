"""Seeded 15 % port sample for the provenance-agreement check of PROTOCOL.md (RQ4), and its adjudication.

  python3 sample_ports.py                 # draw only, print the sample size and value counts, write nothing
  python3 sample_ports.py --write         # write reliability/port_sample.json (the draw)
  python3 sample_ports.py packets         # write adjudication/packets/P_00.json ... from the draw
  python3 sample_ports.py prompt P_00 adj1   # build the adjudicator's workspace and prompt; prints the prompt path
  python3 sample_ports.py collect P_00 adj1  # copy the records it wrote into adjudication/ports/<who>/
  python3 sample_ports.py repack adj2     # packets PR_ADJ2_00 ... of the items that seat has no record for
  python3 sample_ports.py third           # packets PT_00 ... of the ports the two initial seats judged differently
  python3 sample_ports.py fold            # agreement of described values with adjudicated provenance
                                          # -> reliability/port_sample_agreement.json

Records live in adjudication/ports/<who>/, apart from the A1/A2 records of adjudicate.py, whose fold reads
every file in adjudication/<who>/. Adjudication follows PROTOCOL.md Section 11: two initial seats (ADJ1,
ADJ2) judge every value; a value they judge differently goes to the third seat (ADJ3), which receives the
same item objects and never sees the initial records; its verdict decides that value. Agreement (kappa) is
computed from the initial records.

The frame is every port of every returned description (status done or excerpt) that serves at least one
non-pilot case, accepted compositions included. The draw is a seeded shuffle of the frame (seed string
in SEED, same convention as calibrate.py), truncated to 15 %. Each drawn item carries the port's non-null
field values and the provenance strings the description recorded for them, so an adjudicator can check
each value against the snapshot without seeing the case. Packets hold PACKET_SIZE ports each; an
adjudicator's workspace holds only the prompt, its packet, and the cited task workspaces' snapshot or
artifact (never the description, the case, or other adjudicators' records). Reporting only: nothing in
the scoring pipeline reads these files.
"""
from __future__ import annotations

import glob
import json
import os
import random
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ADJ = os.path.join(HERE, "adjudication")
SEED = "20260925:port_sample"
SHARE = 0.15
PACKET_SIZE = 10
FIELDS = ["msg_type", "frame", "units", "qos.reliability", "qos.durability", "qos.deadline_ms", "rate_hz", "definition_id"]
SAMPLE = os.path.join(HERE, "reliability", "port_sample.json")
AGREEMENT = os.path.join(HERE, "reliability", "port_sample_agreement.json")
PORTS = os.path.join(ADJ, "ports")
SEATS = {"ADJ1": 'adj1', "ADJ2": 'adj2', "ADJ3": 'adj3'}
ROLE = {v: k for k, v in SEATS.items()}
VERDICTS = ("verified", "wrong", "unverifiable")


def field_value(port: dict, field: str):
    v = port
    for k in field.split("."):
        v = (v or {}).get(k) if isinstance(v, dict) else None
    return None if v in (None, "") else v


def frame() -> list:
    led = json.load(open(os.path.join(HERE, "ledger", "tasks.json")))["tasks"]
    pilot = set(json.load(open(os.path.join(HERE, "pilot", "PILOT_CASES.json")))["quarantined_pilot_cases"])
    items = []
    for tid in sorted(led):
        e = led[tid]
        cases = [c for c in e.get("cases", []) if c not in pilot]
        if e["status"] not in ("done", "excerpt") or not cases:
            continue
        path = os.path.join(HERE, "s2_work", "tasks", tid, "recon", f"{tid}.json")
        if not os.path.exists(path):
            continue
        r = json.load(open(path))
        prov = r.get("provenance") or {}
        for i, port in enumerate(r.get("ports") or []):
            values = {f: field_value(port, f) for f in FIELDS}
            values = {f: v for f, v in values.items() if v is not None}
            items.append({
                "task_id": tid, "cases": cases, "kind": e["status"], "ros_generation": e.get("ros_generation"),
                "port_index": i, "element": port.get("element"), "side": port.get("side"),
                "values": values,
                "provenance": {f: prov.get(f"ports[{i}].{f}") for f in values},
            })
    return items


def draw(items: list) -> list:
    rng = random.Random(SEED)
    order = list(range(len(items)))
    rng.shuffle(order)
    k = round(SHARE * len(items))
    return [dict(items[j], draw_rank=n) for n, j in enumerate(order[:k])]


def summary(items: list, sample: list) -> dict:
    n_val = sum(len(x["values"]) for x in sample)
    n_with = sum(1 for x in sample if x["values"])
    n_missing_prov = sum(1 for x in sample for f, p in x["provenance"].items() if not p)
    return {"seed": SEED, "share": SHARE, "frame_ports": len(items), "sample_ports": len(sample),
            "sample_ports_with_values": n_with, "sample_values": n_val, "values_without_provenance": n_missing_prov}


def cmd_draw(write: bool) -> None:
    items = frame()
    sample = draw(items)
    out = dict(summary(items, sample), items=sample)
    print(f"frame {out['frame_ports']} ports; sample {out['sample_ports']} ports, {out['sample_ports_with_values']} with at least "
          f"one value, {out['sample_values']} values to verify, {out['values_without_provenance']} of them without a provenance string")
    if write:
        os.makedirs(os.path.dirname(SAMPLE), exist_ok=True)
        json.dump(out, open(SAMPLE, "w"), indent=1)
        print("wrote", SAMPLE)


def cmd_packets() -> None:
    """Ports with at least one value, PACKET_SIZE per packet, in draw order. A port without a value has
    nothing to verify and is counted in the draw only."""
    sample = json.load(open(SAMPLE))["items"]
    todo = [x for x in sample if x["values"]]
    os.makedirs(os.path.join(ADJ, "packets"), exist_ok=True)
    n = 0
    for k in range(0, len(todo), PACKET_SIZE):
        pk = f"P_{k // PACKET_SIZE:02d}"
        items = [{"item_id": f"P-{x['task_id']}-{x['port_index']}", "kind": "P", "task_id": x["task_id"],
                  "task_kind": x["kind"], "port_index": x["port_index"], "element": x["element"], "side": x["side"],
                  "values": x["values"], "provenance": x["provenance"]} for x in todo[k:k + PACKET_SIZE]]
        path = os.path.join(ADJ, "packets", f"{pk}.json")
        if os.path.exists(path):
            print("kept existing", pk); n += 1; continue
        json.dump(items, open(path, "w"), indent=1); n += 1
    print(f"{n} packets of up to {PACKET_SIZE} ports ({len(todo)} ports with values) under adjudication/packets/P_*.json")


def build_workdir(packet: str, who: str) -> str:
    """The adjudicator's workspace: the packet, the prompt, and each cited task's snapshot (linked, read only)
    or artifact, with the hashing tool. No description, no case, no other adjudicator's records."""
    items = json.load(open(os.path.join(ADJ, "packets", f"{packet}.json")))
    wd = os.path.join(ADJ, "work", f"{packet}.{who}")
    shutil.rmtree(wd, ignore_errors=True)
    os.makedirs(os.path.join(wd, "adjudication", "packets"))
    os.makedirs(os.path.join(wd, "adjudication", who))
    os.makedirs(os.path.join(wd, "prompts"))
    shutil.copy(os.path.join(ADJ, "packets", f"{packet}.json"), os.path.join(wd, "adjudication", "packets", f"{packet}.json"))
    shutil.copy(os.path.join(HERE, "prompts", "P_ports.md"), os.path.join(wd, "prompts", "P_ports.md"))
    shutil.copy(os.path.join(HERE, "definition_hash.py"), os.path.join(wd, "definition_hash.py"))
    for it in items:
        t = it["task_id"]
        src = os.path.join(HERE, "s2_work", "tasks", t)
        dst = os.path.join(wd, "s2_work", "tasks", t)
        os.makedirs(dst, exist_ok=True)
        for name in ("snapshot", "artifact.txt"):
            s = os.path.join(src, name)
            if os.path.exists(s) and not os.path.exists(os.path.join(dst, name)):
                if os.path.isdir(s):
                    os.symlink(os.path.realpath(s), os.path.join(dst, name))
                else:
                    shutil.copy(s, os.path.join(dst, name))
    return wd


def cmd_prompt(packet: str, who: str) -> None:
    wd = os.path.realpath(build_workdir(packet, who))
    os.makedirs(os.path.join(ADJ, "prompts"), exist_ok=True)
    text = open(os.path.join(HERE, "prompts", "P_ports.md")).read()
    text = text.replace("{PB2}", wd).replace("{INPUT}", os.path.join(wd, "adjudication", "packets", f"{packet}.json")).replace("{WHO}", who)
    out = os.path.join(ADJ, "prompts", f"{packet}.{who}.md")
    open(out, "w").write(text)
    print(out)


def cmd_collect(packet: str, who: str) -> None:
    """Copy the records a seat wrote for one packet into adjudication/ports/<who>/. A record is collected
    only if its file name is the item_id it carries and that item belongs to the packet; anything else is
    reported and left in the workspace. An existing record is never overwritten."""
    src = os.path.join(ADJ, "work", f"{packet}.{who}", "adjudication", who)
    dst = os.path.join(PORTS, who)
    os.makedirs(dst, exist_ok=True)
    ids = {it["item_id"] for it in json.load(open(os.path.join(ADJ, "packets", f"{packet}.json")))}
    n = 0
    for f in sorted(glob.glob(os.path.join(src, "*.json"))):
        base = os.path.basename(f)[:-5]
        rec = json.load(open(f))
        if base not in ids or rec.get("item_id") != base:
            print(f"not collected: {os.path.basename(f)} (item_id {rec.get('item_id')!r}; "
                  f"{'in' if base in ids else 'not in'} packet {packet})")
            continue
        out = os.path.join(dst, os.path.basename(f))
        if os.path.exists(out):
            print("kept existing", os.path.basename(f)); continue
        shutil.copy(f, out); n += 1
    missing = sorted(ids - {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(dst, "P-*.json"))})
    print(n, "records collected from", packet, who, "| items of this packet still without a record:", missing or "none")


def load_records(who: str) -> dict:
    return {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(os.path.join(PORTS, who, "P-*.json"))}


def verdict_of(rec, field):
    return next((v.get("verdict") for v in (rec or {}).get("values", []) if v.get("field") == field), None)


def initial_items() -> list:
    """Every port item of the P_ packets, in packet order."""
    out = []
    for f in sorted(glob.glob(os.path.join(ADJ, "packets", "P_*.json"))):
        out.extend(json.load(open(f)))
    return out


def write_packets(prefix: str, items_: list) -> list:
    os.makedirs(os.path.join(ADJ, "packets"), exist_ok=True)
    names = []
    for k in range(0, len(items_), PACKET_SIZE):
        name = f"{prefix}_{k // PACKET_SIZE:02d}"
        json.dump(items_[k:k + PACKET_SIZE], open(os.path.join(ADJ, "packets", f"{name}.json"), "w"), indent=1)
        names.append(name)
    return names


def cmd_repack(who: str) -> None:
    """Packets of the P_ items for which this seat has no collected record (a run that ended early or
    wrote a record under another id). Refuses if packets of this prefix already exist."""
    prefix = f"PR_{ROLE[who]}"
    if glob.glob(os.path.join(ADJ, "packets", f"{prefix}_*.json")):
        raise SystemExit(f"{prefix} packets exist already; collect them before repacking")
    have = load_records(who)
    todo = [it for it in initial_items() if it["item_id"] not in have]
    names = write_packets(prefix, todo)
    print(len(todo), "items without a record for", who, "->", ", ".join(names) or "no packet")


def cmd_third() -> None:
    """Packets for ADJ3: every port with at least one value the two initial seats judged differently (the
    same item object, all of its values). Needs a record from both seats for every item. Refuses to
    rewrite once ADJ3 has records, so packets are never reshuffled under a running seat."""
    if load_records(SEATS["ADJ3"]):
        raise SystemExit("ADJ3 has records already; PT packets are not rewritten")
    r1, r2 = load_records(SEATS["ADJ1"]), load_records(SEATS["ADJ2"])
    items_ = initial_items()
    incomplete = [it["item_id"] for it in items_ if it["item_id"] not in r1 or it["item_id"] not in r2]
    if incomplete:
        raise SystemExit(f"{len(incomplete)} items lack an initial record: {incomplete[:10]}")
    split = [it for it in items_ if any(verdict_of(r1[it["item_id"]], f) != verdict_of(r2[it["item_id"]], f) for f in it["values"])]
    for old in glob.glob(os.path.join(ADJ, "packets", "PT_*.json")):
        os.remove(old)
    names = write_packets("PT", split)
    n_val = sum(1 for it in split for f in it["values"] if verdict_of(r1[it["item_id"]], f) != verdict_of(r2[it["item_id"]], f))
    print(len(split), "ports with", n_val, "split values ->", ", ".join(names) or "no packet")


def provenance_kind(p) -> str:
    """What kind of thing a provenance string is: a location in the snapshot or artifact (the protocol's
    format, or a bare path:line spelling), a hashing command for a definition identity, a URL, a reference to
    the packet element, or a statement with no location at all."""
    import re
    if not p:
        return "missing"
    q = p.strip()
    head = q.split("|")[0]
    if q.startswith("snapshot:") or q.startswith("artifact:"):
        return "location"
    if "definition_hash.py" in head:
        return "hash_command"
    if re.match(r"^(curl\s+\S*\s*)?(dependency:)?https?://", head.strip()):
        return "url"
    if re.search(r"(artifact\.txt|\.(cpp|cc|c|h|hpp|py|msg|srv|action|xml|txt|yaml|yml|cmake|launch|json)):\d+", head):
        return "location_other_spelling"
    if head.startswith("packet.json") or head.startswith("packet element"):
        return "packet_reference"
    return "statement"


def provenance_formats(items: list) -> dict:
    """Counts of provenance kinds over the values of the given ports, overall and per field, plus how many
    location strings carry a redundant leading `snapshot/` directory (a path the snapshot does not have)."""
    import collections
    kinds = collections.Counter(); by_field = collections.defaultdict(collections.Counter); prefixed = 0
    for x in items:
        for f, p in x["provenance"].items():
            k = provenance_kind(p); kinds[k] += 1; by_field[f][k] += 1
            if p and p.startswith("snapshot:snapshot/"):
                prefixed += 1
    return {"values": sum(kinds.values()), "kinds": dict(kinds), "by_field": {f: dict(c) for f, c in by_field.items()},
            "location_with_redundant_snapshot_prefix": prefixed}


def kappa_of(pairs: list) -> dict:
    pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
    n = len(pairs)
    if not n:
        return {"n": 0, "observed_agreement": None, "kappa": None}
    cats = sorted({c for p in pairs for c in p})
    po = sum(x == y for x, y in pairs) / n
    pe = sum((sum(x == c for x, _ in pairs) / n) * (sum(y == c for _, y in pairs) / n) for c in cats)
    return {"n": n, "observed_agreement": po, "kappa": (po - pe) / (1 - pe) if pe < 1 else None}


def frame_class(value) -> str:
    return "none" if value == "none" else ("per_message" if value == "per_message" else "named")


def cmd_fold() -> None:
    """Final verdict per value: the initial seats' verdict where they agree, ADJ3's where they differ,
    'pending' while ADJ3 has not judged a split value, 'incomplete' where an initial record is missing.
    Agreement is Cohen's kappa on the initial records, over the three verdicts and over verified-vs-not."""
    import collections
    sample = json.load(open(SAMPLE))
    todo = [x for x in sample["items"] if x["values"]]
    r1, r2, r3 = (load_records(SEATS[k]) for k in ("ADJ1", "ADJ2", "ADJ3"))
    kind_of = {(f"P-{x['task_id']}-{x['port_index']}", f): provenance_kind(p) for x in todo for f, p in x["provenance"].items()}
    rows = []
    for x in todo:
        iid = f"P-{x['task_id']}-{x['port_index']}"
        for field, value in x["values"].items():
            v1, v2, v3 = verdict_of(r1.get(iid), field), verdict_of(r2.get(iid), field), verdict_of(r3.get(iid), field)
            if v1 is None or v2 is None:
                final, how = "incomplete", "incomplete"
            elif v1 == v2:
                final, how = v1, "agreed"
            elif v3 is not None:
                final, how = v3, "third"
            else:
                final, how = "pending", "pending"
            rows.append({"item_id": iid, "field": field, "value": value, "kind": kind_of[(iid, field)],
                         "ADJ1": v1, "ADJ2": v2, "ADJ3": v3, "final": final, "how": how})

    def tally(rs):
        c = collections.Counter(r["final"] for r in rs)
        return {"values": len(rs), **{k: c.get(k, 0) for k in VERDICTS + ("pending", "incomplete")},
                "initial_agreement": kappa_of([(r["ADJ1"], r["ADJ2"]) for r in rs])["observed_agreement"]}

    third = [r for r in rows if r["how"] in ("third", "pending")]
    out = {
        "seats": SEATS,
        "rule": "final = initial verdict where ADJ1 and ADJ2 agree, ADJ3 verdict where they differ (PROTOCOL.md Section 11)",
        "final": tally(rows),
        "initial_agreement": {
            "three_verdicts": kappa_of([(r["ADJ1"], r["ADJ2"]) for r in rows]),
            "verified_vs_not": kappa_of([(r["ADJ1"] == "verified" if r["ADJ1"] else None,
                                          r["ADJ2"] == "verified" if r["ADJ2"] else None) for r in rows]),
        },
        "third_seat": {"split_values": len(third), "judged": sum(1 for r in third if r["ADJ3"]),
                       "sided_with_ADJ1": sum(1 for r in third if r["ADJ3"] and r["ADJ3"] == r["ADJ1"]),
                       "sided_with_ADJ2": sum(1 for r in third if r["ADJ3"] and r["ADJ3"] == r["ADJ2"]),
                       "sided_with_neither": sum(1 for r in third if r["ADJ3"] and r["ADJ3"] not in (r["ADJ1"], r["ADJ2"]))},
        "per_seat": {role: dict(collections.Counter(r[role] for r in rows if r[role])) for role in ("ADJ1", "ADJ2", "ADJ3")},
        "by_field": {f: tally([r for r in rows if r["field"] == f]) for f in FIELDS if any(r["field"] == f for r in rows)},
        "frame_by_class": {c: tally([r for r in rows if r["field"] == "frame" and frame_class(r["value"]) == c])
                           for c in ("none", "per_message", "named")},
        "by_provenance_kind": {k: tally([r for r in rows if r["kind"] == k]) for k in sorted({r["kind"] for r in rows})},
        "final_wrong": [dict(r, excerpts={role: next((v.get("source_excerpt") for v in (rec.get(r["item_id"]) or {}).get("values", [])
                                                       if v.get("field") == r["field"]), None)
                                          for role, rec in (("ADJ1", r1), ("ADJ2", r2), ("ADJ3", r3)) if r[role] == "wrong"})
                        for r in rows if r["final"] == "wrong"],
        "rows": rows,
        "provenance_formats_sample": provenance_formats(todo),
        "provenance_formats_frame": provenance_formats(frame()),
    }
    json.dump(out, open(AGREEMENT, "w"), indent=1, allow_nan=False)
    print(json.dumps({k: v for k, v in out.items() if k not in ("rows", "final_wrong", "provenance_formats_frame", "by_provenance_kind")}, indent=1))
    print(len(out["final_wrong"]), "values finally judged wrong; wrote", AGREEMENT)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args == ["--write"]:
        cmd_draw("--write" in args)
    elif args[0] == "packets":
        cmd_packets()
    elif args[0] == "prompt":
        cmd_prompt(args[1], args[2])
    elif args[0] == "collect":
        cmd_collect(args[1], args[2])
    elif args[0] == "repack":
        cmd_repack(args[1])
    elif args[0] == "third":
        cmd_third()
    elif args[0] == "fold":
        cmd_fold()
    else:
        print(__doc__)
