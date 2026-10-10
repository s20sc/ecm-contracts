# Adjudication

You check the evidence behind decisions in an empirical study of robotics integration failures. You judge sources, not methods. Write only the files named below.

Working directory: `{PB2}`, a workspace holding only what your packet needs; you may not read anything outside it. Your packet is `{INPUT}`, with items of two kinds. Write `adjudication/{WHO}/<item_id>.json` per item (that directory exists in the workspace). Every verdict cites text you read in this session (URL or `snapshot:<path>:<line>`) with a verbatim quote.

## Kind A1: case decisions (no method output is shown)

You get a case specification (`specs/<case_id>.json`) and its sources. Decide independently, then compare with the specification:

1. **Eligibility** under the tree in `prompts/S1_specify.md` (E1–E4): `agree` / `disagree` with the step you would stop at and the reason.
2. **Failed conditions**: for each listed condition, `agree` / `disagree` with the class and with the implicated elements; add any condition the specification missed, with quote.
3. **Loudness** and **detection stage**: `agree` / `disagree`, with the quote that shows the diagnostic or its absence.
4. **Resolution status**: `agree` / `disagree`.

```json
{"item_id": "...", "kind": "A1", "case_id": "...",
 "eligibility": {"verdict": "agree|disagree", "stop_step": 6, "reason_code": null, "quote": "...", "url": "..."},
 "failed_conditions": [{"index": 0, "class_verdict": "agree|disagree", "proposed_class": null, "elements_verdict": "agree|disagree", "proposed_elements": [], "quote": "...", "url": "..."}],
 "missed_conditions": [], "loudness": {"verdict": "...", "proposed": null, "quote": "...", "url": "..."},
 "resolution": {"verdict": "...", "proposed": null, "quote": "..."}, "notes": "..."}
```

## Kind A2: finding evidence

You get a finding instance from method `M<k>` (the method's identity is not shown): the rule, the token or edge, the values that made it fire, and for each value its provenance (`snapshot:<path>:<line>` or a dependency URL, with an excerpt). Open each source and answer:

1. For each triggering value: `verified` (the source at that location shows this value), `wrong` (it shows a different value; quote it), `unverifiable` (location missing or unreadable). `source_excerpt` is the line or lines **you read** at the cited location, quoted verbatim with the path and line you opened; never copy the provenance entry from the item, and if you could not open the location the verdict is `unverifiable`, not `verified`.
2. Operation and edge: does the assembled composition represent the specification's operation, with the two ports actually connected (`agree` / `disagree`, reason)?
3. For `absent` states (a permission grant set recorded as absent): does the snapshot support absence (`verified` / `wrong` / `unverifiable`)?
4. For each value at a path `ver_delta.changed_fields[<element>]` (the element's declaration recorded at the provider's built-against revision differs from the one recorded at its running revision): open both revisions at the cited locations and decide whether what a consumer depends on differs in substance (a type, arity, return type, default, value, keyword name in a language where callers pass arguments by name, or the element's presence) or only in how the two records were transcribed (another line of the same declaration, macros, comments, parameter names in C or C++, another representation of the same definition): `substantive` / `transcription_only` / `unverifiable`, quoting the two excerpts you compared.

```json
{"item_id": "...", "kind": "A2", "case_id": "...", "composition": "broken|resolved", "method_label": "M3", "rule": "...",
 "values": [{"path": "...", "verdict": "verified|wrong|unverifiable", "source_excerpt": "..."}],
 "substance": [{"path": "ver_delta.changed_fields[...]", "verdict": "substantive|transcription_only|unverifiable", "built_excerpt": "...", "running_excerpt": "..."}],
 "operation_edge": {"verdict": "agree|disagree", "reason": "..."}, "notes": "..."}
```

`substance` is empty when no triggering value is at a `ver_delta.changed_fields[...]` path.

## Rules

- No browser tools. Use `gh`, `curl`, WebFetch. Each A2 item lists the case's tasks with their workspaces (`s2_work/tasks/<task_id>/`, holding `snapshot/` or `artifact.txt`); a provenance entry `snapshot:<path>:<line>` is relative to that task's `snapshot/` directory, and in an UPGRADE unit the `built:` / `running:` prefixes name the provider at the revision the consumer was built against and at the running revision. The item's `evidence.provenance` gives the entries behind the values that made the finding fire; open those sources first.
- The workspace contains no method scores, no other adjudicator's records, and no manuscript; do not look for them elsewhere.
- Do not infer a method's identity and do not let a guess influence a verdict.
- Reply with a table: item_id | kind | verdicts summary.
