# Mutation inventory

Code hash (scoring, baselines, assemble, build_packets, materialize, adjudicate): `3d50eb1d48e713e9dc1caae68f3e5dce5c205f4ded7c13387853e9aeaa05c825`

Baseline: pass (37 passed in 0.28s)

| mutation | file | result | tests |
|---|---|---|---|
| stats.mcnemar_constant | scoring.py | killed | 2 failed, 35 passed in 0.20s |
| stats.wilson_vacuous | scoring.py | killed | 1 failed, 36 passed in 0.17s |
| stats.zero_n_as_zero | scoring.py | killed | 1 failed, 36 passed in 0.17s |
| match.frame_to_qos | scoring.py | killed | 4 failed, 33 passed in 0.21s |
| match.token_ignored | scoring.py | killed | 1 failed, 36 passed in 0.17s |
| match.semver_counts | scoring.py | killed | 1 failed, 36 passed in 0.17s |
| prov.always_verified | scoring.py | killed | 2 failed, 35 passed in 0.21s |
| prov.ignore_adjudication | scoring.py | killed | 1 failed, 36 passed in 0.17s |
| prov.grants_open_world | scoring.py | killed | 1 failed, 36 passed in 0.29s |
| wrapper.invent_semver | scoring.py | killed | 1 failed, 36 passed in 0.18s |
| switch.scored | scoring.py | killed | 1 failed, 36 passed in 0.17s |
| agg.unassessable_dropped | scoring.py | killed | 1 failed, 36 passed in 0.16s |
| agg.false_alarm_on_broken | scoring.py | killed | 1 failed, 36 passed in 0.17s |
| agg.no_nesting | scoring.py | killed | 1 failed, 36 passed in 0.17s |
| agg.warning_not_fp | scoring.py | killed | 1 failed, 36 passed in 0.18s |
| base.nt_no_promotion | baselines_v2.py | killed | 1 failed, 36 passed in 0.23s |
| base.dq_no_durability | baselines_v2.py | killed | 1 failed, 36 passed in 0.17s |
| base.dq_no_deadline | baselines_v2.py | killed | 1 failed, 36 passed in 0.18s |
| base.di_wildcard_rejects | baselines_v2.py | killed | 1 failed, 36 passed in 0.17s |
| base.di_mixed_algorithms | baselines_v2.py | killed | 1 failed, 36 passed in 0.17s |
| asm.ignore_element_sides | assemble.py | killed | 1 failed, 36 passed in 0.17s |
| asm.pair_first_port | assemble.py | killed | 1 failed, 36 passed in 0.17s |
| asm.undetermined_as_absent | assemble.py | killed | 1 failed, 36 passed in 0.16s |
| asm.signature_not_normalised | assemble.py | killed | 1 failed, 36 passed in 0.16s |
| asm.pair_view_running_did | assemble.py | killed | 1 failed, 36 passed in 0.16s |
| mat.excerpt_by_case | materialize.py | killed | 2 failed, 35 passed in 0.20s |
| mat.refresh_dispatched | materialize.py | killed | 1 failed, 36 passed in 0.17s |
| mat.drop_resolved_commit | materialize.py | killed | 1 failed, 36 passed in 0.16s |
| fold.third_ignored | adjudicate.py | killed | 1 failed, 36 passed in 0.17s |
| fold.split_as_agree | adjudicate.py | killed | 1 failed, 36 passed in 0.16s |
| c3.no_cap | scoring.py | killed | 1 failed, 36 passed in 0.17s |
| c3.skip_gaps | scoring.py | killed | 1 failed, 36 passed in 0.16s |
| c3.h1_all_failures | scoring.py | killed | 1 failed, 36 passed in 0.16s |
| pilot.included | scoring.py | killed | 1 failed, 36 passed in 0.16s |
| mat.follow_symlinks | materialize.py | killed | 1 failed, 36 passed in 0.17s |
| pkt.drop_confidential | build_packets.py | killed | 1 failed, 36 passed in 0.17s |

36 killed, 0 survived, 36 mutations.
