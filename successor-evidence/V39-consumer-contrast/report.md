# Real endpoint contrast, sealed before execution

Six observations completed; five endpoints succeeded and one original client
failed. This means six observations, not six successful workflows or six accuracy
samples. Raw data remain outside the vault; compact hash-bound receipts are here.

| Provider source | Original rosidl pytest endpoint | Installed pip25.0.1 list endpoint | Upgrade predictions from3.9 |
|---|---|---|---|
| CPython3.9.0 | EntryPoint.load and pytest executed;81 tests pass |149 packages; actual selected-provider objects |Baseline only|
| CPython3.10.0 |81 pass;2 deprecation warnings |Identical149-package output|rosidl reject;pip accept|
| CPython3.12.0 |AttributeError: EntryPoints has no get; original get_entry_points line39; no load/pytest call|Identical149-package output|rosidl reject;pip accept|

Predictions were written before running workflows. All version strings retain
major3; the frozen assembler/checker is unchanged. The declaration surface contains
only the AST argument/return descriptions of entry_points and distributions, plus
the clients' actual direct references. Baselines are not extra predictions.

The3.10 rejection remains a scoped false alarm when warnings are allowed. The3.12
rejection coincides with a real failure at the original client's dict-style get;
pip is an independent unaffected endpoint. This is selected, post-outcome,
current-host evidence under Python3.11.2, not deployment on the historical
interpreters, complete API coverage, prospective accuracy, general SemVer validity,
consumer-aware superiority, a primary control label, or a human reference.

All549 presealed input hashes and the6695-file V38 seal remained unchanged.
Within-cell metadata fingerprints and all six cross-cell metadata inventories
were identical (1509 candidates). All three pip outputs share the complete
normalized name/version SHA256
`dcf20ef83c73412ecb3ca3c7551fe963dc2baafe7cc50041fb326335c48d68b2`.
Each successful pytest run reports5252 ResourceWarnings from unclosed files;
these are disclosed and do not become warning-free execution claims.

No provider, consumer, checker, primary score, label or control was patched.
The process-local binding and discovery-only host bridge are part of the harness
and are disclosed. The independent code review identified the need to compare
metadata across all six cells; this separate post-run integrity guard passed.
