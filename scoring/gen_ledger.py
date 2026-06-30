"""Generate the per-case provenance ledger (both substrates) from the scored
corpus data, with the ECM verdict recomputed by the frozen checker. Emits a LaTeX
longtable listing every scored bug, its public source, and the dimension(s) the
checker fired. Usage: python3 gen_ledger.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PB = os.path.join(HERE, "..", "data")
sys.path.insert(0, os.path.join(HERE, "..", "checker"))
from contract_checker import ECM_FULL, Severity, all_findings, method_findings


def gold_of(c):
    g = c.get("gold") or c.get("gold_dimension")
    return g if isinstance(g, list) else [g]


def ecm_fired(case):
    f = [x for x in all_findings(case) if x.severity == Severity.CRITICAL]
    dims = {x.dimension for x in method_findings(f, ECM_FULL)}
    return sorted(dims & set(gold_of(case)))


def short(u, n=70):
    if not u or str(u).strip().upper() in ("N/A", "NONE", ""):
        return "ROBUST corpus (Timperley et al. 2024)"
    return re.sub(r"^https?://(www\.)?", "", str(u))


def esc(s):
    return str(s).replace("_", r"\_").replace("&", r"\&").replace("#", r"\#").replace("%", r"\%")


def rows_robust():
    sc = json.load(open(os.path.join(PB, "scoreable_cases.json")))
    rc = {c["case_id"]: c for c in json.load(open(os.path.join(PB, "robust_cases.json")))}
    out = []
    for x in sc:
        cid = x["case_id"]
        if not x.get("gold"):
            continue
        meta = rc.get(cid, {})
        src = meta.get("issue_url") or "ROBUST corpus (Timperley et al. 2024)"
        fd = ecm_fired({**x["case"], "gold_dimension": x["gold"]}); hit = "/".join(fd) if fd else "--"
        out.append((cid.replace("robust_", "R-"), "/".join(x["gold"]), short(src), hit))
    return out


def rows_corpus():
    cs = json.load(open(os.path.join(PB, "cases.json")))
    out = []
    for c in cs:
        if not c.get("gold_dimension") or c.get("excluded"):
            continue
        fd = ecm_fired(_adapt(c)); hit = "/".join(fd) if fd else "--"
        g = c["gold_dimension"]
        out.append((c["case_id"], "/".join(g) if isinstance(g, list) else g,
                    short(c.get("source_url")), hit))
    return out


def _adapt(c):
    c = dict(c)
    if c.get("type") == "UPGRADE":
        vd = c.get("ver_delta", {}) or {}
        c["old"] = {"interface_hash": vd.get("interface_hash_old", "o"), "semver": vd.get("semver_old", "1.0.0")}
        c["new"] = {"interface_hash": vd.get("interface_hash_new", "n"), "semver": vd.get("semver_new", "1.0.1"),
                    "changed_fields": vd.get("changed_fields", []) or []}
        c["consumer_reads"] = vd.get("consumer_reads", []) or []
    c.setdefault("edge", {})
    return c


def fmt_src(s):
    e = esc(s)
    if "/" in s and " " not in s:
        return "{\\scriptsize\\ttfamily " + e.replace("/", "/\\allowbreak{}") + "}"
    return "{\\scriptsize " + e + "}"


def table(title, label, rows):
    L = [r"\begin{longtable}{@{}ll>{\raggedright\arraybackslash}p{0.44\linewidth}>{\raggedright\arraybackslash}p{0.11\linewidth}@{}}",
         r"\caption{" + title + r"}\label{" + label + r"}\\",
         r"\toprule",
         r"\textbf{Case} & \textbf{Gold dim.} & \textbf{Documented source} & \textbf{ECM fired} \\",
         r"\midrule\endfirsthead",
         r"\toprule \textbf{Case} & \textbf{Gold dim.} & \textbf{Documented source} & \textbf{ECM fired} \\ \midrule\endhead",
         r"\bottomrule\endfoot"]
    for cid, gold, src, hit in rows:
        L.append(f"{esc(cid)} & {esc(gold)} & {fmt_src(src)} & {hit} \\\\")
    L.append(r"\end{longtable}")
    return "\n".join(L)


def main():
    rb, cp = rows_robust(), rows_corpus()
    body = [
        r"\section{Per-Case Provenance Ledger}\label{app:ledger}",
        r"This appendix lists every scored bug on both substrates with its public source and the dimension(s) the checker fired (a gold dimension name = predicted and attributed to that dimension; -- = missed). Per-dimension recall in Section~\ref{sec:evaluation} is reconstructible from this column: dimension $D$'s recall is the number of $D$-gold rows whose ECM column contains $D$, over all $D$-gold rows. Gold dimensions are assigned from each corpus's native fault taxonomy through the frozen crosswalk, independently of the checker. A case is credited to a dimension only when the checker emits a finding of that dimension; the ECM column marks Y when the checker predicts the bug and attributes it to a gold dimension. Cases without a separate issue URL are documented within the ROBUST corpus record itself. Per-dimension denominators in Section~\ref{sec:evaluation} are multi-label: a bug that stresses two dimensions (for example a message-definition change that is both a signature and a version fault) is counted under each, so per-dimension counts sum to more than the de-duplicated scored-set size of 32.",
        "",
        f"\\noindent ROBUST substrate (blind reconstruction): {len(rb)} scored cases; ECM predicts {sum(1 for r in rb if r[3]!='--')}.",
        table("ROBUST substrate: scored integration bugs, sources, and ECM verdicts.", "tab:ledger_robust", rb),
        "",
        f"\\noindent ROS\\,2 corpus: {len(cp)} scored cases; ECM predicts {sum(1 for r in cp if r[3]!='--')}.",
        table("ROS\\,2 corpus: scored integration bugs, sources, and ECM verdicts.", "tab:ledger_corpus", cp),
    ]
    open(os.path.join(os.path.dirname(HERE), "tables", "app_ledger.tex"), "w").write("\n".join(body))
    print(f"ledger: ROBUST {len(rb)} rows ({sum(1 for r in rb if r[3]!='--')} hit), "
          f"ROS2 {len(cp)} rows ({sum(1 for r in cp if r[3]!='--')} hit)")


if __name__ == "__main__":
    main()
