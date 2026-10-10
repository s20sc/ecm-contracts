# Mutation inventory

Code hash (scoring.py, baselines_v2.py, assemble.py, build_packets.py, materialize.py, adjudicate.py, qos_literal.py, frame_literal.py, freeze.py, report_extra.py, exploratory_consumer_blind.py): `23fcff27a528218735550d7718414903dd8fe880f48bd694ab084219e2e9da94`

Baseline: pass (65 passed in 0.41s)

Killed means a test failed on an assertion; ERROR means the run failed some other way and is not a kill.

| mutation | file | result | tests |
|---|---|---|---|
| report.distinct_counts_occurrences | report_extra.py | killed | 1 failed, 64 passed in 0.39s |
| report.strata_pooled | report_extra.py | killed | 1 failed, 64 passed in 0.41s |
| report.alert_counts_unassessable_control | report_extra.py | killed | 1 failed, 64 passed in 0.41s |
| ablation.added_reads_unverified | exploratory_consumer_blind.py | killed | 1 failed, 64 passed in 0.40s |
| ablation.mutates_input | exploratory_consumer_blind.py | killed | 2 failed, 63 passed in 0.44s |
| ablation.breaking_only_keeps_additions | exploratory_consumer_blind.py | killed | 1 failed, 64 passed in 0.40s |
| ablation.breaking_only_counts_empty_declaration | exploratory_consumer_blind.py | killed | 1 failed, 64 passed in 0.43s |
| ablation.breaking_only_missing_description_is_empty | exploratory_consumer_blind.py | killed | 1 failed, 64 passed in 0.39s |
| report.cause_share_drops_warning_cause | report_extra.py | killed | 1 failed, 64 passed in 0.38s |
| report.stage_double_counts_unknown | report_extra.py | killed | 1 failed, 64 passed in 0.39s |
| agg.by_class_every_carried_class | scoring.py | killed | 1 failed, 64 passed in 0.40s |
| stats.mcnemar_constant | scoring.py | killed | 2 failed, 63 passed in 0.42s |
| stats.wilson_vacuous | scoring.py | killed | 1 failed, 64 passed in 0.39s |
| stats.zero_n_as_zero | scoring.py | killed | 1 failed, 64 passed in 0.41s |
| match.frame_to_qos | scoring.py | killed | 5 failed, 60 passed in 0.50s |
| match.token_ignored | scoring.py | killed | 1 failed, 64 passed in 0.41s |
| match.semver_counts | scoring.py | killed | 1 failed, 64 passed in 0.41s |
| prov.always_verified | scoring.py | killed | 2 failed, 63 passed in 0.71s |
| prov.ignore_adjudication | scoring.py | killed | 3 failed, 62 passed in 0.45s |
| prov.grants_open_world | scoring.py | killed | 1 failed, 64 passed in 0.39s |
| wrapper.invent_semver | scoring.py | killed | 1 failed, 64 passed in 0.41s |
| switch.scored | scoring.py | killed | 1 failed, 64 passed in 0.43s |
| agg.unassessable_dropped | scoring.py | killed | 2 failed, 63 passed in 0.47s |
| agg.false_alarm_on_broken | scoring.py | killed | 2 failed, 63 passed in 0.46s |
| agg.unassessable_control_not_fp | scoring.py | killed | 1 failed, 64 passed in 0.42s |
| agg.unassessable_warning_not_fp | scoring.py | killed | 1 failed, 64 passed in 0.41s |
| agg.no_nesting | scoring.py | killed | 1 failed, 64 passed in 0.44s |
| agg.warning_not_fp | scoring.py | killed | 2 failed, 63 passed in 0.43s |
| base.nt_no_promotion | baselines_v2.py | killed | 1 failed, 64 passed in 0.44s |
| base.dq_no_durability | baselines_v2.py | killed | 1 failed, 64 passed in 0.44s |
| base.dq_no_deadline | baselines_v2.py | killed | 1 failed, 64 passed in 0.39s |
| base.di_wildcard_rejects | baselines_v2.py | killed | 1 failed, 64 passed in 0.43s |
| base.di_mixed_algorithms | baselines_v2.py | killed | 1 failed, 64 passed in 0.42s |
| asm.ignore_element_sides | assemble.py | killed | 1 failed, 64 passed in 0.42s |
| asm.pair_first_port | assemble.py | killed | 2 failed, 63 passed in 0.42s |
| asm.undetermined_as_absent | assemble.py | killed | 1 failed, 64 passed in 0.43s |
| asm.signature_not_normalised | assemble.py | killed | 2 failed, 63 passed in 0.48s |
| asm.canonical_keeps_macros | assemble.py | killed | 2 failed, 63 passed in 0.44s |
| asm.canonical_erases_everything | assemble.py | killed | 2 failed, 63 passed in 0.45s |
| asm.type_spelling_kept | assemble.py | killed | 1 failed, 64 passed in 0.42s |
| asm.consumer_task_is_producer | assemble.py | killed | 1 failed, 64 passed in 0.41s |
| fold.substance_ignored | adjudicate.py | killed | 1 failed, 64 passed in 0.44s |
| fold.substance_split_counts | adjudicate.py | killed | 1 failed, 64 passed in 0.40s |
| a1.packets_reshuffled | adjudicate.py | killed | 1 failed, 64 passed in 0.40s |
| a1.guard_after_delete | adjudicate.py | killed | 1 failed, 64 passed in 0.41s |
| c3.adjudicated_walk | scoring.py | killed | 1 failed, 64 passed in 0.42s |
| fold.missed_single_dropped | adjudicate.py | killed | 1 failed, 64 passed in 0.42s |
| fold.missed_third_ignored | adjudicate.py | killed | 2 failed, 63 passed in 0.44s |
| a3.one_packet | adjudicate.py | killed | 1 failed, 64 passed in 0.40s |
| a3.stale_kept | adjudicate.py | killed | 1 failed, 64 passed in 0.41s |
| fold.adj1only_keeps_adj2 | adjudicate.py | killed | 1 failed, 64 passed in 0.42s |
| fold.adj1only_overwrites_primary | adjudicate.py | killed | 2 failed, 63 passed in 0.44s |
| a2.positional_ids | adjudicate.py | killed | 1 failed, 64 passed in 0.43s |
| a2.single_score_dir | adjudicate.py | killed | 1 failed, 64 passed in 0.40s |
| score.shared_dir | scoring.py | killed | 1 failed, 64 passed in 0.40s |
| score.variant_reads_primary_overrides | scoring.py | killed | 1 failed, 64 passed in 0.40s |
| strata.same_repo_any | scoring.py | killed | 1 failed, 64 passed in 0.40s |
| strata.same_repo_git_suffix | scoring.py | killed | 1 failed, 64 passed in 0.42s |
| a1.pilot_included | adjudicate.py | killed | 1 failed, 64 passed in 0.41s |
| freeze.ledger_by_basename | freeze.py | killed | 1 failed, 64 passed in 0.41s |
| qos.reads_explanation | qos_literal.py | killed | 1 failed, 64 passed in 0.41s |
| qos.named_profile_literal | qos_literal.py | killed | 2 failed, 63 passed in 0.44s |
| qos.producer_task_both_sides | qos_literal.py | killed | 2 failed, 63 passed in 0.45s |
| qos.outside_snapshot | qos_literal.py | killed | 1 failed, 64 passed in 0.40s |
| qos.no_prose_in_artifacts | qos_literal.py | killed | 1 failed, 64 passed in 0.39s |
| qos.unit_changed_in_place | qos_literal.py | killed | 1 failed, 64 passed in 0.42s |
| sens.excerpt_not_excluded | scoring.py | killed | 1 failed, 64 passed in 0.42s |
| sens.qos_reuses_primary | scoring.py | killed | 1 failed, 64 passed in 0.40s |
| sens.qos_ignores_here | scoring.py | killed | 1 failed, 64 passed in 0.40s |
| asm.pair_view_running_did | assemble.py | killed | 1 failed, 64 passed in 0.41s |
| mat.excerpt_by_case | materialize.py | killed | 2 failed, 63 passed in 0.42s |
| mat.refresh_dispatched | materialize.py | killed | 1 failed, 64 passed in 0.40s |
| mat.drop_resolved_commit | materialize.py | killed | 1 failed, 64 passed in 0.40s |
| fold.third_ignored | adjudicate.py | killed | 1 failed, 64 passed in 0.40s |
| fold.split_as_agree | adjudicate.py | killed | 1 failed, 64 passed in 0.40s |
| c3.no_cap | scoring.py | killed | 1 failed, 64 passed in 0.39s |
| c3.skip_gaps | scoring.py | killed | 1 failed, 64 passed in 0.40s |
| c3.h1_all_failures | scoring.py | killed | 2 failed, 63 passed in 0.42s |
| pilot.included | scoring.py | killed | 1 failed, 64 passed in 0.41s |
| mat.follow_symlinks | materialize.py | killed | 1 failed, 64 passed in 0.40s |
| qos.bare_ref_ignored | qos_literal.py | killed | 1 failed, 64 passed in 0.46s |
| qos.bare_ref_no_boundary | qos_literal.py | killed | 1 failed, 64 passed in 0.45s |
| frame.description_kept | frame_literal.py | killed | 1 failed, 64 passed in 0.40s |
| frame.tokens_nulled | frame_literal.py | killed | 1 failed, 64 passed in 0.41s |
| frame.never_nulls | frame_literal.py | killed | 1 failed, 64 passed in 0.38s |
| frame.unit_changed_in_place | frame_literal.py | killed | 1 failed, 64 passed in 0.41s |
| sens.frame_reuses_primary | scoring.py | killed | 1 failed, 64 passed in 0.41s |
| fold.nosubstance_ignored | adjudicate.py | killed | 1 failed, 64 passed in 0.45s |
| fold.nosubstance_same_dir | adjudicate.py | killed | 1 failed, 64 passed in 0.41s |
| pkt.drop_confidential | build_packets.py | killed | 1 failed, 64 passed in 0.40s |

90 killed, 0 survived, 0 error, 0 not applied, 90 mutations.
