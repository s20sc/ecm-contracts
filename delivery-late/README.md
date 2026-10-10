# Portable seven-case late replay

This is a separate delivery entry. It executes the retained V34
`late/replay.py` evaluation logic with explicit, sealed logical-path aliases.
The original `main` is never called. Public source and receipt copies use the
documented role, path and comment mappings. Historical result values and
algorithm versions are preserved; these copies do not claim byte identity with
the original archive.

Use Python 3.10 or later (the earlier delivery was exercised on Python 3.11). No third-party packages,
installation, network, ROS, GPU, archive extraction or model calls are needed.
The public input seal names 50 files already selected for publication. Only the
21 retained source slices used by the original late inputs are required; this
entry does not consume the separately restored 176 task files.

The two modes must run in separate fresh interpreters:

- `historical` loads the seven designated `historical-project` aliases and the
  publication FREEZE for those historical algorithm versions. These copies are
  documented derivatives; historical scoring and canonical implementations
  are not replaced by their current counterparts.
- `current` loads the active replication package's eight modules, including
  `adjudication_guard`, and its current FREEZE. Its reference is the V40
  current-active record authenticated by the V41 identity work.

## Run

Place this directory as `delivery-late/` alongside `replication_package/`,
`historical-project/`, and `successor-evidence/` in the reviewed public tree.
The seal also refers to selected historical evidence files using their explicit
public paths. Verify `public-input-seal.json` against the independently trusted
digest below (or its published successor). The adjacent `.sha256` file is a
convenience record, not a cryptographic signature.

```text
b46b85f7542149cee77f6ddff906723ef3043abc083f54f463aeab3461bb1701
```

```sh
python3 -B delivery-late/replay.py \
  --public-root /path/to/public-tree \
  --seal-sha256 b46b85f7542149cee77f6ddff906723ef3043abc083f54f463aeab3461bb1701 \
  --mode historical --output-dir /path/to/new-historical-output

python3 -B delivery-late/replay.py \
  --public-root /path/to/public-tree \
  --seal-sha256 b46b85f7542149cee77f6ddff906723ef3043abc083f54f463aeab3461bb1701 \
  --mode current --output-dir /path/to/new-current-output
```

`--seal` optionally selects a different reviewed seal file. Paths in the seal
are relative to `--public-root`; unknown aliases, traversal and escaping
symlinks fail. The output's parent must exist. Output directories must be new
and outside the input and delivery-source roots. Failed attempts are retained
with `failure.json`; result mismatches also retain the result and comparison
receipt. Reusing an existing output is rejected without changing it.

## Checks and boundaries

Preflight parses the same raw seal bytes whose digest it authenticates, records
resolved roots, and authenticates every listed input, then verifies
module hashes against the selected mode's publication FREEZE. Original freeze
times and historical amendment hashes do not date or authenticate these
derivative bytes. The public seal
replaces the V41 runner's private V40-manifest receipt-authentication dependency;
it is not represented as that old manifest or old runner hash.

During evaluation, the guard denies writes, network, subprocesses, native-library
loading and filesystem mutation. Reads are limited to sealed inputs, this
entry, its seal and standard-library files. Sources are compiled from their
verified bytes without target bytecode caches; observed `__file__` values and
code filenames must agree. Receipts distinguish function calls from modules
that were only loaded. All 50 input hashes, the runner and seal are checked
again before outputs are written. The original source-anchor, declaration,
missingness and seven-case constraints execute unchanged before and after the
scientific computation.

Results are compared recursively with type sensitivity, including all seven
case rows, census, complete aggregate, bindings and whole JSON. Historical and
current modes compare with their respective reference; their differing
historical/current pairwise fields are never normalized away.

This is a coordinator-built, unblinded, post-outcome source-slice replay. It does
not rerun original S2, recreate ROS/runtime failures, validate historical labels
or establish independent human ground truth, expanded-boundary completeness,
primary-study gain or prospective accuracy.

`python3 -B delivery-late/test_guard.py` runs eight focused guard tests.
Independent review of this new delivery entry remains a separate gate.
