# Post-outcome review addendum (V28, 2026-10-03)

These additions answer specific V27 review findings. They preserve all original specifications, selection records, primary scores, A2 packets, adjudications and provenance labels. They supply neither independent human validation nor the protocol's still-incomplete expanded-boundary sensitivity. No new model inference or runtime experiment is represented here.

## Same-source boundary alternative

`cross-frame-primary-source-crosswalk.json` compares the **recorded first-source URLs** across the 152 C3 and 30 C3-neutral frame entries. It identifies two shared-source pairs, one with opposite eligibility decisions (C3-057/C3N-001). This is not an exhaustive search for all possible duplicate reports or a unique-issue count.

`boundary-sensitivity.json` reaggregates retained case scores after excluding C3-057 under the same internal-controller interpretation already assigned to C3N-001. No replacement case is selected. C3 selected failures change 40→39; H1 b=2/c=0/p=.5 and common complete-case binary observations remain unchanged, while conservative rates and affected strata change. The JSON includes all before/after differences and the 444 files actually read. This does not rerun the checker: run the complete package reproduction separately.

```sh
python3 -B posthoc_review_v28/replay_boundary.py --package . > /outside/package/boundary-sensitivity.json
```

`chronology-correction.json` records PR6336's source-verified merge date, 11 August 2026. The source API response and retrieval receipt accompany it. The historical C3N-001 specification incorrectly says 2025 and is intentionally not rewritten. The timestamp correction alone is not an eligibility adjudication.

## Historical A2 coverage and source-only checks

The census distinguishes 44 actual control-rejection finding instances from the 48 historical A2 items. 37 findings have an active A2 item; 7 warning-only findings across C3-063 (3),C3-135 (1),robust_fa64ec6 (3) lack one. Twenty A2 items cover the 37 findings; six of those items retain transcription-only verdicts. A generated item having completed records is different from complete coverage of the required finding set.

`C3-063-posthoc-source-audit.json` and `additional-warning-control-source-audit.json` preserve the separately timed coordinator source-only assessments. The fourteen source files in `source-extracts/` are the exact snapshot files named in its receipt. They show why declaration-string changes alone do not establish the alleged interface break. They do not establish complete behavioral equivalence, repair the historical A2 process, or change actual false alarms.

The original `additional-warning-control-source-audit.json` still says independent coverage refutation was pending when written. That is a historical status, retained with the original bytes. The later independent coverage refutation confirmed the 44/37/7 census and is recorded with the manuscript's review audit; it independently verifies coverage enumeration, not the scientific correctness of every source-only assessment. The portable `control_coverage_census.py` reproduces `control-coverage-census.json`. It records the 312 package dependencies actually read, locks the historical 126 nonpilot score identities, and rejects pilot substitution. Independent tests verified unchanged output, exact read dependencies, no package writes, path relocation and malformed-input rejection. This validates the census implementation, not the labels or source-only scientific judgments.

```sh
python3 -B posthoc_review_v28/control_coverage_census.py --package . > /outside/package/control-coverage-census.json
```

## Reproduction and disclosure boundary

The read-only scripts print JSON; write their output **outside the input package**. Compare complete JSON objects, including dependency receipts. These addenda are separate from the 170-test baseline and the original reproduction wrapper. Inclusion in a local review package does not imply public deposit, permission to redistribute third-party files, author confirmation or journal acceptance.
