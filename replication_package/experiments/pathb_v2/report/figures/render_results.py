"""Results figure of Section 4 (Path B v2.1), rendered as a standalone PDF.

  python3 report/figures/render_results.py            # writes V19-EMSE/paper_source/figures/fig_v2_results.pdf

Panel (a): right-reason detection per corpus and method with Wilson 95 % intervals, read from
report/numbers.json (written by make_report.py from the sealed results). Panel (b): the 40 pre-registered
held-out failures by whether their failed-condition class has a matching rule, whether they assembled, and
which method detected them, recomputed from scores_adjudicated/ and asserted against numbers.json. Straight
edges only, no rotated text (paper rule 7.11k).
"""
from __future__ import annotations

import glob
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PATHB = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.abspath(os.path.join(PATHB, "..", "..", "V19-EMSE", "paper_source", "figures", "fig_v2_results.pdf"))

METHODS = ["ECM", "NT", "DI", "DQ", "SV"]
COLORS = {"ECM": "#1F77B4", "NT": "#7F7F7F", "DI": "#2CA02C", "DQ": "#FF7F0E", "SV": "#D62728"}
CORPORA = [("C1", "C1\nROBUST"), ("C2", "C2\nROS reports"), ("C3", "C3\nheld-out"), ("C3N", "C3-neutral")]
MATCHABLE = {"nominal_type_mismatch", "definition_mismatch", "frame_mismatch", "unit_mismatch", "qos_reliability",
             "qos_durability", "qos_deadline", "rate_shortfall", "exclusive_resource_conflict", "permission_missing",
             "element_removed_or_renamed", "element_retyped"}

plt.rcParams.update({"font.family": "serif", "mathtext.fontset": "cm", "font.size": 7.5, "axes.titlesize": 8,
                     "axes.labelsize": 7.5, "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
                     "axes.linewidth": 0.6, "pdf.fonttype": 42})


def load_numbers() -> dict:
    with open(os.path.join(PATHB, "report", "numbers.json")) as f:
        return json.load(f)


def panel_a(ax, n: dict) -> None:
    width = 0.15
    for ci, (c, _) in enumerate(CORPORA):
        for mi, m in enumerate(METHODS):
            r = n[f"{c}.{m}"]["right_reason"]
            k, nn = r["k"], r["n"]
            lo, hi = r["wilson95"]
            x = ci + (mi - 2) * width
            rate = 100 * k / nn
            ax.bar(x, rate, width=width, color=COLORS[m], edgecolor="black", linewidth=0.4, zorder=2)
            ax.plot([x, x], [100 * lo, 100 * hi], color="black", linewidth=0.6, zorder=3)
            ax.plot([x - 0.035, x + 0.035], [100 * hi, 100 * hi], color="black", linewidth=0.6, zorder=3)
            ax.plot([x - 0.035, x + 0.035], [100 * lo, 100 * lo], color="black", linewidth=0.6, zorder=3)
            if k:  # the count sits directly above its own whisker; the denominator is under the corpus name
                ax.text(x, 100 * hi + 1.2, str(k), ha="center", va="bottom", fontsize=7, zorder=4)
    ax.set_xticks(range(len(CORPORA)))
    ax.set_xticklabels([f"{lab}\n$n = {n[f'{c}.ECM']['right_reason']['n']}$" for c, lab in CORPORA])
    ax.set_ylim(0, 82)
    ax.set_yticks([0, 20, 40, 60, 80])
    ax.yaxis.grid(True, linewidth=0.3, color="#cccccc", zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(handles=[Patch(facecolor=COLORS[m], edgecolor="black", linewidth=0.4, label=m) for m in METHODS],
              ncol=5, loc="upper left", frameon=False, handlelength=1.0, columnspacing=0.8, handletextpad=0.4)
    ax.set_title("(a) Right-reason detection (%)", loc="left")


def held_out_breakdown(n: dict) -> dict:
    """Recompute the composition of the 40 pre-registered held-out failures from the per-case score records."""
    sel = set(n["c3_selection"]["selected"])
    groups = {"assessable": {"ECM and DQ": 0, "ECM only": 0, "DQ only": 0, "neither": 0},
              "unassessable": {"unassessable": 0}, "no_rule": {"unassessable": 0, "assessable, no rule": 0}}
    seen = 0
    for f in glob.glob(os.path.join(PATHB, "scores_adjudicated", "*.json")):
        with open(f) as fh:
            r = json.load(fh)
        if r["corpus"] != "C3" or r["case_id"] not in sel or r["outcome_class"] != "failure":
            continue
        seen += 1
        matchable = bool(set(r["classes"]) & MATCHABLE)
        done = r["assembled_status"] == "done"
        if not matchable:
            groups["no_rule"]["assessable, no rule" if done else "unassessable"] += 1
        elif not done:
            groups["unassessable"]["unassessable"] += 1
        else:
            e = r["broken"]["ECM"]["state"] == "right_reason"
            d = r["broken"]["DQ"]["state"] == "right_reason"
            key = "ECM and DQ" if e and d else "ECM only" if e else "DQ only" if d else "neither"
            groups["assessable"][key] += 1
    assert seen == 40, seen
    a, u, z = groups["assessable"], groups["unassessable"], groups["no_rule"]
    assert sum(a.values()) + u["unassessable"] == len(n["c3_inscope"]) == 11, (a, u)
    assert u["unassessable"] == 3 and sum(a.values()) == 8, (a, u)
    h1 = n["H1.results_adjudicated.json"]
    assert a["ECM only"] == h1["b_ecm_only"] == 2 and a["DQ only"] == h1["c_dq_only"] == 0 and a["ECM and DQ"] == h1["both"] == 1
    assert sum(z.values()) == 29 and u["unassessable"] + z["unassessable"] == n["C3.n"]["unassessable"] == 10
    return groups


def panel_b(ax, groups: dict) -> None:
    cols = [("matchable,\nassembled\n(8)", groups["assessable"]),
            ("matchable,\nunassessable\n(3)", groups["unassessable"]),
            ("no matching\nrule\n(29)", groups["no_rule"])]
    shade = {"ECM and DQ": "#1F77B4", "ECM only": "#9ecae1", "DQ only": "#FF7F0E", "neither": "#ffffff",
             "unassessable": "#bdbdbd", "assessable, no rule": "#ffffff"}
    order = ["ECM and DQ", "ECM only", "DQ only", "neither", "assessable, no rule", "unassessable"]
    xs = [0.0, 1.35, 2.7]  # spread so the three-line category labels do not touch
    for xi, (lab, seg) in zip(xs, cols):
        bottom = 0
        for key in order:
            v = seg.get(key, 0)
            if not v:
                continue
            ax.bar(xi, v, width=0.55, bottom=bottom, color=shade[key], edgecolor="black", linewidth=0.5,
                   zorder=2)
            dark = key in ("ECM and DQ", "DQ only")
            if v < 2:  # a segment shorter than its label: count outside the bar, joined by a horizontal leader
                y = bottom + v / 2
                ax.plot([xi + 0.275, xi + 0.40], [y, y], color="black", linewidth=0.5, zorder=3)
                ax.text(xi + 0.42, y, str(v), ha="left", va="center", fontsize=7, zorder=3)
            else:
                ax.text(xi, bottom + v / 2, str(v), ha="center", va="center", fontsize=7, zorder=3,
                        color="white" if dark else "black")
            bottom += v
    ax.set_xticks(xs)
    ax.set_xticklabels([c[0] for c in cols], fontsize=7)
    ax.set_ylim(0, 38)
    ax.set_xlim(-0.6, 3.3)
    ax.set_yticks([0, 10, 20, 30])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    handles = [Patch(facecolor=shade["ECM and DQ"], edgecolor="black", linewidth=0.5, label="ECM and DQ"),
               Patch(facecolor=shade["ECM only"], edgecolor="black", linewidth=0.5, label="ECM only"),
               Patch(facecolor="#ffffff", edgecolor="black", linewidth=0.5, label="not detected"),
               Patch(facecolor="#bdbdbd", edgecolor="black", linewidth=0.5, label="unassessable")]
    ax.legend(handles=handles, loc="upper left", frameon=False, handlelength=1.0, handletextpad=0.4, borderaxespad=0.2)
    ax.set_title("(b) The 40 held-out failures", loc="left")


def main() -> None:
    n = load_numbers()
    groups = held_out_breakdown(n)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(5.2, 2.5), gridspec_kw={"width_ratios": [1.3, 1.1], "wspace": 0.22})
    panel_a(ax1, n)
    panel_b(ax2, groups)
    fig.subplots_adjust(left=0.055, right=0.995, top=0.90, bottom=0.235)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
