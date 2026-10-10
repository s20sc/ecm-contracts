# Port provenance check

You check whether recorded interface values are supported by the source they cite. You judge sources only; you are not told what any value is for.

Working directory: `{PB2}`, a workspace holding only what your packet needs; you may not read anything outside it, and you must not use the network. The `snapshot` entries under `s2_work/tasks/<task_id>/` are symbolic links into the workspace's snapshot store; they are part of the working directory, and you must read through them. Your packet is `{INPUT}`. Write one record per item to `adjudication/{WHO}/<item_id>.json`, and nothing else.

Each item names a unit at one revision (`task_id`), one interface element (`element`, with the `side` the unit takes), the values a description run recorded for that element (`values`, keyed by field), and for each value the provenance string the run recorded (`provenance`): `snapshot:<path>:<line or line range> | <verbatim excerpt>` for a code snapshot under `s2_work/tasks/<task_id>/snapshot/`, or `artifact:<line or line range> | <excerpt>` for a quoted-artifact unit under `s2_work/tasks/<task_id>/artifact.txt`. Several locations may be joined with `;`.

For each value:

1. Open the cited location yourself (do not trust the excerpt) and decide:
   - `verified`: the source at that location states this value (the same identifier, type name, frame string, unit, quality-of-service setting, rate, or definition), allowing only the description's canonical spellings (`pkg/Type` for `pkg::msg::Type`, `per_message` or `none` as frame tokens, hash values as the hashing tool `definition_hash.py` computes them);
   - `wrong`: the location is readable and states a different value; quote what it states;
   - `unverifiable`: the location is missing, unreadable, or does not mention the value.
   A provenance string that gives a command, a URL, or a statement instead of a location is treated as `unverifiable`, with one exception: a `definition_hash.py` command over a file in the snapshot, which you run and compare.
2. Give `source_excerpt`: the line(s) you read, verbatim, at most 300 characters.
3. For a quality-of-service value, also say whether the cited line sets the value literally in code or configuration (`literal`), names a library default or a named profile (`default`), or leaves the value to a run-time choice (`runtime`), in `qos_basis`; leave it null for other fields.

Record format:

```json
{"item_id": "...", "kind": "P", "task_id": "...", "element": "...", "side": "...",
 "values": [{"field": "msg_type", "recorded": "...", "verdict": "verified|wrong|unverifiable", "source_excerpt": "...", "qos_basis": null}],
 "notes": "..."}
```

Rules: read only inside the working directory; write only the records; do not modify anything under `s2_work/`; every verdict rests on a location you opened; if a snapshot directory is empty or a path does not exist, say so in `notes` and mark the value `unverifiable`.
