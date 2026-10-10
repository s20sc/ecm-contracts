# Public replay entry point

This is a delivery-only adaptation of the archived boundary, consumer-contrast,
and original adaptive-client runners. Recorded predictions, results and
failed attempts remain separate historical evidence. Public source and receipt
representations use the documented role and path mappings; they do not claim
byte identity with the original archive. The delivered copies retain
declaration extraction, the fixed ECM checker, provider binding,
endpoint execution, metadata observation, and outcome validation.

The private review-tree guard is replaced by `public-inputs.json`: content pins
for this publication edition of the scientific package, retained provider/client source, source
intake, and this runtime. Changed/missing inputs and added Python source in the
listed import trees fail verification. Output paths inside any input root are
refused. This guard is not a cryptographic signature or an OS write lock.

## Inputs and setup

Use Python 3.11 with pip 25.0.1, pytest 9.0.3, and pluggy 1.6.0 (plus their normal
installation dependencies). For a clean environment, also install a real pytest plugin,
for example pytest-asyncio 1.4.0, so the adaptive client can inspect a nonempty
pytest11 group. Plugin autoload stays disabled and adaptive discovery never
loads the plugin. The original host had four such entries; the new host need
not reproduce that count. No automatic install or network download occurs.
The runtime records the exact interpreter and package source pins used locally.
A clean Python environment is recommended; this delivery has not yet been
validated on a second operating system or independently provisioned machine.

Place this edition's scientific replication package, selected retained source,
and CPython 3.12 source intake at paths specified in a configuration JSON:

```json
{
  "schema": 1,
  "package": "inputs/replication_package",
  "retained": "inputs/tasks",
  "intake": "inputs/cpython312",
  "previous_contrast": "outputs/contrast"
}
```

Relative paths resolve against the configuration file, not the current working
directory. The retained task directory follows `<task>/snapshot/<source path>`
and `<task>/recon/<task>.json`. Source bytes are recoverable from the existing
content-addressed `snapshots.zip` plus `snapshots.json`; do not create another
full snapshot archive. `public-inputs.json` lists the exact required source
paths and hashes. Keep the existing archive and its hash in the overall release
inventory: it is a distribution asset, not re-read on every endpoint call.

The intake directory contains `source-intake.json`, `helper-source-intake.json`,
and `provider3.12/*.py` at the recorded CPython commit. The input manifests in the
historical receipts describe the old execution environment. Their public copies
replace the exact author-machine prefixes with documented aliases while
preserving the recorded outcomes and failures. Historical hashes refer to the
archived bytes; current publication pins bind their public representations.
This runtime uses the new configuration for a fresh execution.

## Commands

```sh
python3 -B replay.py verify --config /path/to/config.json
python3 -B replay.py contrast prepare --config /path/to/config.json --output /path/to/outputs/contrast
python3 -B replay.py contrast run --config /path/to/config.json --output /path/to/outputs/contrast
python3 -B replay.py adaptive prepare --config /path/to/config.json --output /path/to/outputs/adaptive
python3 -B replay.py adaptive run --config /path/to/config.json --output /path/to/outputs/adaptive
```

Use the same configuration throughout. Adaptive replay binds to the newly
completed six-cell contrast in `previous_contrast`, including its metadata
inventory. `boundary prepare` and `boundary run` execute the earlier four-cell
subset separately when that specific reproduction is required. Each prepare
requires a new output directory; run rejects existing outcome receipts.
Do not edit inputs after preparing a run. Preserve failed attempts and choose a
new directory after a repair.

## Interpretation

These are fresh host-dependent observations, not replacements for historical
receipts. Counts of installed distributions and entry points, metadata hashes,
paths, and warnings can differ across machines. The adaptive mapping groups
must be nonempty and equal across providers on the same presealed host.
A real consumer failure at the expected original call site is an observed
outcome, not successful execution of that consumer. `complete_cells` counts
valid observations, including the explicitly recognized consumer failure.

No human reference is created, no primary failure labels are changed, and these
replays do not establish an independent full scientific Accept or reproduce
historic host counts by fiat. The 545 original missing-metadata entries remain
historical absence observations; a new host inventories its own presence and
absence before/after execution. No synthetic metadata fixture is substituted
for the reported real-host experiment.
