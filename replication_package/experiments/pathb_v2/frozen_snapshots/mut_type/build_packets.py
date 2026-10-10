"""Build S1 packets for Path B v2.1 (steward script; PROTOCOL.md Sections 3 and 5).

  python3 build_packets.py C1 [--chunk 8]    from ../pathb/robust_cases.json (all 92)
  python3 build_packets.py C2 [--chunk 8]    from ../pathb/cases.json (32; V18 flags ignored)
  python3 build_packets.py C3 [--chunk 8]    from candidates/C3_order.json + C3_ledger.json
  python3 build_packets.py C3N [--chunk 8]   from candidates/C3N_ledger.json

Packets carry only source pointers. Fix references that are not a list (a string such as
"confidential", or null) are carried as `fix_status` metadata, never dropped or invented.
S2 packets are built by materialize.py. The six quarantined pilot cases (pilot/PILOT_CASES.json) are
left out of C1/C2 and reported as pilot.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PB = os.path.join(os.path.dirname(HERE), "pathb")


def fix_refs(raw):
    if isinstance(raw, list):
        return [{"repo": f.get("repo"), "hash": f.get("hash")} for f in raw if isinstance(f, dict)], "listed"
    if isinstance(raw, str):
        return [], raw.strip().lower() or "unspecified"
    return [], "absent"


def items(corpus):
    if corpus == "C1":
        out = []
        for c in json.load(open(os.path.join(PB, "robust_cases.json"))):
            refs, status = fix_refs(c.get("fix_commits"))
            out.append({"case_id": c["case_id"], "corpus": "C1", "bug_title": c.get("title"),
                        "bug_description": c.get("description"), "issue_url": c.get("issue_url"),
                        "fix_commits": refs, "fix_status": status})
        return out
    if corpus == "C2":
        seen, out = {}, []
        for c in json.load(open(os.path.join(PB, "cases.json"))):
            url = c["source_url"].rstrip("/")
            is_tracker = "github.com/" in url and ("/issues/" in url or "/pull/" in url)
            if is_tracker and url in seen:  # one candidate per tracker issue (ros2_control#1400 appears twice in V18)
                continue
            seen[url] = c["case_id"]
            out.append({"case_id": c["case_id"], "corpus": "C2", "source_url": c["source_url"]})
        return out
    if corpus in ("C3", "C3N"):
        ledger = json.load(open(os.path.join(HERE, "candidates", f"{corpus}_ledger.json")))
        urls = (json.load(open(os.path.join(HERE, "candidates", "C3_order.json")))["ordered"]
                if corpus == "C3" else list(ledger["hits"].keys()))
        out = []
        for i, url in enumerate(urls):
            h = ledger["hits"][url]
            out.append({"case_id": f"{corpus}-{i + 1:03d}", "corpus": corpus, "bug_title": h.get("title"),
                        "issue_url": url, "fix_refs": h.get("fix_links", [])})
        return out
    raise SystemExit(f"unknown corpus {corpus}")


def main():
    corpus = sys.argv[1]
    n = int(sys.argv[sys.argv.index("--chunk") + 1]) if "--chunk" in sys.argv else 8
    os.makedirs(os.path.join(HERE, "packets"), exist_ok=True)
    it = items(corpus)
    quarantine = set(json.load(open(os.path.join(HERE, "pilot", "PILOT_CASES.json")))["quarantined_pilot_cases"])
    dropped = [c["case_id"] for c in it if c["case_id"] in quarantine]
    it = [c for c in it if c["case_id"] not in quarantine]
    if dropped:
        print(corpus, "quarantined pilot cases left out:", ", ".join(dropped))
    for k in range(0, len(it), n):
        json.dump(it[k:k + n], open(os.path.join(HERE, "packets", f"S1_{corpus}_{k // n:02d}.json"), "w"), indent=1)
    print(corpus, len(it), "cases in", (len(it) + n - 1) // n, "packets")


if __name__ == "__main__":
    main()
