# Compatible-change retained-source replay

This delivery copy relocates the archived source-comparison script. Its provider/consumer
loading, discovery binding, metadata monitoring, four endpoints, mapping
comparison, and source-stability predicates are preserved. Public representations
of the historical script, protocol and observations remain under
`successor-evidence/`; documented role, path and comment changes mean these
copies need not be byte-identical to the original archive. Current input pins
bind this publication edition; historical hashes retain their original meaning.

Use Python 3.11 and restore the selected source files using
`delivery-input-tools/restore_retained.py` with
`SUPPLEMENT_RETAINED_INPUTS.json`. No package installation is performed.
Create a configuration file (relative paths resolve from that file):

```json
{
  "schema": 1,
  "package": "replication_package",
  "retained": "/path/to/restored/tasks",
  "supplement": "successor-evidence"
}
```

```sh
python3.11 -B delivery-compatible/replay.py --config config.json \
  --output-dir /path/to/new-output-directory
```

The output parent must already exist. All inputs, including the script itself,
are hash-checked before and after execution. Retained provider helpers must
exactly match the source inventory; bytecode and native extensions in that tree
are rejected so they cannot shadow the sealed Python source. Output
must be outside all input roots. Each attempt reserves a new directory; keep
failed/interrupted attempts and inspect `run-summary.json` and `result.json`.
If a preflight fails, there is no `result.json` and no endpoint was executed.

The protocol's historical snapshot location is replaced by the explicitly
configured restored sources, with the same snapshot hashes. This is a declared
delivery-path adaptation, not an execution at the historical location.
Real installed distribution metadata is used; plugins are never loaded.
Counts and path fingerprints depend on the current host. A successful run does
not establish historical output identity, a new primary evaluation, independent
clients, or an original ROS/CPython 3.9/3.10 deployment. Four nonempty maps and
their six pairwise equality results are reported separately. The original
completion predicate is preserved; inspect equality before drawing that claim.

The original fingerprint function checks stat equality while reading (including
access time); filesystems that change it on reads may fail conservatively.
No guard is disabled to force a completed run.
