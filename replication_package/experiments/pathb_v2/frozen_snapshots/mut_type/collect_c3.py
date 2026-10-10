"""Deterministic C3 retrieval (PROTOCOL.md Section 3). Steward script, not an agent.

  python3 collect_c3.py search      -> candidates/C3_ledger.json (every hit, all pages)
  python3 collect_c3.py neutral     -> candidates/C3N_ledger.json (30 fix-linked issues, no terms)
  python3 collect_c3.py order       -> candidates/C3_order.json (dedup, exclusions, seeded order)

Uses `gh api` only. Records queries, page counts, timestamps and exclusion reasons.
The ledger hashes go into FREEZE.json when retrieval runs.
"""
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
PB = os.path.join(os.path.dirname(HERE), "pathb")
OUT = os.path.join(HERE, "candidates")

REPOS = ["ros2/rclcpp", "ros2/rclpy", "ros2/rmw_fastrtps", "ros2/rmw_cyclonedds", "ros2/geometry2",
         "ros-navigation/navigation2", "ros-controls/ros2_control", "ros-controls/ros2_controllers",
         "moveit/moveit2", "ros-perception/image_common", "ros-perception/image_transport_plugins",
         "ros-perception/vision_opencv", "cra-ros-pkg/robot_localization", "mavlink/mavros",
         "RobotWebTools/rosbridge_suite", "ros-drivers/usb_cam", "ros2/ros2"]
TERMS = ["incompatible", "QoS", "frame_id", "frame", "units", "already claimed", "claimed", "renamed",
         "removed", "deprecated", "breaking", "md5", "type hash", "version mismatch", "does not match"]
WINDOW = ("2022-01-01", "2026-06-30")
PER_REPO_CAP = 6
NEUTRAL_N = 30


def gh(args, retries=3):
    """`gh api`; retries with backoff (5, 15, 45 s) on a transient failure. Raises on a final failure."""
    backoff = [5, 15, 45]
    for attempt in range(retries + 1):
        r = subprocess.run(["gh", "api"] + args, capture_output=True, text=True)
        if r.returncode == 0:
            return json.loads(r.stdout)
        err = r.stderr.strip()[:300]
        if "404" in err or attempt == retries:
            raise RuntimeError(err)
        time.sleep(backoff[min(attempt, len(backoff) - 1)])
    raise RuntimeError(err)


def search_issues(repo, term=None):
    """All pages of a GitHub issue search; returns hits and the page count."""
    q = f'repo:{repo} is:issue is:closed closed:{WINDOW[0]}..{WINDOW[1]}'
    if term:
        q += f' "{term}"'
    hits, page = [], 1
    while True:
        res = gh(["-X", "GET", "search/issues", "-f", f"q={q}", "-f", "per_page=100", "-f", f"page={page}"])
        items = res.get("items", [])
        hits.extend(items)
        if len(items) < 100 or page >= 10:  # GitHub search returns at most 1000 results
            break
        page += 1
        time.sleep(2)
    return hits, page


def fix_links(repo, number):
    """Merged PRs or commits that reference the issue, from its timeline.
    Returns (links, error): error is the gh message when the timeline could not be read
    (the hit is then recorded as `timeline_unavailable`, never silently dropped or invented)."""
    links = []
    try:
        # -X GET is required: with -f fields and no method, gh api issues a POST, which the
        # timeline endpoint answers with 404 (the cause of the first two retrieval failures).
        events = gh(["-X", "GET", f"repos/{repo}/issues/{number}/timeline", "-f", "per_page=100", "--paginate"]) or []
    except RuntimeError as exc:
        return None, str(exc)
    for ev in events:
        if ev.get("event") == "cross-referenced":
            src = (ev.get("source") or {}).get("issue") or {}
            pr = src.get("pull_request") or {}
            if pr.get("merged_at"):
                links.append(src.get("html_url"))
        elif ev.get("event") in ("referenced", "closed") and ev.get("commit_url"):
            links.append(ev["commit_url"].replace("api.github.com/repos", "github.com").replace("/commits/", "/commit/"))
    return sorted(set(l for l in links if l)), None


def search():
    """Resumable: progress is saved to C3_ledger.partial.json after every query, and a restart
    skips the queries already recorded. A query that fails after all retries is recorded in
    `failed_queries` and the run continues; `order` refuses a ledger with failed queries."""
    os.makedirs(OUT, exist_ok=True)
    partial = os.path.join(OUT, "C3_ledger.partial.json")
    if os.path.exists(partial):
        ledger = json.load(open(partial))
        ledger.setdefault("resumed_at", []).append(datetime.now(timezone.utc).isoformat())
    else:
        ledger = {"retrieved_at": datetime.now(timezone.utc).isoformat(), "window": WINDOW, "terms": TERMS,
                  "repos": REPOS, "queries": [], "failed_queries": [], "hits": {}}
    done = {(q["repo"], q["term"]) for q in ledger["queries"]}
    for repo in REPOS:
        for term in TERMS:
            if (repo, term) in done:
                continue
            try:
                hits, pages = search_issues(repo, term)
            except RuntimeError as exc:
                ledger["failed_queries"].append({"repo": repo, "term": term, "error": str(exc)[:200],
                                                 "at": datetime.now(timezone.utc).isoformat()})
                json.dump(ledger, open(partial, "w"), indent=1)
                continue
            ledger["queries"].append({"repo": repo, "term": term, "pages": pages, "n": len(hits)})
            ledger["failed_queries"] = [q for q in ledger.get("failed_queries", []) if (q["repo"], q["term"]) != (repo, term)]
            for h in hits:
                key = h["html_url"]
                e = ledger["hits"].setdefault(key, {"repo": repo, "number": h["number"], "title": h["title"],
                                                     "closed_at": h["closed_at"], "state_reason": h.get("state_reason"),
                                                     "matched_terms": []})
                if term not in e["matched_terms"]:
                    e["matched_terms"].append(term)
            json.dump(ledger, open(partial, "w"), indent=1)
            time.sleep(2)
    path = os.path.join(OUT, "C3_ledger.json")
    if os.path.exists(path):  # a previous enrichment pass: keep its fix_links
        prev = json.load(open(path)).get("hits", {})
        for k, e in ledger["hits"].items():
            if k in prev and "fix_links" in prev[k]:
                e["fix_links"], e["timeline_error"] = prev[k]["fix_links"], prev[k].get("timeline_error")
                if e["timeline_error"] is None:
                    del e["timeline_error"]
    json.dump(ledger, open(path, "w"), indent=1)  # searches saved before enrichment
    for e in ledger["hits"].values():
        if e.get("fix_links") is not None and e.get("timeline_error"):
            del e["timeline_error"]  # normalise records enriched successfully after an earlier error
    for i, (key, e) in enumerate(ledger["hits"].items()):
        if e.get("fix_links") is not None:
            continue  # enriched in an earlier run (an errored hit is retried)
        e["fix_links"], err = fix_links(e["repo"], e["number"])
        if err:
            e["timeline_error"] = err
        else:
            e.pop("timeline_error", None)  # a retried hit that now succeeded carries no stale error
        if i % 25 == 0:
            json.dump(ledger, open(path, "w"), indent=1)
    ledger["enriched_at"] = datetime.now(timezone.utc).isoformat()
    ledger["complete"] = not ledger.get("failed_queries")
    json.dump(ledger, open(path, "w"), indent=1)
    if ledger["failed_queries"]:
        print("WARNING:", len(ledger["failed_queries"]), "queries failed after retries; re-run `search` to retry them before `order`")
    print(len(ledger["hits"]), "hits;", sum(1 for e in ledger["hits"].values() if e["fix_links"]), "fix-linked;",
          sum(1 for e in ledger["hits"].values() if e.get("timeline_error")), "timeline unavailable")


def neutral(seed):
    os.makedirs(OUT, exist_ok=True)
    rng = random.Random(f"{seed}:neutral")
    pool = []
    for repo in REPOS:
        hits, _ = search_issues(repo)
        pool.extend(hits)
        time.sleep(2)
    rng.shuffle(pool)
    chosen, ledger = [], {"retrieved_at": datetime.now(timezone.utc).isoformat(), "seed": seed, "pool": len(pool), "hits": {}}
    for h in pool:
        links, err = fix_links(h["repository_url"].split("/repos/")[1], h["number"])
        if err:
            continue  # timeline unreadable: not shown to be fix-linked, so not drawn
        if links:
            ledger["hits"][h["html_url"]] = {"repo": h["repository_url"].split("/repos/")[1], "number": h["number"],
                                             "title": h["title"], "closed_at": h["closed_at"], "fix_links": links}
            chosen.append(h["html_url"])
        if len(chosen) >= NEUTRAL_N:
            break
    json.dump(ledger, open(os.path.join(OUT, "C3N_ledger.json"), "w"), indent=1)
    print(len(chosen), "neutral candidates")


def prior_refs():
    """URLs, issue numbers and fix SHAs already used by C1 or C2."""
    refs = set()
    for c in json.load(open(os.path.join(PB, "robust_cases.json"))):
        if c.get("issue_url"):
            refs.add(c["issue_url"].rstrip("/"))
        for f in c.get("fix_commits") or []:
            if isinstance(f, dict) and f.get("hash"):
                refs.add(f["hash"][:7])
    for c in json.load(open(os.path.join(PB, "cases.json"))):
        refs.add(c["source_url"].rstrip("/"))
    return refs


def order(seed):
    ledger = json.load(open(os.path.join(OUT, "C3_ledger.json")))
    if ledger.get("failed_queries"):
        raise SystemExit(f"{len(ledger['failed_queries'])} queries failed; re-run `search` until the ledger is complete")
    refs = prior_refs()
    rng = random.Random(f"{seed}:order")
    by_repo, excluded = {}, []
    seen_fix = {}
    for url, e in sorted(ledger["hits"].items()):
        reason = None
        if not e["fix_links"]:
            reason = "no_merged_fix_link"
        elif e.get("state_reason") == "reopened":
            reason = "reopened"
        elif url.rstrip("/") in refs or any(l.split("/")[-1][:7] in refs for l in e["fix_links"]):
            reason = "in_C1_or_C2"
        else:
            for l in e["fix_links"]:
                if l in seen_fix:
                    reason = f"duplicate_fix_of:{seen_fix[l]}"
                    break
        if reason:
            excluded.append({"url": url, "reason": reason})
            continue
        for l in e["fix_links"]:
            seen_fix.setdefault(l, url)
        by_repo.setdefault(e["repo"], []).append(url)
    for urls in by_repo.values():
        rng.shuffle(urls)
    ordered, i = [], 0
    while any(by_repo.values()):
        for repo in REPOS:
            if by_repo.get(repo):
                ordered.append(by_repo[repo].pop())
        i += 1
    out = {"seed": seed, "per_repo_cap": PER_REPO_CAP, "ordered": ordered, "excluded": excluded,
           "ledger_sha256": hashlib.sha256(open(os.path.join(OUT, "C3_ledger.json"), "rb").read()).hexdigest()}
    json.dump(out, open(os.path.join(OUT, "C3_order.json"), "w"), indent=1)
    print(len(ordered), "ordered;", len(excluded), "excluded")


if __name__ == "__main__":
    cmd = sys.argv[1]
    seed = json.load(open(os.path.join(HERE, "FREEZE.json")))["seed"] if os.path.exists(os.path.join(HERE, "FREEZE.json")) else 20260925
    {"search": search, "neutral": lambda: neutral(seed), "order": lambda: order(seed)}[cmd]()
