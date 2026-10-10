"""Read-only steward check of S1 output format for one packet (not a frozen file; changes nothing).
  python3 check_specs.py S1_C1_01
"""
import glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    pk = json.load(open(os.path.join(HERE, "packets", f"{sys.argv[1]}.json")))
    probs = []
    for c in pk:
        cid = c["case_id"]
        f = os.path.join(HERE, "specs", f"{cid}.json")
        if not os.path.exists(f):
            probs.append((cid, "missing")); continue
        try:
            s = json.load(open(f))
        except Exception as e:
            probs.append((cid, f"invalid JSON: {e}")); continue
        if not s.get("eligible"):
            e2 = (s.get("eligibility") or {}).get("E2") or {}
            print(f"  {cid}: ineligible ({e2.get('reason_code') or s.get('ineligible_reason')})"); continue
        units = {u["name"] for u in s.get("units", [])}
        for u in s.get("units", []):
            for k in ("broken_rev", "resolved_rev"):
                v = u.get(k)
                if v and (" " in v or len(v) > 80):
                    probs.append((cid, f"{u['name']} {k} not bare: {v[:50]}"))
            if u.get("excerpt") is None:
                probs.append((cid, f"{u['name']} excerpt flag missing"))
            if u.get("excerpt") and not os.path.exists(os.path.join(HERE, "artifacts", f"{cid}.txt")):
                probs.append((cid, "excerpt unit but no artifact"))
        inv = {i["element"] for i in s.get("inventory", [])}
        for i in s.get("inventory", []):
            if set((i.get("sides") or {}).keys()) - units:
                probs.append((cid, f"inventory side names unknown unit: {i['element']}"))
        for cond in s.get("failed_conditions", []):
            if not set(cond.get("implicated_elements", [])) <= inv:
                probs.append((cid, f"implicated element not in inventory: {cond.get('implicated_elements')}"))
        if s.get("operation") == "UPGRADE" and not (s.get("consumer_built_against") or {}).get("broken"):
            probs.append((cid, "UPGRADE without consumer_built_against.broken"))
        cba = s.get("consumer_built_against") or {}
        print(f"  {cid}: {s.get('operation')} {s.get('outcome_class')} {s.get('loudness')} classes={[x['class'] for x in s.get('failed_conditions', [])]} "
              f"res={(s.get('resolution') or {}).get('status')} cba={cba.get('basis')} excerpt={[u['name'] for u in s['units'] if u.get('excerpt')]}")
    print("problems:", probs or "none")
    sys.exit(1 if probs else 0)


if __name__ == "__main__":
    main()
