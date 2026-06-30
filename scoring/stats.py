"""Statistical inference for Path B: Wilson 95% CIs on every recall proportion and
exact McNemar tests (ECM vs the strongest baseline) on each substrate. Emits
stats_table.tex and prints the per-method recall with confidence intervals.
Usage: python3 stats.py [output_dir]   (output_dir defaults to ../tables)
"""
import json
import math
import os
import sys
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))      # scoring/
REPO = os.path.dirname(HERE)                           # repo root
DATA = os.path.join(REPO, "data")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "tables")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(REPO, "checker"))
from contract_checker import (ECM_FULL, SCHEMA_ONLY, SCHEMA_QOS, SEMVER_ONLY,
                              ALL_METHODS, Severity, all_findings, method_findings)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(0, min(b, c) + 1)) * (0.5 ** n))


def adapt(c):
    c = dict(c)
    if c.get("type") == "UPGRADE":
        vd = c.get("ver_delta", {}) or {}
        c["old"] = {"interface_hash": vd.get("interface_hash_old", "o"), "semver": vd.get("semver_old", "1.0.0")}
        c["new"] = {"interface_hash": vd.get("interface_hash_new", "n"), "semver": vd.get("semver_new", "1.0.1"),
                    "changed_fields": vd.get("changed_fields", []) or []}
        c["consumer_reads"] = vd.get("consumer_reads", []) or []
    c.setdefault("edge", {})
    return c


def goldset(c):
    g = c.get("gold") or c.get("gold_dimension")
    return set(g) if isinstance(g, list) else {g}


def hit(case, method):
    f = [x for x in all_findings(case) if x.severity == Severity.CRITICAL]
    dims = {x.dimension for x in method_findings(f, method)}
    return bool(dims & goldset(case))


def load_robust():
    sc = json.load(open(os.path.join(DATA, "scoreable_cases.json")))
    return [adapt({**x["case"], "gold_dimension": x["gold"]}) for x in sc if x.get("gold")]


def load_corpus():
    return [adapt(c) for c in json.load(open(os.path.join(DATA, "cases.json"))) if c.get("gold_dimension") and not c.get("excluded")]


def analyze(name, cases):
    n = len(cases)
    print(f"\n=== {name} (N={n}) ===")
    rows = []
    for m in ALL_METHODS:
        k = sum(1 for c in cases if hit(c, m))
        lo, hi = wilson(k, n)
        print(f"  {m.name:12s} {k}/{n} = {k/n:.0%}  Wilson95 [{lo:.0%}, {hi:.0%}]")
        rows.append((m.name, k, n, lo, hi))
    # McNemar ECM vs strongest baseline (schema+QoS)
    b = sum(1 for c in cases if hit(c, ECM_FULL) and not hit(c, SCHEMA_QOS))
    cc = sum(1 for c in cases if not hit(c, ECM_FULL) and hit(c, SCHEMA_QOS))
    p = mcnemar_exact(b, cc)
    print(f"  McNemar ECM vs schema+QoS: discordant b={b} c={cc}  exact p={p:.2e}  ({'SIG' if p<0.05 else 'ns'})")
    return rows, (b, cc, p)


def main():
    rb = load_robust()
    cp = load_corpus()
    rrows, rmc = analyze("ROBUST (blind)", rb)
    crows, cmc = analyze("ROS2 corpus", cp)
    # LaTeX table fragment
    L = [r"\begin{table}[!ht]\centering",
         r"\caption{Recall with Wilson 95\% confidence intervals, and exact McNemar tests of ECM-full against the strongest baseline (schema+QoS) on each substrate.}",
         r"\label{tab:pathb_stats}\small",
         r"\begin{tabularx}{\linewidth}{@{}lXX@{}}",
         r"\toprule",
         r"\textbf{Method} & \textbf{ROBUST (N=%d)} & \textbf{ROS\,2 (N=%d)} \\" % (len(rb), len(cp)),
         r"\midrule"]
    for (nm, k1, n1, lo1, hi1), (_, k2, n2, lo2, hi2) in zip(rrows, crows):
        L.append(f"{nm} & {k1}/{n1}={k1/n1:.0%} [{lo1:.0%},{hi1:.0%}] & {k2}/{n2}={k2/n2:.0%} [{lo2:.0%},{hi2:.0%}] \\\\")
    L.append(r"\midrule")
    L.append(r"McNemar (ECM vs schema+QoS) & $b{=}%d, c{=}%d$, $p{=}%.3g$ & $b{=}%d, c{=}%d$, $p{=}%.3g$ \\" %
             (rmc[0], rmc[1], rmc[2], cmc[0], cmc[1], cmc[2]))
    L += [r"\bottomrule", r"\end{tabularx}", r"\end{table}"]
    open(os.path.join(OUT, "stats_table.tex"), "w").write("\n".join(L))
    print("\nwrote stats_table.tex")


if __name__ == "__main__":
    main()
