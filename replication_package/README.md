# Deterministic numerical reproduction

This directory contains the computation and recorded inputs for the retrospective study. It is a publication derivative: neutral role identifiers and path aliases replace internal working names, with changes recorded separately. The original historical freeze times do not date this export. Current integrity manifests and historical provenance have different purposes; see ../PUBLIC_EDITION.md.

Model-generated specifications and model judgments are research inputs, not human ground truth. Reproducing their scores does not verify the labels, prove superiority or recreate historical blinding.

## Full numerical replay

Use Python 3.10 or later and a filesystem supporting hard links. Allocate about 3 GB of new writable output space (about 6 GB without hard links). No network, model account, ROS, GPU or TeX is needed. The separately distributed source snapshot archive is REQUIRED for this complete command; browsing the repository does not require it.

```sh
python3 -B reproduce.py --snapshot-archive /path/to/snapshots.zip --out /a/new/output/directory
```

Choose a new output directory outside this package for each run. Never reuse an earlier output or point the command at the preserved input directories. The command verifies the package and archive pins, restores 391 source trees, reconstructs three adjudication folds and current/freeze-time assembly readings, recomputes seven score sets and result files, and checks 44 main/binary table fragments plus the separate loudness table. All result fields and per-case identities are checked. Five explicitly enumerated historical H1 wording differences are the only baseline result exception; see evidence/known-pre-adjudication-wording-differences.json.

A Python audit hook blocks network calls and reads of an author's home outside the selected output. It is not an OS sandbox. The interpreter's standard library and dependencies must resolve outside user-home prefixes, so some home-installed environments fail the preliminary import probe. Select an appropriate interpreter; do not disable the guard. Inputs may be read-only. File content and internal relative links are materialized into new writable output, without copying original ownership, flags or permissions.

Successful execution must leave verification.json and the individual comparison receipts in the output directory. Any recorded historical success is evidence for its recorded inputs, not automatic validation of this publication derivative. Local publication checks must complete before this candidate is released.

## Focused verification commands

Run from this directory. The first command requires pytest; the rest use the standard library.

```sh
python3 -B -m pytest -q -p no:cacheprovider experiments/pathb_v2/test_scoring.py experiments/pathb_v2/test_adjudication_guard.py experiments/pathb_v2/test_proposal_conflicts.py
python3 -B experiments/pathb_v2/test_supplementary_binary_metrics.py
python3 -B test_reproduction_reports.py
python3 -B test_loudness_report_gate.py
python3 -B test_shared_snapshot_inputs.py
python3 -B derived_loudness/test_loudness_analysis.py
python3 -B test_python_preflight.py
```

Do not recursively run every historical test copy. Archived copies under frozen_snapshots and historical_boundary depend on different module sets; eight such collection attempts previously failed due to missing historical imports. Substituting current modules would mix versions. The historical mutation report is also not a test-adequacy result for today's code.

## Data and interpretation

- experiments/pathb_v2 contains case specifications, final descriptions, assembly, adjudication packets and records, disagreements, exclusions and the recorded protocol/deviation history. The role ledger maps ADJ1/ADJ2/ADJ3 to the actual model identities. Withdrawn and unused roles remain distinguished; see ../METHODS.md.
- experiments/pathb contains the contract checker and retained historical inputs for the correction ledger. Registry entries for precondition and resource_unmet are not implemented capabilities: no executable rule emits them. The resource rule checks declared exclusive-lock conflicts, not all resource conditions.
- expected contains recorded results/table references. Recomputed files go into new output. The current per-finding credit gate requires affirmative active A2 evidence; absent, superseded or unresolved evidence does not confer adjudicated credit. Before-adjudication readings remain explicit.
- snapshots.json describes 391 available source trees in the separately supplied archive. The 439-entry task ledger also includes excerpt, unavailable or withdrawn tasks without source trees. See ../sources/README.md for browsable retained files and source identities.
- evidence and selection_provenance contain scoped recorded checks, including the correction history. Frozen timestamps, model identity, deviations and withdrawal reasons remain historical information; publication representation changes do not make them new independent observations.
- runtime contains recorded demonstrations. Its verify_archived_records.py checks stored bytes and summaries; it does not run ROS, Docker or a remote system.

After the full replay, exploratory_consumer_blind.py may be run from the reconstructed work/experiments/pathb_v2 directory. Its additional matches are provisional and unadjudicated; they are not primary detections. The main command does not rerender the results figure or execute the later source/client workflows. Those have separate instructions under the repository's delivery-* directories. Later observed-fix controls, retained-client replays, manual semantic source checks and the eligibility sensitivity are not all established by one numerical replay exit code.

All underlying scientific limitations remain: model labels, post-outcome decisions, unresolved source interpretations, narrow implemented rules, and same-host validation do not establish independent ground truth, a positive held-out result or production suitability. Third-party material retains its own licensing and attribution; see ../THIRD_PARTY_SOURCES.md.
