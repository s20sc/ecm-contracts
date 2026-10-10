# Sensitivity to the unresolved C3-057 / C3N-001 eligibility pair

This post-hoc analysis quantifies one fixed-sample exclusion. It does not adjudicate eligibility, reconstruct missing interfaces, establish historical causal truth, or replace the manuscript's primary results. The original model-written specifications and judgments remain unchanged.

Both specifications cite navigation2 issue #5386. C3-057 is an eligible C3 failure, selected into the frozen 40-case H1 sample, with class `other` and an unassessable provider. All five methods are unassessable for it; no method receives right-reason credit. Its associated recommended repair is also unassessable. C3N-001 is ineligible (`internal`) and has no primary score row. There is no double counting of this pair in the primary scores. The source-guided interpretations nevertheless conflict.

A later [joint source assessment](../source-assessment/README.md) assigns both records the same current status, interface eligibility unconfirmed. It retains this numerical exclusion result and the original primary inputs. The discussion below records the earlier assessment stage.

## Results

| Quantity | Preserved primary analysis | Exclude C3-057, no replacement |
|---|---:|---:|
| Overall credited detections | 14/93 (15.05%) | 14/92 (15.22%) |
| Overall Wilson 95% interval | 9.18–23.70% | 9.29–23.94% |
| C3 credited detections | 3/40 (7.50%) | 3/39 (7.69%) |
| C3 Wilson 95% interval | 2.58–19.86% | 2.65–20.32% |
| H1 ECM-only / DQ-only / both / neither | 2 / 0 / 1 / 37 | 2 / 0 / 1 / 36 |
| H1 exact two-sided McNemar p | 0.5 | 0.5 |
| C3 recommended-repair false-alarm bound | 15/44 | 14/43 |
| Overall recommended-repair false-alarm bound | 28/105 | 27/104 |
| Observed-fix false alarms, all corpora | 5/19 | 5/19 |
| Observed-fix false alarms, C3 | 1/6 | 1/6 |

Warning-only bounds and the complete-case aggregate are unchanged. The H1 sample decreases to 39, so the scorer marks it below the planned sample size. The unchanged discordant counts do not support superiority: the effect difference remains 2, below the protocol's minimum relevant gain of 4, and p remains 0.5. Denominators, rates, and intervals do change; it would be wrong to describe the conflict as having no statistical effect.

The recommended-repair bound changes because the primary rule counts an unassessable control as not accepted. Omitting the disputed case therefore removes one failure and one unassessable recommended repair. It does not remove an observed repair failure.

## Method and reproducibility boundary

1. Read the 126 retained rows in `replication_package/experiments/pathb_v2/scores_adjudicated/`. Confirm that the retained `scoring.py` functions `by_corpus(rows)` and `h1_record(rows)` exactly reproduce the full `by_corpus` and `H1` objects in `results_adjudicated.json`.
2. Form a second list containing every original row except `case_id == C3-057`. Do not replace it with the next candidate and do not include C3N-001. This respects the frozen-sample, no-replacement boundary in PROTOCOL Section 13 and scoring.py's selection logic.
3. Run `aggregate` over each full list and each C3 subset, and `h1_record` over each full list. An independent direct census of failure/credit counts and the paired sets matched these outputs. The independent exact-p calculation used twice the lower binomial tail on b+c, capped at one.
4. Assert equality of complete-case aggregates and observed-fix/warning-only false-alarm objects before and after exclusion. All assertions passed. The 137 input hashes in INPUTS.json matched again after calculation.

This is a reaggregation of stored adjudicated rows, not a fresh raw-source-to-score reproduction. It does not justify treating the alternative C3N specification as eligible: that would require a defensible specification and assembly followed by separately identified scoring. It also does not complete the study's other outstanding A2 coverage or expanded-boundary checks. The original eligibility conflict remains disclosed.
