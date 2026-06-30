"""Flatten the blind-reconstruction workflow output into a checker-ready contract
library, sanitizing messy free-text numeric fields (agents sometimes wrote prose
where a number was expected). Usage: python3 build_library.py <wf_output.json> <out.json>
"""
import json
import re
import sys


def num(v):
    """Coerce a value to float, or None if it is prose / unspecified."""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        m = re.search(r"-?\d+(\.\d+)?", v)
        if m:
            return float(m.group())
    return None


def clean_endpoint(ep):
    if not isinstance(ep, dict):
        return None
    out = dict(ep)
    if "rate_hz" in out:
        out["rate_hz"] = num(out["rate_hz"])
    if "min_rate_hz" in out:
        out["min_rate_hz"] = num(out["min_rate_hz"])
    q = out.get("qos")
    if isinstance(q, dict) and "deadline_ms" in q:
        q = dict(q)
        q["deadline_ms"] = num(q["deadline_ms"])
        out["qos"] = q
    return out


def clean_contract(c):
    c = dict(c)
    for key in ("outputs", "inputs"):
        if isinstance(c.get(key), list):
            c[key] = [clean_endpoint(e) for e in c[key] if isinstance(e, dict)]
    if not isinstance(c.get("exclusive"), list):
        c["exclusive"] = []
    return c


def main():
    src, out = sys.argv[1], sys.argv[2]
    data = json.load(open(src))
    libs = data.get("result", {}).get("libraries", [])
    lib = {}            # module_id -> contract
    by_system = {}      # system_short -> [module_id]
    for L in libs:
        sysname = (L.get("system", "?")).split("(")[0].split(",")[0].strip()[:40]
        for comp in L.get("components", []) or []:
            mid = comp.get("module_id")
            con = comp.get("contract")
            if not mid or not isinstance(con, dict):
                continue
            con = clean_contract(con)
            con["_system"] = sysname
            con["_provenance"] = comp.get("provenance", "")[:200]
            lib[mid] = con
            by_system.setdefault(sysname, []).append(mid)
    json.dump(lib, open(out, "w"), indent=2)
    print(f"systems: {len(libs)}  modules: {len(lib)}")
    for s, mods in by_system.items():
        print(f"  {s}: {len(mods)}  -> {', '.join(mods[:8])}")
    # quick contract-richness summary (which fields are actually grounded)
    import collections
    fields = collections.Counter()
    for c in lib.values():
        if c.get("outputs"): fields["has_outputs"] += 1
        if c.get("inputs"): fields["has_inputs"] += 1
        if c.get("exclusive"): fields["has_exclusive"] += 1
        if any(e and e.get("frame") for e in (c.get("outputs", []) + c.get("inputs", []))): fields["has_frame"] += 1
        if any(e and e.get("qos") for e in (c.get("outputs", []) + c.get("inputs", []))): fields["has_qos"] += 1
        if any(e and e.get("rate_hz") for e in c.get("outputs", [])): fields["has_rate"] += 1
        if c.get("changed_fields"): fields["has_changed_fields"] += 1
    print("contract richness:", dict(fields))


if __name__ == "__main__":
    main()
