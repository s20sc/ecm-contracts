"""Single scoring pass that regenerates every reported number. One attribution
convention produces recall_table / perdim_table / stats_table so the recall table,
the per-dimension table, and the stats table all reconcile exactly.
Usage: python3 canonical_scores.py [output_dir]   (output_dir defaults to ../tables)

Attribution convention: for a case whose gold set is G, a method
PREDICTS+ATTRIBUTES the case iff it emits a CRITICAL finding whose dimension is in
G. Per-dimension recall for dimension D = (# cases with D in G where ECM emits a
critical finding of dimension D) / (# cases with D in G). Denominators are
multi-label (a case stressing two dimensions counts under each).
"""
import json
import math
import os
import sys
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))      # scoring/
REPO = os.path.dirname(HERE)                           # repo root
DATA = os.path.join(REPO, "data")
PS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "tables")
os.makedirs(PS, exist_ok=True)
sys.path.insert(0, os.path.join(REPO, "checker"))
from contract_checker import (ECM_FULL, SCHEMA_ONLY, SCHEMA_QOS, SEMVER_ONLY,
                              ALL_METHODS, Severity, all_findings, method_findings)
DIMS = ["Sig", "Beh", "Res", "Perm", "Rec", "Ver"]


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n; d = 1 + z*z/n
    c = (p + z*z/(2*n))/d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return (max(0.0, c-h), min(1.0, c+h))


def mcnemar(b, c):
    n = b+c
    return 1.0 if n == 0 else min(1.0, 2*sum(comb(n, i) for i in range(min(b, c)+1))*0.5**n)


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


def gold(c):
    g = c.get("gold") or c.get("gold_dimension")
    return set(g) if isinstance(g, list) else {g}


def fired(case, method):
    """Critical dimensions method emits that are in the gold set."""
    f = [x for x in all_findings(case) if x.severity == Severity.CRITICAL]
    return {x.dimension for x in method_findings(f, method)} & gold(case)


def load():
    sc = json.load(open(os.path.join(DATA, "scoreable_cases.json")))
    rb = [adapt({**x["case"], "gold_dimension": x["gold"]}) for x in sc if x.get("gold")]
    cp = [adapt(c) for c in json.load(open(os.path.join(DATA, "cases.json"))) if c.get("gold_dimension") and not c.get("excluded")]
    return rb, cp


def per_method(cases):
    out = {}
    for m in ALL_METHODS:
        out[m.name] = sum(1 for c in cases if fired(c, m))
    return out, len(cases)


def per_dim(cases):
    rec = {}
    for D in DIMS:
        den = [c for c in cases if D in gold(c)]
        num = sum(1 for c in den if D in fired(c, ECM_FULL))
        if den:
            rec[D] = (num, len(den))
    return rec


def main():
    rb, cp = load()
    out = {}
    for name, cs in [("robust", rb), ("ros2", cp)]:
        pm, n = per_method(cs)
        b = sum(1 for c in cs if fired(c, ECM_FULL) and not fired(c, SCHEMA_QOS))
        cc = sum(1 for c in cs if not fired(c, ECM_FULL) and fired(c, SCHEMA_QOS))
        out[name] = {"n": n, "per_method": pm, "per_dim": per_dim(cs),
                     "mcnemar": {"b": b, "c": cc, "p": mcnemar(b, cc)}}
    print(json.dumps(out, indent=2))

    pct = lambda k, n: f"{round(100*k/n)}\\%"
    # recall table
    R = [r"\begin{table}[!ht]\centering",
         r"\caption{Recall on both substrates (a method predicts a bug when it emits a critical finding whose dimension is in the bug's gold set).}",
         r"\label{tab:pathb_recall}\small",
         r"\begin{tabularx}{\linewidth}{@{}lXX@{}}\toprule",
         r"\textbf{Method} & \textbf{ROBUST ($N{=}%d$)} & \textbf{ROS\,2 ($N{=}%d$)} \\\midrule" % (out["robust"]["n"], out["ros2"]["n"])]
    nm = {"ECM-full": "ECM-full (6-dim)", "schema-only": "schema-only", "schema+QoS": "schema+QoS", "semver-only": "semver-only"}
    for m in ALL_METHODS:
        k1, k2 = out["robust"]["per_method"][m.name], out["ros2"]["per_method"][m.name]
        n1, n2 = out["robust"]["n"], out["ros2"]["n"]
        R.append(f"{nm[m.name]} & {k1}/{n1} ({pct(k1,n1)}) & {k2}/{n2} ({pct(k2,n2)}) \\\\")
    R += [r"\bottomrule\end{tabularx}\end{table}"]
    open(os.path.join(PS, "recall_table.tex"), "w").write("\n".join(R))

    # per-dim table
    P = [r"\begin{table}[!ht]\centering",
         r"\caption{Per-dimension recall of ECM-full (multi-label denominators: a bug stressing two dimensions counts under each).}",
         r"\label{tab:pathb_perdim}\small",
         r"\begin{tabularx}{\linewidth}{@{}lXX@{}}\toprule",
         r"\textbf{Dimension} & \textbf{ROBUST} & \textbf{ROS\,2} \\\midrule"]
    full = {"Sig": "Signature", "Beh": "Behavioral", "Res": "Resource", "Perm": "Permission", "Rec": "Recovery", "Ver": "Version"}
    for D in DIMS:
        r1 = out["robust"]["per_dim"].get(D); r2 = out["ros2"]["per_dim"].get(D)
        c1 = f"{r1[0]}/{r1[1]}" if r1 else "---"
        c2 = f"{r2[0]}/{r2[1]}" if r2 else "---"
        P.append(f"{full[D]} (\\textit{{{D}}}) & {c1} & {c2} \\\\")
    P += [r"\bottomrule\end{tabularx}\end{table}"]
    open(os.path.join(PS, "perdim_table.tex"), "w").write("\n".join(P))

    # stats table
    S = [r"\begin{table}[!ht]\centering",
         r"\caption{Recall with Wilson 95\% confidence intervals and exact McNemar tests of ECM-full against the strongest baseline (schema+QoS).}",
         r"\label{tab:pathb_stats}\small",
         r"\begin{tabularx}{\linewidth}{@{}lXX@{}}\toprule",
         r"\textbf{Method} & \textbf{ROBUST ($N{=}%d$)} & \textbf{ROS\,2 ($N{=}%d$)} \\\midrule" % (out["robust"]["n"], out["ros2"]["n"])]
    for m in ALL_METHODS:
        k1, n1 = out["robust"]["per_method"][m.name], out["robust"]["n"]
        k2, n2 = out["ros2"]["per_method"][m.name], out["ros2"]["n"]
        l1, h1 = wilson(k1, n1); l2, h2 = wilson(k2, n2)
        S.append(f"{m.name} & {k1}/{n1} [{round(100*l1)},{round(100*h1)}]\\% & {k2}/{n2} [{round(100*l2)},{round(100*h2)}]\\% \\\\")
    rm, cm = out["robust"]["mcnemar"], out["ros2"]["mcnemar"]
    S.append(r"\midrule McNemar vs schema+QoS & $b{=}%d,c{=}%d,\ p{=}%.2g$ & $b{=}%d,c{=}%d,\ p{=}%.2g$ \\" %
             (rm["b"], rm["c"], rm["p"], cm["b"], cm["c"], cm["p"]))
    S += [r"\bottomrule\end{tabularx}\end{table}"]
    open(os.path.join(PS, "stats_table.tex"), "w").write("\n".join(S))
    json.dump(out, open(os.path.join(DATA, "canonical_numbers.json"), "w"), indent=2)
    print("\nregenerated recall_table.tex, perdim_table.tex, stats_table.tex (all consistent)")


if __name__ == "__main__":
    main()
