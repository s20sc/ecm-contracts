# Current-host independent workflow boundary study

This is a new, source-selected, post-outcome boundary study. It is not part of
the frozen primary corpus, an independent human reference, a prospective
accuracy estimate, or original ROS deployment. Do not change primary denominators
or count either workflow as a newly labelled primary control.

## Inputs and predictions before workflow execution

Use retained, unmodified CPython v3.9.0 (u0395) and v3.10.0 (u0394)
importlib.metadata source, including the latter's Python helpers; verify every
provider source against the V32 snapshot manifest. Run on the installed Framework
Python 3.11, not the historical interpreters. Both have major version 3; retain
the exact declared 3.9.0 -> 3.10.0 version change in checker input.

Prepare and hash the protocol, script, provider inputs, rosidl_cli u0396 module,
host pip/pytest/pluggy source inventories, frozen checker/assembler/scoring inputs,
and the two existing test files before running any workflow. Save the two
declaration-surface contracts and the frozen-checker predictions first.

The surface is explicitly limited to the two top-level API functions
`entry_points` and `distributions`. Derive argument and return declarations from
Python AST source, not from the later runtime outcome; preserve source ranges.
The retained rosidl_cli calls the first, and pip's retained importlib backend
calls the second. Record those direct-call source ranges. This is an illustrative
two-function declaration surface, not a complete extraction of every transitive
API. No ROS message type, QoS, behavioural contract, missing major version, or
synthetic success label may be fabricated. Also report the unchanged original
rosidl_cli reconstruction's prediction separately; do not replace that encoding.

## Four isolated cells

Fresh subprocesses for each provider x workflow cell, with a 90-second timeout:

1. `rosidl_cli.load_entry_points('console_scripts', specs=['pytest'], strict=True)`:
   discover from real installed metadata, verify the selected provider's
   EntryPoint class, execute its unchanged `EntryPoint.load`, then invoke the
   loaded `pytest:console_main` callable with the two existing frozen scoring and
   adjudication test modules. Disable third-party pytest plugin autoload and
   cache writing; create each temporary parent before execution. Require exactly
   81 collected, 81 passed and exit 0. This is complete for this specified console
   workflow, not for ROS extensions, factory instances or ROS nodes.
2. Execute installed pip's actual `list --format=json --disable-pip-version-check`
   command through its unchanged CLI. Require its importlib metadata backend,
   nonempty successfully parsed output and exit 0. Disable network and config
   inputs using isolated mode and PIP_NO_INDEX. No install or package mutation.

Rebind the standard importlib.metadata module to the selected retained provider
inside each fresh child before importing workflow modules, and disclose this
binding. Register the provider's MetadataPathFinder as the sole distribution
resolver, retaining import-only proxies for the host finders. Do not patch
provider API implementations, returned objects, consumer source or checker rules.
The discovery-only host bridge delegates `find_distributions` to the unchanged
retained MetadataPathFinder and returns None for Python module `find_spec`.
The historical MetadataPathFinder class must not be placed directly in the host
import finder chain: its inherited `find_module` is an unbound instance method.
Verify discovered Distribution and EntryPoint ownership. Record actual calls to
provider functions and `EntryPoint.load`, not just module import success.

Hash the real installed distribution metadata before and after execution;
persist counts and digests rather than the host package inventory. For pip,
compare complete canonical package/name/version output between provider cells
in memory and persist its count and SHA256. Capture all warnings, exceptions,
exit codes and test summaries. Verify source pins again after each cell and at
aggregate closure. Do not repair failed environments or change endpoints/groups
to obtain a successful run; retain failures and incomplete cells.

## Interpretation

Distinguish the two independent metadata clients (rosidl_cli and pip) from the
downstream pytest workload. This comparison can establish only observed behavior
at these two declared endpoints on this host. It cannot prove all upgrades
compatible, differential failure recognition, a consumer-aware detection gain,
full boundary reproduction, or human annotation validity. A checker rejection
paired with a successful workflow is a scoped false alarm for that endpoint,
not grounds to modify frozen primary results. The version rule remains unchanged.
