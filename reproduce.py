#!/usr/bin/env python3
"""One-command reproduction harness for the ECM Contracts Path B evaluation.

Runs, in order, using only the Python standard library and no network:
  1. checker/selftest.py        -- asserts the frozen checker behaves as specified
  2. scoring/canonical_scores.py -- regenerates the recall / per-dim / stats numbers
  3. scoring/stats.py            -- Wilson CIs + exact McNemar tests

Then prints the headline results. Tables are written to ./tables/.

Usage:  python3 reproduce.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable or "python3"


def run(label, args, cwd):
    print(f"\n{'=' * 70}\n{label}\n{'=' * 70}")
    proc = subprocess.run([PY, *args], cwd=cwd, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    return proc


def main():
    # 1. Frozen-checker self-test (must pass).
    proc = run("[1/3] checker self-test", ["selftest.py"], cwd=os.path.join(HERE, "checker"))
    if proc.returncode != 0:
        sys.exit("checker self-test FAILED -- aborting reproduction.")

    # 2. Canonical scoring pass (regenerates every reported number + tables).
    proc = run("[2/3] canonical scoring", ["canonical_scores.py"], cwd=os.path.join(HERE, "scoring"))
    if proc.returncode != 0:
        sys.exit("canonical_scores.py FAILED.")

    # 3. Statistical inference (Wilson CIs + exact McNemar).
    proc = run("[3/3] statistical inference", ["stats.py"], cwd=os.path.join(HERE, "scoring"))
    if proc.returncode != 0:
        sys.exit("stats.py FAILED.")

    # Headline summary, read back from the regenerated numbers.
    nums = json.load(open(os.path.join(HERE, "data", "canonical_numbers.json")))
    rb, ros2 = nums["robust"], nums["ros2"]
    rb_ecm, rb_n = rb["per_method"]["ECM-full"], rb["n"]
    rb_sq = rb["per_method"]["schema+QoS"]
    r2_ecm, r2_n = ros2["per_method"]["ECM-full"], ros2["n"]
    r2_sq = ros2["per_method"]["schema+QoS"]
    kappa = json.load(open(os.path.join(HERE, "data", "kappa_result.json")))

    print(f"\n{'=' * 70}\nHEADLINE RESULTS\n{'=' * 70}")
    print(f"ROBUST substrate : ECM-full {rb_ecm}/{rb_n} "
          f"({round(100 * rb_ecm / rb_n)}%)  vs schema+QoS {rb_sq}/{rb_n} "
          f"({round(100 * rb_sq / rb_n)}%)")
    print(f"ROS2 corpus      : ECM-full {r2_ecm}/{r2_n} "
          f"({round(100 * r2_ecm / r2_n)}%)  vs schema+QoS {r2_sq}/{r2_n} "
          f"({round(100 * r2_sq / r2_n)}%)")
    print(f"McNemar (ECM vs schema+QoS): ROBUST p={rb['mcnemar']['p']:.2e}, "
          f"ROS2 p={ros2['mcnemar']['p']:.2e}")
    print(f"Gold-label inter-rater agreement: kappa = {kappa['kappa']:.2f} "
          f"({kappa['band']})")
    print("\nReproduction complete. Tables written to ./tables/.")


if __name__ == "__main__":
    main()
