# Portable mechanism-ledger entry

Use this publication edition of the V32 scientific package, the selected
retained task files and the V40 mechanism-ledger supplement. Their documented
role, path and comment mappings preserve the scientific algorithms and
recorded judgments without claiming byte identity with the original archive.
Copy `config.example.json`
to a configuration file and set its three input directories. `retained`
contains `uNNNN/snapshot/...` paths. Python 3.10 or newer is required; there
are no third-party dependencies and no internal review-manifest requirement.

```sh
python3 -B run_ledger.py --config /path/to/config.json --out /path/to/new-output
```

The output parent must exist. The target must be new, cannot be a symlink,
and cannot be inside an input, configuration, or delivery-code directory.
Reusing a completed or failed output is rejected. An accepted attempt keeps
`attempt.json`; runtime/preflight failures keep `failure.json` and any partial
artifacts. Invalid output locations are rejected without writing there.

The entry checks the sealed 702-input manifest and current supplement
hashes, executes the retained generator logic with three path-binding
statements adapted in memory, and rechecks inputs afterward. These pins
authenticate the publication representations; historical hashes continue to
refer to the archived bytes. The retained adjudication guard is compiled
directly from its pinned source, bypassing
bytecode caches. The retained source resolver exposes only the 51 snapshot
files read by the historical ledger; restoring extra sources cannot silently
increase its original evidence coverage.

The runtime read check examines both the requested absolute path and its
resolved target. Reads involving protected roots require sealed targets;
symlinks requested inside a protected root cannot escape that root.

Generated `mechanism-ledger.json`, `credit-case-index.json`, and
`source-sha256.json` are compared field by field with the reference records
in this edition. The derivation inventory links them to their archived
representations.
Only exact input-path aliases, `active_scope`, and the ledger generation time
may change. Every path/time change and any other difference is retained in
`comparison.json`; a scientific or structural difference fails the attempt.
This entry does not add detections, labels, source adjudications, or accuracy
claims. It regenerates the recorded ledger, not the separate manual report.

Run the bounded safety tests with:

```sh
python3 -B -m unittest test_run_ledger.py
```
