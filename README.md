# ECM Contracts: research code and data

This repository accompanies the retrospective feasibility study of declaration-level interface contracts for embodied agents. Start with the code and data directories below, the recorded annotation method in [METHODS.md](METHODS.md), and the source browser in [sources/README.md](sources/README.md).

Model-written specifications and model adjudications are research inputs, not independent human ground truth. The held-out comparison does not establish superiority. The separately labelled eligibility-exclusion sensitivity does not resolve the underlying disputed eligibility judgment.

This edition separates reader instructions from retained scientific provenance. [PUBLIC_EDITION.md](PUBLIC_EDITION.md) explains the representation changes and validation boundaries. A current file digest is not evidence that a changed publication representation was present at the original freeze date.

## Contents

- `replication_package/`: the publication representation of the scientific package,
  its current `PACKAGE_MANIFEST.json`, deterministic reproduction code, and recorded data.
- `snapshots.zip`: the separately distributed content-addressed source asset,
  placed under `replication_package/` or supplied with `--snapshot-archive`.
  Its SHA256 and size are recorded in `ARTIFACTS.json`; it is not duplicated in
  the Git tree.
- `successor-evidence/`: later source checks, narrowed interpretation,
  compatible-change replays, and preserved per-observation results.
- `execution-records/`: recorded attempts and inputs, including preparation and
  harness failures. Machine-specific paths are represented by documented aliases;
  these records are not portable instructions or promises of a supported old environment.
- `historical-project/`: specifically retained analysis inputs that differ
  from the V32 package. Do not silently substitute one implementation for another.
- `upstream-evidence/` and `third-party-notices/`: selected upstream sources,
  original notices, source URLs, and retrieved license text.
- `delivery-runtime/` and `delivery-input-tools/`: delivery-only entry points
  for the V38 boundary, V39 contrast, and V41 adaptive-client workflows.
- `delivery-compatible/`, `delivery-late/`, and `delivery-ledger/`: configured
  retained-source comparison, historical/current late replay, and mechanism
  ledger regeneration. Their own READMEs specify inputs and output boundaries.
- `delivery-validation/`: new same-host validation records for those entry
  points. They do not replace the historical observations.

A numerical reproduction validates the recorded computations, not the correctness of every source interpretation or model label.

## Primary deterministic reproduction

See `replication_package/README.md` for the supported interpreter, filesystem,
space, read-only-input, and historical-code boundaries. It documents a full
numerical replay that requires several GB of writable output space:

```sh
python3 replication_package/reproduce.py --out /a/new/output/directory \
  --snapshot-archive /path/to/existing/snapshots.zip
```

The snapshot asset is separately hash-bound. No model generation, ROS/GPU run,
or historical annotation is recreated by this command. Historical test copies
are preserved as evidence; recursively running every archived `test_*.py` is
not the supported verification procedure. Later source-based supplements are
separate from this base command; do not infer their validation from its exit code.

## Three-provider/client delivery replay

Follow `delivery-input-tools/README.md` to restore the 51 selected retained
files (181,251 bytes) for the three delivery workflows, not the entire snapshot
corpus. For the wider source-evidence checks, pass `SUPPLEMENT_RETAINED_INPUTS.json`
to the same restore tool: it selects 176 retained files, including the patched
u0397 client used by V36. Configure
`delivery-runtime/README.md` with the scientific package, restored task tree,
and CPython 3.12 intake at
`execution-records/p5-v39-consumer-contrast-001/`. Run contrast before adaptive;
the adaptive experiment binds to the newly completed contrast and its actual
metadata inventory. Use fresh output directories and retain interrupted attempts.

Before publication normalization, the archived delivery entry points were validated on the same macOS/Python 3.11.2 host:
six contrast observations, three adaptive observations, and four boundary
observations. The current export requires its own new integrity and execution receipts. This is not a second-machine reproduction claim. The recognized
3.12 consumer failure is an observed failure, not a successful client workflow.
Installed-package and entry-point counts are host dependent; do not require a
new machine to reproduce the original host counts by construction.

## Source comparison and analysis supplements

`delivery-compatible/README.md` documents the V36 source comparison using the
same restored task tree. Four provider/client combinations returned 63 nonempty
mapping entries each on the validation host; all six full-map comparisons were
equal. These counts are observations, not values imposed by the entry point.
The final guard also rejects native extensions and bytecode that could shadow
the retained Python source. Earlier validation attempts are preserved separately.

`delivery-late/README.md` documents two fresh-process runs over 50 explicitly
sealed public inputs. Historical and current modes each reproduce their own
seven-case reference JSON exactly; they use different, separately bound module
versions. This entry uses the retained source slices already in the public tree
and does not require restoring the snapshot archive. Source identities and the
distinction between executed and merely loaded modules are retained in receipts.

`delivery-ledger/README.md` documents regeneration from 702 pinned inputs
(651 package files and 51 restored source files). Its comparison retains and
reports path aliases and generation-time differences separately from scientific
or structural differences. The manual source-pointer and semantic assessments
remain recorded evidence, not newly automated experiments.

Every entry requires new output outside its input roots and keeps failure or
interruption evidence. These are same-host delivery validations of existing
analyses. They do not create new scientific samples, historical causal evidence,
independent annotations, or a second-machine validation.

## Supplementary evidence completion and eligibility sensitivity

[`successor-evidence/V56-evidence-completion/`](successor-evidence/V56-evidence-completion/README.md)
adds source assessments for seven omitted control findings, seven boundary
candidate dispositions, and one common eligibility treatment for the two Nav2
records. Review coverage is 44/44; three supplementary semantic judgments remain
indeterminate. All actual rejections remain counted.

The shared incident's interface eligibility is unconfirmed. The supplementary
reading excludes C3-057 without replacement; 14/93 becomes 14/92, and H1's sample
changes from 40 to 39 while b=2, c=0, and p=0.5 remain unchanged. It does not
resolve the cause or replace the historical primary analysis. The earlier
`successor-evidence/eligibility-sensitivity/` record quantifies that exclusion
before the joint assessment and is retained as historical evidence.

The new entry point runs offline without the full snapshot archive. Its current
result is [EVIDENCE_COMPLETION_RESULTS.json](EVIDENCE_COMPLETION_RESULTS.json),
and [EVIDENCE_COMPLETION_VALIDATION.json](EVIDENCE_COMPLETION_VALIDATION.json)
records exact equality of the scientific result fields against the original
analysis. Input-receipt differences reflect portable paths, publication bytes,
and the additional evidence inventory, not altered scientific outcomes.

## Reading the evidence

Current claims are scoped by the manuscript and
`replication_package/CURRENT_INTERPRETATION.md`. Later evidence retains both
unresolved findings and superseded conditions. Full trigger semantics are not
established merely by resolving a filename or line-range alias. An independent
human-labelled reference has not been added. Supplement directories may contain
archived scripts whose original private execution environment is not supported
by the new delivery entry points; their recorded results remain distinct from
newly rerunnable components. `historical-project/` keeps the separate historical module versions. Publication
normalization must not replace one scientific implementation with a different
same-named implementation; the derivation inventory records representation changes.

`PUBLIC_FILES.json` binds the distributed file inventory.
`THIRD_PARTY_SOURCES.md` records attribution boundaries. Root `LICENSE` retains
the existing repository's license for author-owned material; it does not
relicense the third-party source snapshots or files with their own notices.
