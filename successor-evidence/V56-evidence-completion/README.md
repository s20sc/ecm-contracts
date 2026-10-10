# Supplementary source assessment and eligibility sensitivity

This dated post hoc supplement accompanies the revised manuscript. It adds seven source-review records omitted from the original control-finding packets, records dispositions for seven boundary candidates, and jointly treats C3-057 / C3N-001 as one incident with unconfirmed interface eligibility. It preserves the historical primary analysis.

## Findings

- Review records cover 44/44 control findings: 37 historical plus seven supplementary. Three supplementary differences concern representation, one adds an optional parameter, and three xacro judgments remain indeterminate. Reviewed does not mean positively verified. Every actual control rejection remains counted.
- Of seven boundary candidates, three have undocumented runtime outcomes. Of four reported failures, one lacks an adequate receiver declaration and three are unsupported under the retained matching classifications. No new detection credit is assigned. Full expanded-boundary performance remains unidentified.
- A reported retest recovered after removal of a DDS profile; retained MoveIt code exposes sign loss before a quaternion sign check. Neither establishes a complete historical deployment or a source-complete working control.
- Removing C3-057 without replacement gives 14/92 overall and 3/39 on reserved failures. C3N-001 has no primary score row and is not added. H1 remains b=2, c=0, p=0.5. Recommended-fix bounds change to 14/43 for C3 and 27/104 overall; observed-fix and complete-case results are unchanged.

## Recompute

From the repository root, using Python 3.10 or later and a new output file outside both input directories:

```sh
python3 -B successor-evidence/V56-evidence-completion/recompute.py --package replication_package --out /tmp/ecm-evidence-result.json
```

This verifies the current evidence inventory, exact source quotes, seven census gaps, seven method-state records, and original 126-row numerical reaggregation. It then computes the separate 125-row exclusion reading. It does not regenerate model judgments, execute ROS, or repair missing historical data. The command needs no full snapshot download or network access. Output uses portable evidence/package path prefixes.

`source-map.json` binds selected original source copies. `control-source-review.json` retains per-item quotes and judgments. `joint-eligibility.json` distinguishes the original report from a later fix on another platform. `boundary-source-inputs.json` and `retained-boundary-replay.json` retain the prior source record and replay; their historical binding hashes refer to that original run, not to this derivative's execution. `auxiliary-sources/` contains newly retrieved pinned upstream files; `fresh-sources/` retains dated issue-comment retrievals. Recorded project-relative origins describe archive provenance, not additional runtime dependencies. Original source quotations remain unchanged.

The supplementary judgments were assembled with model assistance after outcomes were known. A separate GPT-6.1-sol request checked boundary evidence, and Grok 4.7 High checked supplied control excerpts; Grok requested three evidence/wording corrections and subsequently closed them. The serving identity of the GPT request was not independently exposed. These checks are limited model-assisted source assessments, not independent human labels or new runtime experiments. Historical adjudicator aliases in the census use the same neutral role mapping as METHODS.md.

The original numerical result's SHA256 and the exact public scientific-result comparison are recorded in the repository's publication update and validation records. Public inventories identify current files; they do not certify historical blinding or semantic truth. All third-party notices continue to apply.
