# Stage S2: interface description of one unit at one revision

You describe the interface that a robot software package declares in its source code at one revision. Each task is independent. You are not told what the package is paired with, whether anything is wrong, or why this revision was chosen. Record what the code declares; do not guess.

Working directory: `{S2WORK}`, a workspace holding exactly one task; you may not read anything outside it. `packet.json` there gives `task_id`, `package`, `ros_generation`, `ros_distro` (may be null), `snapshot` (the directory with the package source at the revision), `elements` (interface element names, each with the side this package takes: `provides` or `consumes`), or for an excerpt-based task `artifact_file` instead of a snapshot. Write `recon/<task_id>.json` in the workspace. Write nothing else.

## Sources allowed

- The snapshot directory. It has no version history; do not try to obtain any, and do not compare it with anything outside the workspace.
- Dependency **definition files** (`.msg`, `.srv`, `.action`, `.idl`) that the snapshot's definitions or code depend on, fetched as raw files from the dependency's repository at the release tag of `ros_distro` (URL pattern `https://raw.githubusercontent.com/<org>/<repo>/<tag>/...`). Nothing else from those repositories.
- `python3 definition_hash.py ros1 <pkg/Type> <dir> [<dir>...]` and `python3 definition_hash.py sha256 <file>` in this directory.
- For excerpt-based tasks, only the artifact file.

Not allowed: issue trackers, pull requests, Q&A sites, search engines, changelogs, other revisions of this or any package, other workspaces, and any path outside `{S2WORK}`.

## What to record

```json
{
  "task_id": "...", "package": "...",
  "manifest_version": "x.y.z or null",
  "ports": [
    {"element": "<name from the packet>", "side": "provides|consumes",
     "msg_type": "pkg/Type or null", "frame": "<as written in code> | per_message | none | null", "units": "... or null",
     "qos": {"reliability": "reliable|best_effort|null", "durability": "volatile|transient_local|null", "deadline_ms": null},
     "rate_hz": null, "min_rate_hz": null,
     "definition_id": {"algorithm": "ros1_md5|sha256_normalised", "kind": "msg|srv|action|idl", "value": "..."}}
  ],
  "exclusive": ["<resource tokens claimed exclusively, as the code names them>"],
  "declares": {"<element>": "<one-line declaration signature>"},
  "not_declared": ["<packet elements this package positively does not declare at this revision>"],
  "references": ["<canonical names of other packages' elements this code references>"],
  "perm_requires": {"state": "present|absent|unknown", "values": []},
  "perm_grants": {"state": "present|absent|unknown", "values": []},
  "recovery": {"state": "present|absent|unknown", "value": null},
  "provenance": {"<field path>": "snapshot:<path>:<line> | <verbatim excerpt>"},
  "blinding_guess": {"defective": "yes|no|cannot_tell", "why": "..."},
  "confidence": "high|medium|low", "notes": "..."
}
```

- `ports`: one entry per packet element this package publishes, offers, subscribes to, or calls. `msg_type` fully qualified at this revision. `frame`: exactly as the code declares or hard-codes it for that element; `per_message` if taken from each message header at run time; `none` if the data has no spatial meaning; null if undeterminable. `units`: as stated in the definition or code, or a REP-103 convention the code explicitly relies on; else null. QoS: values set in code or configuration; if none, the documented default of that API at that version, with the citation in provenance; null for ROS 1. A QoS value the code fixes, or the API's documented default when the code sets none, is static and is recorded even when the topic name or type arrives at run time. Only a QoS value the code selects from the discovered peers' profiles, or from configuration that is not in the snapshot, is not statically determined: record null for that value and describe the selection rule in `notes`. `rate_hz` / `min_rate_hz` only if set. `definition_id`: the tool's output; null if the definition is not available.
- `exclusive`: resources claimed exclusively in code or configuration (hardware command interfaces, exclusive device handles), verbatim.
- `declares` and `not_declared` concern only the elements this package **provides**; an element it consumes goes into `references` when the code names it, and into neither list when the name is supplied at run time (say so in `notes`). `declares`: one entry per provided element, in exactly these forms (they are compared textually across revisions described by different runs, so use the templates verbatim, single spaces, no trailing text):
  - `topic <name>: <pkg/Type>`; `service <name>: <pkg/Type>`; `action <name>: <pkg/Type>`;
  - `param <name>: <type>` (the declared or default type, for example `double`, `string`, `bool`, `int`; `unknown` if not stated);
  - `msg <pkg/Type>: <definition_id value>` (the hash from `definition_hash.py`, not the text);
  - `field <pkg/Type>.<field>: <fieldtype>` (the field's type as written in the definition, for example `float32`, `std_msgs/String`, `float64[9]`);
  - `api <symbol>: <declaration line verbatim, whitespace collapsed>`.
  An element the package positively does not declare at this revision (you searched the snapshot, or the artifact is a complete definition body and the field is not in it) goes into `not_declared`, with a provenance entry `not_declared[<element>]` saying what you searched or which artifact lines are complete. An element you could not determine either way is in neither list; say so in `notes`.
- Field elements (`field:...`) get a port whose `msg_type` is the parent message type; the field's own type goes only into `declares`.
- `references` (elements this package consumes): canonical names (`topic:<name>`, `service:<name>`, `param:<name>`, `msg:<pkg/Type>`, `field:<pkg/Type>.<field>`, `api:<symbol>`) that the code references, including any it still references under an old name.
- Permissions and recovery: `present` with values if declared; `absent` if you checked the code and configuration and found none; `unknown` if you could not check.
- Every non-null value has a provenance entry keyed by its exact path (`ports[0].frame`, `ports[0].qos.reliability`, `ports[0].definition_id`, `exclusive[<token>]`, `declares[<element>]`, `not_declared[<element>]`, `references[<element>]`, `manifest_version`).
- Never write placeholder or illustrative values. Unknown is null. Copy identifiers verbatim (no normalisation of frames, topics, or symbols).
- `blinding_guess`: after writing everything else, say whether you believe this package at this revision is defective in one of the listed elements, and why, **without** further investigation.

## Rules

- No browser tools. Do not invent lines, hashes, or versions.
- If the snapshot lacks the package or the elements cannot be found after a careful search, write the file with `status: evidence_inadequate` and what you searched.
- Reply with one line: task_id | ports set | declares | not_declared | references | null fields | blinding_guess | confidence.
