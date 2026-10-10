# Predeclared source replay protocol

Scope: execute unchanged retained CPython importlib.metadata provider source
u0395 (v3.9.0), u0394 (v3.10.0) and unchanged rosidl_cli consumer source
u0396 (62fc0bd), u0397 (7909d0f) under the current Framework Python 3.11.
This is current-host source replay, not original ROS deployment, two independent
clients, CPython 3.9/3.10 runtime deployment, or a new primary evaluation.

Before execution verify each loaded provider/consumer source and every provider
package Python helper against V32 replication_package/snapshots.json pins.
Use existing materialized snapshots in p5-v30-author-reproduction-001; do not
copy trees, extract archives, install dependencies, or access network/ROS/GPU.

Load provider packages with unique importlib spec names and their own retained
helpers. Load both consumer modules unchanged, then explicitly replace only
their importlib_metadata module binding with the selected provider. Record this
binding. Never invoke load_entry_points or EntryPoint.load; execute plugins zero
times. Only invoke public consumer get_entry_points('console_scripts').

Group rule fixed before run: use console_scripts, a standard installed group;
require all four successful cells to return nonempty mappings. If absent, record
the unmet requirement and do not synthesize metadata or change group.
Input is real installed distribution metadata discovered on current sys.path.

Default host PathFinder discovery can yield host 3.11 Distribution objects.
During each cell, retain original import finder behavior through proxies that
hide find_distributions, and register the selected provider MetadataPathFinder
as the sole distribution resolver. Do not patch provider functions or returns.
Use the provider Distribution.discover and verify every returned Distribution
and EntryPoint belongs to the selected provider module; record finder classes,
counts, and ownership. Restore sys.meta_path after each cell.

Run all four provider x consumer cells independently, capture exceptions and
all warnings, and canonicalize returned mapping internally as sorted
{name: {group, value}}. Persist count and SHA256 only (avoid disclosing the host
software list). Compare complete canonical mappings in memory and persist all
six pairwise equality results. Record source/runtime/protocol/script pins,
entry_points result class and get/select availability. No mocked inputs/results.

Faithful interpretation: get remains usable, select is added, warnings may be
observable; distinguish observed output from source expectations. Version major
is unchanged (3.9 to 3.10). Do not claim ECM wins, execute frozen checker, change
14/93 or count independent success controls. Import/execution failure is a
partial outcome; do not undertake complex environment repair. Record host
stdlib dependencies and the limits of same-consumer revision comparison.

This protocol is saved and its SHA256 recorded before source execution.
