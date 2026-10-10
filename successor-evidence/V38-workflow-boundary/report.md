# Independent metadata-client workflow boundary

Status: four specified workflow endpoints completed; submission readiness unchanged.
This is a source-selected post-outcome supplement, not a new primary cohort.

| Metadata client and specified endpoint | CPython 3.9 source baseline | CPython 3.10 source after upgrade | Frozen upgrade prediction |
|---|---|---|---|
| rosidl_cli 62fc0bd, discover/load pytest console entry then execute scoring and adjudication tests | exit 0; 81 passed | exit 0; 81 passed; two deprecation warnings | reject |
| pip 25.0.1, `list --format=json` through the importlib backend | exit 0; 149 packages | exit 0; same complete 149-package output | accept |

The checker prediction is for the **3.9.0 -> 3.10.0 upgrade pair**. Baseline
runtime cells are not additional predictions, false alarms, or accuracy samples.
The clients are independent metadata call paths (rosidl_cli and pip); pytest is
the downstream workload of rosidl_cli, not a third independent metadata client.

## What was executed and verified

Framework Python 3.11.2 loaded unchanged retained CPython sources with their own
helpers. Standard-module rebinding and a distribution-only host bridge were
explicit, process-local harness choices. Both clients used real installed
metadata. The rosidl EntryPoint.load call occurred once per cell; its returned
pytest console callable executed the two unchanged frozen test modules. Each
pip cell used 149 actual retained-provider PathDistribution objects; complete
normalized output SHA256 was
`dcf20ef83c73412ecb3ca3c7551fe963dc2baafe7cc50041fb326335c48d68b2`.

Prepared source/environment inputs: 540. The preparation and outcomes bind
SHA256 `3db04cf4a16ddcfb7fb205f2eb7dd010df9ac95a9ce7eb87956c83236efd2312`.
Source and metadata inputs matched at closure. V38's entire 6,695-file seal
verified before and after, with manifest SHA256
`522599b8c7ac6d45d70fc3f128c6ee2d66cb8832728b0542c35bb1b5c018367d`.

Each pytest stdout also reports 5,252 ResourceWarnings from unclosed files
in the frozen code/tests. These remain in the raw receipts. Successful execution
is not a warning-free run. The new-provider rosidl cell records two
DeprecationWarnings because discovery verification and actual loading each call
the metadata API. This is consistent with the known warning-only case, not
evidence that all historical behavior was fault-free.

## Interpretation

Only the top-level declarations `entry_points` and `distributions` were newly
derived from AST source before execution. The first changes from a no-argument
declaration to `**params` with a return annotation; the second retains its
signature. Direct source calls place only the former in rosidl_cli's references
and only the latter in pip's references for this surface. Frozen assembler and
checker code, with the actual 3.9.0 and 3.10.0 versions, predict rosidl reject and
pip accept. No ROS message, QoS value, missing version, or outcome-derived
signature was fabricated. The original frozen rosidl reconstruction and its
three rejection findings are separately retained in prepared.json.

The rosidl after-upgrade endpoint still completes, so its rejection is a local
false alarm **under the predeclared endpoint-success criterion that permits
warnings**. This does not relabel the historical warning-only failure, prove a
warning-free upgrade, or alter the primary 14/93 and 12/93 counts. This example
shows both consumer-referenced blocking and its compatibility limitation. It
does not distinguish a genuinely failing client from a genuinely unaffected one,
measure detection benefit, or exhaust the provider's transitive API surface.
The complete original ROS deployment and independent human reference remain open.

## Execution trail and review

Raw evidence is retained at
`/historical/runs/p5-v38-workflow-boundary-006/`.
The compact receipt.json pins those files without duplicating snapshots,
software lists, or large test stdout. Earlier preparation/harness attempts are
retained in sibling `-001` through `-005` directories and summarized in receipt.
The atime guard and finder-bridge defects were reproduced by independent
tooling probes before repair; two filesystem regression tests pass. Their
failures were not attributed to consumer compatibility.

An independent code reviewer inspected the code and final raw receipts, then
rehash-verified all 540 prepared inputs and 6,695 sealed files with zero
mismatches. That review endorses this scoped supplement, not a scientific
Accept, a human-labelled reference, or SOP audit completion.
