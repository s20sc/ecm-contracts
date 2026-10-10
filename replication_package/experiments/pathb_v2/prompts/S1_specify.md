# Stage S1: case specification

You specify documented robotics integration defects for an empirical study, from public sources only. You do not see, and must not look for, any checker, contract encoding, scoring rule, or earlier analysis of these cases.

Working directory: `{PB2}`. Your packet is `{INPUT}`: cases with a `case_id`, a `corpus`, and source pointers (bug title and description, issue URL, fix commits, or a source URL; some fixes are marked `confidential` or absent). Write one file per case to `specs/<case_id>.json` and, for excerpt-based cases, `artifacts/<case_id>.txt`. Write nothing else.

## Read the source

The issue or thread with all comments, the fixing commit or PR diff, and the code around the change at the parent revision when needed. Follow linked PRs and commits. Quote verbatim.

## Eligibility (all four must hold)

One case is one composition: two units and one operation. If the source documents failed interactions in more than one composition (for example two controllers that cannot be co-activated, and a service whose response is wrong), specify the composition whose failure the reporter reports as the problem (the one they reproduced or asked about) and record the other compositions in `notes`. Within that composition, every documented failed interaction is a failed condition, whether or not the reporter calls it a bug and including refusals the runtime enforced (mark those `loud_documented`); an internal defect of that composition is a condition of class `other`. Defects that the fix also addresses in other compositions are not conditions of this case; mention them in `notes`.

- **E1** A publicly readable issue, PR, commit, or Q&A thread documents one concrete defect with a reproducer, an error log, or a maintainer's confirmation. A confidential or absent fix does not by itself fail E1 if the public report is concrete.
- **E2** Walk this tree and record the step at which you stop:
  1. Name the two **units** whose interaction failed. A unit is a separately deployable component: a ROS node or process, a library, a firmware image, or a package. Two nodes that interact only through ROS interfaces (topics, services, actions, parameters) are separate units even when they ship in one package; a plugin and its host framework are separate units; a node and its own launch file are one unit. For UPGRADE the provider and consumer must be separately released or separately built.
  2. The failure does not depend on any assumption between the two units and would occur with any correct peer (a crash in one unit's own logic, wrong arithmetic the same unit consumes, a leak inside one process) → ineligible `internal`. A wrong value, frame, unit, component order, name, or timing that **crosses the boundary** is an interface failure even when the resolving edit is inside one unit.
  3. Minimal resolving change only binds names at deployment (launch/config remaps, namespaces, topic or parameter names, device paths), no unit's declared or referenced interface changed → ineligible `deployment_wiring`. (A provider renaming a parameter that a consumer must follow is an interface change, even if the consumer's fix is in YAML.)
  4. Build-system, packaging, or dependency-resolution change only, no interface change → ineligible `build`. (Rebuilding a consumer because a provider's definition changed is an interface change.)
  5. Firmware fault with no declared interface → ineligible `firmware`.
  6. Otherwise eligible; record the interface kind (topic, service, action, parameter, definition, exclusive resource, library API, wire protocol field).
- **E3** The failing operation is one of PAIR (an output of one unit feeds an input of the other), CONCURRENT (both active at the same time), UPGRADE (the provider runs at a newer revision than the consumer was built or written against; a consumer that still references provider elements as they existed at an earlier provider revision is an UPGRADE, with that earlier revision as `consumer_built_against`), SWITCH (one unit stopped, the other started). If the source supports more than one, record the one in which the failure was observed and list the others in `notes`.
- **E4** The source documents the defect's effect on the interaction: an observed failure, a warning, or a code-level statement of the mismatch (a maintainer's commit or a dataset record that names the mismatch counts). If the effect was never observed, the case is still eligible with outcome class `undocumented`.

## For an eligible case, record

- **Units**: package name, repository URL, and the revision in the **broken** and in the **resolved** composition. `broken_rev` and `resolved_rev` are bare git revisions that `git archive <rev>` resolves in that repository (a commit SHA, a tag, or a branch name, and nothing else in the string); `pinned` is true only for an exact commit or tag; `revision_basis` holds the reasoning and bounds in prose (for example "the reporter names only the distro; the humble branch head on the reproduction date was 945d64ed"). A unit that the resolution does not change keeps its broken revision as `resolved_rev`. `excerpt` is true for a unit described from the artifact file (no public repository, or its interface artifact exists only as text quoted in the source) and false for a unit described from its repository snapshot. `ros_distro` if stated. For UPGRADE: which unit is the provider, and in `consumer_built_against` the **provider's revision label** that the consumer was built or written against in each composition (a commit, tag, release, or, for excerpt-based cases, a label such as `md5:<sum>` or `as-reported-2021-09` that also names a section of the artifact file). It is a provider revision, not a description. `basis` says how you know it: `documented` when the source states the revision the consumer was built or run against; `inferred` when you derived it from the consumer's references matching that revision's declarations (for example a script that still names a topic the provider renamed). An inferred built-against revision makes every other provider change between the two revisions visible to the checkers as well, so the two kinds are analysed separately.
- **Operation**.
- **Interaction inventory**: every interface element through which the two units interact, as the consumer uses them, up to 10, in canonical form: `topic:<name>`, `service:<name>`, `action:<name>`, `param:<name>`, `msg:<pkg/Type>`, `field:<pkg/Type>.<field>`, `api:<symbol>`, `resource:<token>`. For each, the side each unit takes: `provides` or `consumes`. Names only: no types, frames, units, QoS values, versions, or which attribute differs.
- **Failed conditions**: one or more, each with a `class` from: `nominal_type_mismatch`, `definition_mismatch` (same nominal type, different definition), `frame_mismatch`, `unit_mismatch`, `qos_reliability`, `qos_durability`, `qos_deadline`, `rate_shortfall`, `exclusive_resource_conflict`, `permission_missing`, `recovery_conflict`, `element_removed_or_renamed`, `element_retyped` (declaration changed, element still present), `representation_convention` (component or byte order, handedness, or encoding of a value crossing the boundary), `other`; the **implicated elements** (a subset of the inventory); a verbatim quote and its URL. Classify from primary sources (code, diff, maintainer statements); if a secondary summary disagrees, follow the primary source and say so. A renamed field inside a definition is both `definition_mismatch` and `element_retyped`; list both.
- **Outcome class**: `failure` (crash, error, refusal, no data, wrong data, wrong motion), `warning_only` (a warning while the composition keeps working), `undocumented` (defect recorded, effect never observed in the source), `unresolved`.
- **Loudness**: `loud_documented` (the source shows a diagnostic from existing tooling at build, connection, or activation: compiler or import error, ROS 1 md5sum/type mismatch at connection, ROS 2 incompatible-QoS event, resource-manager claim error, launch error), `silent_documented` (the source shows the failure observed without such a diagnostic), `unknown`; with the quote and `detection_stage` (build / connect / activate / run / unknown).
- **Resolution**: the minimal resolving change; status `observed` (the source shows the resolved composition working, with both of its units identified by revision), `recommended` (proposed or accepted but not shown working in this composition; a fix shown working with a different client or peer is `recommended`, with that observation as evidence), `none`.
- `ros_generation` (ROS1 / ROS2 / other), `excerpt_based` (true when any unit has `excerpt` true), `confidence`, `notes`.
- Excerpt-based units: when any unit has `excerpt` true, write `artifacts/<case_id>.txt` with, for each such unit and revision, sections `[[<unit name>@<revision>]]` (the same unit names and revision strings as in `units`; use a descriptive revision label such as `as-reported-2021-09` when there is no commit) containing only quoted artifacts for that unit and revision: definition texts (`.msg`/`.srv`/`.action` bodies), configuration or code lines, and verbatim statements of an interface attribute made in the source (for example `"the publisher uses Best Effort" -- <url>`). Nothing else: no log or error lines, no md5sums or hashes (S2 computes them from the text), no bracketed descriptions or labels, no statement of what went wrong or which side is at fault. Each section starts with the `[[...]]` line and then the artifact text verbatim. A connection header or similar runtime record is quoted with its hash fields removed: the `message_definition` it carries is written out as a plain definition body in the section of the **provider at the built-against revision**, and the remaining fields that state the consumer's interface (topic, type, caller id) stay in the consumer's section as its evidence. A unit with neither code nor such a statement gets an empty section; units with `excerpt` false are described from their repository snapshots and get no section. For an UPGRADE, also write a section for the **provider at the built-against revision** (`[[<provider>@<consumer_built_against label>]]`) holding the provider's definitions or declarations as they were at that revision; the consumer's sections hold only what the consumer's own code or configuration states.

## Output schema

```json
{
  "case_id": "...", "corpus": "C1|C2|C3|C3N", "source_refs": ["..."],
  "eligibility": {"E1": {"pass": true, "evidence": "..."},
                  "E2": {"pass": true, "stop_step": 6, "reason_code": null, "units_identified": ["...", "..."], "interface_kind": "...", "evidence": "..."},
                  "E3": {"pass": true, "evidence": "..."}, "E4": {"pass": true, "evidence": "..."}},
  "eligible": true, "ineligible_reason": null,
  "units": [{"name": "...", "role": "provider|consumer|peer", "repo": "https://...", "broken_rev": "<bare git revision>", "resolved_rev": "<bare git revision>", "pinned": true, "revision_basis": "...", "excerpt": false, "ros_distro": null}],
  "operation": "PAIR|CONCURRENT|UPGRADE|SWITCH",
  "consumer_built_against": {"broken": null, "resolved": null, "basis": "documented|inferred|null"},
  "inventory": [{"element": "topic:/image_raw", "sides": {"<unit name>": "provides", "<other unit name>": "consumes"}}],
  "failed_conditions": [{"class": "...", "implicated_elements": ["..."], "quote": "...", "url": "..."}],
  "outcome_class": "failure|warning_only|undocumented|unresolved",
  "loudness": "loud_documented|silent_documented|unknown", "loudness_evidence": "...", "detection_stage": "...",
  "resolution": {"summary": "...", "status": "observed|recommended|none", "evidence": "..."},
  "ros_generation": "ROS1|ROS2|other", "excerpt_based": false,
  "confidence": "high|medium|low", "notes": "..."
}
```

For an ineligible case fill `case_id`, `corpus`, `source_refs`, `eligibility`, `eligible: false`, `ineligible_reason`; other fields null.

## Rules

- No browser tools. Use `gh`, `curl`, WebFetch, or `git clone` into `/private/tmp` (delete when done). ROS Answers blocks many fetchers: try its static archive with `curl`, the Wayback Machine via `curl`, or the Stack Exchange API for migrated questions.
- Read only your packet and the files you write. Do not open anything under `experiments/pathb/`, `s2_work/`, `recon/`, `scores/`, the manuscript, or `V19-EMSE/`.
- Quote verbatim. Do not invent revisions, quotes, or URLs. Unknown values are null. If a source is unreachable after two attempts, set `status: source_unavailable` at the top level and stop that case.
- Reply with a table: case_id | eligible (reason) | operation | outcome | loudness | classes | resolution | confidence.
