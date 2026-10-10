# Retained compatible-change source replay

All four cells completed under Framework Python 3.11 against real current-host
installed `console_scripts` metadata. Returned mappings are identical in all
six pairwise complete-value comparisons. Only the new provider with the old
consumer emitted `DeprecationWarning: SelectableGroups dict interface is
deprecated. Use select.` No plugin was loaded or executed.

| Retained provider | Real rosidl_cli consumer revision | Returns | Warnings |
|---|---|---:|---:|
| u0395 / CPython v3.9.0 | u0396 / 62fc0bd | 63 | 0 |
| u0395 / CPython v3.9.0 | u0397 / 7909d0f | 63 | 0 |
| u0394 / CPython v3.10.0 | u0396 / 62fc0bd | 63 | 1 DeprecationWarning |
| u0394 / CPython v3.10.0 | u0397 / 7909d0f | 63 | 0 |

Each canonical mapping SHA256 is
`8c73026b91734ac0eec57348ba94cb7da868ff626c7f703eb65a971d52ba53b2`.
Complete `{name: {group, value}}` mappings were compared in memory, then omitted
from persisted output to avoid disclosing the host software inventory. Group
selection was fixed to console_scripts before execution; it was nonempty in
every cell. Warnings used `simplefilter('always')`, an explicit observation
policy that can differ from default deployed warning visibility.

## Source and execution provenance

The protocol was saved and hashed before writing/executing replay.py:
`f56eb6ee782e05148c267c1c17c11cbbc22805029859f9efcba1a87bb4155ba4`.
result.json records the runtime, script pin, actual UTC start/end and all ten
source SHA256 checks against V32 replication_package/snapshots.json. All match:
two provider main files, six u0394 package helper files, and two consumer files.
Loaded module locations also identify the retained helpers actually imported.

Existing source root:
`/historical/runs/p5-v30-author-reproduction-001/work/experiments/pathb_v2/s2_work/tasks`.
Providers and consumers were loaded with unique importlib spec module names
from their existing snapshot paths. No source tree was copied or extracted.
Consumer module bodies remained unchanged; after import their
`importlib_metadata` binding was explicitly switched to the selected retained
provider. Each cell calls the actual `provider.entry_points()` for its API
surface and actual consumer `get_entry_points('console_scripts')` for outputs.
It does not call `load_entry_points()` or `EntryPoint.load()`.

Default provider `Distribution.discover()` did return 149 host
`importlib.metadata.PathDistribution` objects. That default path was not used
for reported consumer cells. During each cell, original sys.meta_path finders
were wrapped to preserve imports while hiding their find_distributions
attribute, and the selected provider MetadataPathFinder was registered as the
sole distribution resolver. The real retained Distribution.discover() then
returned 149 selected-provider PathDistribution instances; returned mappings
contain 63 selected-provider EntryPoint instances. Both ownership checks were
performed in every cell. Original sys.meta_path was restored afterward. No
provider function/body or discovered distribution/entry-point return was
replaced with a fake.

Command:
`/Library/Frameworks/Python.framework/Versions/3.11/bin/python3 -B successor-evidence/V36-compatible-source-replay/replay.py --output /historical/runs/p5-v36-source-replay-output/output-separated-run.json`
returned exit 0 and `{"status": "source_replay_complete", "cells": 4}`.
This exit/result denotes the bounded source replay, not scientific acceptance.

## Provenance-hardened rerun

After independent review requested stronger provenance, the original receipt
was preserved byte-for-byte as first-run-result.json, SHA256
`9e2cfa1d7e25b73717c656b88b6942a82b9dc61b5e813737e119a1dc44d1a3f2`.
The original protocol and its hash remain unchanged. The script now disables
bytecode writes internally (`sys.dont_write_bytecode=True`), records sys.path,
verifies source/hash/device/inode/size/mtime before and after, and returns exit 1
for partial execution or mismatched/changed inputs. Fresh execution of the same
four cells again returned exit 0, the same 63-item mapping/hash and warning
pattern 0/0/1/0. Updated script SHA256 is
`9a7937c58900b517e8080987ec9338c2e52ba2e64f5ca3d833b9e96cbd8d6884`.

The rerun preinventoried 149 discovered distribution directories and 447
candidate metadata paths (entry_points.txt, METADATA, PKG-INFO); 201 files exist.
Their path-identity/content/stat aggregate SHA256 is
`e9c4aeabff6a33a7354b09fc3e3747f4d93f0a26625681eee929fe524478b22f`,
identical before/after. Distribution directory device/inode identities and
sys.path also remained unchanged. These aggregates retain input identity
without publishing the installed-software list.

A read-only Python profile callback observed retained PathDistribution.read_text
calls without modifying provider code or return values. It recorded 1,192
entry_points.txt attempts across the four cells and their API-surface calls:
149 unique paths, 52 actual files and 97 absent files. Their per-path
before/after identity/content/stat aggregate is
`6b9f65721c794969319eb6a1155408e11d4f0a2145c1926e5fc4f18912593a0c`,
unchanged. No METADATA/PKG-INFO read_text call occurred in these entry-point
operations; the 201-file inventory must not be described as 201 files actually
read by the provider. Every observed read path belonged to the preinventory,
and its pre-read fingerprint matched that inventory. All ten source/helper
before/after hashes still match the pins, and their inode/stat fingerprints
remain unchanged. This strengthens reproducibility of these observed inputs;
it does not add deployed-runtime or independent-client evidence.

## Sealed-input-safe output interface

The final replay CLI requires explicit `--output`. Before reading protocol,
source pins, providers or metadata it rejects an existing target, missing
parent, symlink target, or a target resolving inside the P5 project ROOT. Output
uses exclusive new-file creation; there is no default write to HERE/result.json.
Reviewers can execute the retained script in place with a new output path in
their existing external scratch directory, preserving sealed inputs.

The preceding hardened receipt is retained unchanged as
hardened-run-result.json; first-run-result.json is also retained. Fresh execution
using the explicit command above returned exit 0, four 63-entry mappings,
warning counts 0/0/1/0, six true complete-value comparisons, and unchanged source,
sys.path and metadata fingerprints. Its receipt was checked before being
atomically installed as the coordinator-owned result.json. The stored receipt
records its original external output path and exact process command. Final
script SHA256 is
`00d2e1382561c6ab833bc68c7aca685b8ed1510156cbe444821dce8c068ce668`.
The protocol hash/group/pins and computation remain unchanged.

Output preflight tests attempted an in-project nonexistent target and an already
existing external target; both returned exit 1. No in-project output was
created, and the owned result.json SHA remained unchanged through those tests.
The output-interface repair does not add any scientific observations beyond
repeating the same bounded source replay.

## Faithful interpretation and remaining limits

Observed old API result class is dict; new is the retained SelectableGroups.
Both expose get, only new exposes select. Old consumer uses get; real fixed
consumer uses select when available and falls back to get on the old provider.
The equal returned mapping and warning difference support compatibility for
this specific public consumer operation on these real host metadata inputs.
They do not establish every importlib.metadata operation or deployment behavior.

This is **CPython 3.9/3.10 module source running on host Python 3.11**, with host
stdlib dependencies (including import machinery, configparser, pathlib, email,
zipfile and typing) and current sys.path/installed metadata. It is neither a
CPython 3.9/3.10 runtime deployment nor the original rosidl/ROS issue environment.
The two consumers are authentic revisions of one rosidl_cli consumer, not two
independent clients. The old provider revision used by the original consumer
was inferred in the historical spec. Nothing here validates that inference or
identifies the reporter's exact Python patch version. Plugin functionality and
original pipeline completion were not tested.

No frozen checker was executed and no primary scores, 14/93 cause credit,
independent success-control count, A2 coverage, or H1 changed. Version major is
unchanged (3.9 to 3.10). Read-only inspection corrects an earlier investigation
statement: frozen checker `_ver` at
V32-EMSE/replication_package/experiments/pathb/checker/contract_checker.py:165–175
has independent `semver_major` and changed_fields intersection consumer_reads
`field_break` branches; it does not require a major increase AND the
intersection. Therefore unchanged major alone cannot predict its result.
This replay did not construct declarations or demonstrate ECM superiority.

The result provides a real compatible substantive provider source change with
observable warning exposure depending on authentic consumer revision. The
strict missing study requirement remains: independent affected/unaffected
clients, faithful reviewed declarations, and specified actual runtime/deployment
outcomes under the same upgrade. Do not relabel this as closure of that gate.
