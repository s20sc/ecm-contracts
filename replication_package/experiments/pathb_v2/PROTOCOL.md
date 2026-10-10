> Historical protocol, presented with neutral role names and normalized paths. Original freeze timestamps and scientific provisions are retained, but these are not the original frozen bytes. Machine-specific dispatch scripts referenced historically are not included; current integrity bindings belong to this public edition.

# Path B v2.1: evaluation protocol

Status: **FROZEN 2026-09-25** (`FREEZE.json`, copy in `V19-EMSE/audit/`). v2 (2026-09-25 morning) was reviewed by three adversarial readers (`V19-EMSE/audit/2026-09-25-{adj1,gemini,fable}-protocol-review.md`, triage in `2026-09-25-protocol-review-triage.md`); v2.1 is the rewrite, refined through the quarantined six-case pilot of Section 14 (`PILOT.md`) and frozen after it. The freeze manifest hashes this file, every prompt, every script, the dispatch runners, and the source-snapshot ledger. Changes after the freeze go to `DEVIATIONS.md`, never into this file.

This protocol evaluates one finite artifact, the frozen checker of the V18 submission, not the six-dimension framework in general. The authors have seen the V18 cases (C1, C2) and their audit; C1 and C2 are therefore re-analyses. C3 is collected after the freeze and is the only confirmatory corpus. Every C3 case is a previously documented and fixed defect: C3 tests transfer to historical cases the authors and the checker rules never saw, not discovery of unknown failures.

## 1. Claims and reporting commitments (pre-registered)

**H1 (confirmatory).** On the eligible C3 failures, ECM-full detects for the right reason more cases than the definition-and-QoS proxy DQ (Section 8). Test: exact two-sided McNemar on the paired right-reason outcomes, α = 0.05. Effect: b − c with the discordant counts and a Wilson interval on b/(b+c). Minimum practically relevant gain: b − c ≥ 4. If H1 is not rejected, or the sample is smaller than planned, the paper reports the result as a bounded retrospective feasibility study and says so in the abstract.

**Secondary, descriptive.** Everything else: C1 and C2 re-analyses, the documented-silent subset, per-condition detection, binary rejection, controls, precision and F1 on the case-control set, overlap, undetected causes, derivability, strata. No multiplicity control; reported as exploratory.

**Reported regardless of outcome.** V18 numbers with the case-by-case correction ledger; the freeze history of the checker (`experiments/pathb/checker/FROZEN.md`); that v2.1 was designed after seeing V18 results; the C2 ROS 1 / ROS 2 mix; the full eligibility funnel of every corpus; every unassessable case; the keyword-enrichment comparison (Section 3); the checker's coverage and assumption matrix (Section 8); the leakage residuals of Section 6.

## 2. Research questions

- **RQ1 (right-reason detection).** For how many eligible documented integration failures does each method reject the broken composition for the documented cause?
- **RQ2 (value beyond the proxy comparators).** RQ1 restricted to failures whose source documents no diagnostic from existing tooling at build, connection, or activation (documented-silent), and detection timing (pre-deployment vs runtime).
- **RQ3 (over-rejection).** How often does each method reject a composition that works: the resolved composition after the documented fix, and compositions documented as warning-only?
- **RQ4 (coverage).** Which documented failed conditions can the contract fields express, which does no method detect, how do the methods overlap, and how much of each contract can be derived from public artifacts?

## 3. Corpora and retrieval frames

- **C1 (ROBUST, re-analysis).** All 92 bugs that the fault-code crosswalk of `experiments/pathb/extract_robust.py` selected from ROBUST (Timperley et al. 2024), `experiments/pathb/robust_cases.json`, including the three with confidential fixes and the one without a fix commit. The V18 funnel is not reused.
- **C2 (mixed ROS corpus, re-analysis).** The 32 candidates in `experiments/pathb/cases.json`, ignoring V18 `excluded` flags and encodings, labelled by ROS generation from the source. Two candidates that cite one defect (ros2_control#1400) are one candidate.
- **C3 (held-out, confirmatory).** Retrieved after the freeze by `collect_c3.py` (a script, not an agent), which pages through the GitHub search API for closed issues of the repositories in Section 3.1 that (a) closed between 2022-01-01 and 2026-06-30, (b) match at least one search term of Section 3.1 in title or body, and (c) have a timeline event from a merged pull request or a commit that references them. The script writes `candidates/C3_ledger.json` (query, page count, timestamps, every hit with its match terms and fix links, exclusion reasons) and its SHA-256 into `FREEZE.json`. Exclusions: any issue, pull request, or commit that appears in C1 or C2 (by URL or fix SHA); duplicates by fix (same fixing PR/commit) or by defect (S1 finds the same root defect); reopened issues. Order: after retrieval, candidates are grouped by repository and interleaved in seeded random order (seed in `FREEZE.json`), at most 6 eligible failures per repository. S1 processes them in that order until **40 unique eligible failures** are specified or the ledger is exhausted, with a time box of 2026-10-15. The size is fixed before collection and is not extended.
- **C3-neutral (enrichment comparison).** `collect_c3.py` also draws 30 closed, fix-linked issues from the same repositories and window **without** term filtering, in seeded random order. S1 specifies them; nothing further is run on them unless eligible. Reported: the share of ordinary fixed issues that are eligible interface failures, by failed-condition class, next to the same share in the term-selected frame.

The C3 population is "keyword-selected, fix-linked, closed issue reports of the listed repositories in the window", and the paper states it that way.

### 3.1 Repositories and search terms

Repositories: ros2/rclcpp, ros2/rclpy, ros2/rmw_fastrtps, ros2/rmw_cyclonedds, ros2/geometry2, ros-navigation/navigation2, ros-controls/ros2_control, ros-controls/ros2_controllers, moveit/moveit2, ros-perception/image_common, ros-perception/image_transport_plugins, ros-perception/vision_opencv, cra-ros-pkg/robot_localization, mavlink/mavros, RobotWebTools/rosbridge_suite, ros-drivers/usb_cam, ros2/ros2. Redirects are followed and counted once.

Search terms (case-insensitive, title or body): `incompatible`, `QoS`, `frame_id`, `frame`, `units`, `already claimed`, `claimed`, `renamed`, `removed`, `deprecated`, `breaking`, `md5`, `type hash`, `version mismatch`, `does not match`.

## 4. Eligibility

S1 decides each criterion with a quoted reason. E2 is a decision tree; the minimal failure-resolving change is what is judged, not everything the fixing commit touched. **One case is one composition** (two units, one operation). If the source documents failed interactions in more than one composition, S1 specifies the composition whose failure the reporter reports as the problem (the one they reproduced or asked about) and records the others in `notes`; the scorer never chooses. **Within that composition, every documented failed interaction is a failed condition**, whether or not the reporter calls it a bug and including refusals that the runtime enforced (those are `loud_documented`); an internal defect of that composition is recorded as `other`, so that a co-reported internal bug neither excludes nor inflates the case. Defects the fix also addresses in other compositions are not conditions of this case.

- **E1 Specific public instance.** A publicly readable issue, PR, commit, or Q&A thread documents one concrete defect with a reproducer, an error log, or a maintainer's confirmation. Confidential or missing sources fail E1.
- **E2 Interface between two units.** Walk the tree:
  1. Identify the two units whose interaction failed. A unit is a separately deployable component: a ROS node or process, a library, a firmware image, or a package. Two nodes that interact only through ROS interfaces (topics, services, actions, parameters) are separate units even when they ship in one package; a plugin and its host framework are separate units; a node and its own launch file are one unit. For UPGRADE, the provider and the consumer must be separately released or separately built, otherwise there is no version skew.
  2. `internal`: the failure does not depend on any assumption between the two units; it would occur with any correct peer (a crash in one unit's own logic, wrong arithmetic that the same unit consumes, a leak inside one process). A wrong value, frame, unit, component order, name, or timing that **crosses the boundary** is an interface failure even when the resolving edit is inside one unit.
  3. `deployment_wiring`: the minimal resolving change only binds names at deployment (launch or configuration remaps, namespaces, topic or parameter names, device paths) and no unit's declared or referenced interface changes. A provider renaming a parameter that a consumer must follow is an interface change, wherever the consumer's fix lives.
  4. `build`: a build-system, packaging, or dependency-resolution change with no interface change. Rebuilding a consumer because a provider's definition changed is an interface change.
  5. `firmware`: a firmware fault with no declared interface.
  6. Otherwise eligible, with the interface kind: topic, service, action, parameter, message/service/action definition, exclusive resource, library API, wire protocol field.
- **E3 Operation.** PAIR, CONCURRENT, UPGRADE, or SWITCH (Section 5). UPGRADE includes a consumer that references provider elements as they existed at an earlier provider revision (the consumer was written against that revision), with the built-against revision justified from the reference. If the source supports more than one operation, S1 records the one in which the failure was observed and lists the alternatives; the scorer never chooses.
- **E4 Documented effect.** The source documents the defect's effect on the interaction: an observed failure, a warning, or a code-level statement of the mismatch. Cases whose effect was never observed are eligible with outcome class `undocumented` and are reported in the funnel but not in any failure denominator.

Ineligible cases are kept in the funnel with their reason. A 20 % seeded sample of E2 exclusions in every corpus is adjudicated (Section 11); the paper reports an expanded-boundary sensitivity in which adjudicated disagreements are included.

## 5. Case specification (stage S1)

One agent run per packet of cases. Output `specs/<case_id>.json`:

1. Eligibility with evidence (Section 4).
2. **Units** (two): package name, repository URL, revision of each unit in the **broken** composition and in the **resolved** composition as a bare git revision (commit SHA, tag, or branch; `git archive` must resolve it), `pinned` true only for an exact commit or tag, `revision_basis` in prose; a unit the resolution does not change keeps its broken revision. `excerpt` per unit: true when the unit is described from quoted artifacts rather than a repository snapshot. `ros_distro` if stated. For UPGRADE: which unit is the provider, and the provider **revision label** the consumer was built or written against in each composition (a commit, tag, release, or an artifact-section label for excerpt-based cases); the provider at that revision is one of the unit@revision tasks of Section 6.
3. **Operation**: PAIR (an output of one unit feeds an input of the other), CONCURRENT (both active at the same time), UPGRADE (the provider runs at a newer revision than the consumer was built against), SWITCH (one unit stopped, the other started).
4. **Interaction inventory**: every interface element through which the two units interact, as the consumer uses them (topics, services, actions, parameters, command interfaces, classes, functions), up to 10, in canonical form (`topic:<name>`, `service:<name>`, `action:<name>`, `param:<name>`, `msg:<pkg/Type>`, `field:<pkg/Type>.<field>`, `api:<symbol>`, `resource:<token>`), each with the side each unit takes (`provides` / `consumes`). Names only; no attribute values.
5. **Failed conditions** (one or more), each with a class from Section 9, the **implicated elements** (a subset of the inventory), a verbatim quote, and its URL. Classified from primary sources (code, diff, maintainer statements); secondary summaries are not authoritative.
6. **Outcome class**: `failure` (crash, error, refusal, no data, wrong data, wrong motion), `warning_only`, `undocumented` (defect recorded, effect never observed in the source), `unresolved`.
7. **Loudness**: `loud_documented` (the source shows a diagnostic from existing tooling at build, connection, or activation: compiler or import error, ROS 1 md5/type mismatch at connection, ROS 2 incompatible-QoS event, resource-manager claim error, launch error), `silent_documented` (the source shows the failure was observed without such a diagnostic), `unknown`. With the quote and the **detection stage** (build, connect, activate, run).
8. **Resolution**: the minimal resolving change; status `observed` (the source shows the resolved composition working), `recommended`, `none`.
9. `ros_generation` (ROS1 / ROS2 / other), `excerpt_based` (true when any unit has `excerpt` true; then `artifacts/<case_id>.txt` holds the quoted artifacts per excerpt unit and revision, no narrative), `confidence`, `notes`. Resolution status `observed` requires the resolved composition's both units identified by revision; a fix shown working with a different peer is `recommended`.

Items 4 and 5 are separated in the packet builder: S2 receives the inventory; the implicated elements and everything else in the spec are withheld from S2.

## 6. Interface description (stage S2)

S2 describes **one unit at one revision**, with no knowledge of the case, the other unit, the operation, or the outcome. Blinding is structural, not behavioural:

- `materialize.py` (steward script) exports each `unit@revision` with `git archive` into an **isolated workspace** `s2_work/tasks/<task_id>/snapshot/`, with no `.git`, and removes `CHANGELOG*`, `NEWS*`, `RELEASE*`, `.github/`. The workspace holds only that snapshot (or `artifact.txt`), `packet.json`, `definition_hash.py`, and an empty `recon/`. **One S2 run per task**, confined to its workspace, so no run can compare two revisions or two units (the pilot showed a multi-task run diffing snapshots across tasks). Task ids are opaque (`u0001`, …); the mapping to cases lives in `ledger/tasks.json`, outside every workspace. Dispatch order is shuffled (seed in `FREEZE.json`); the steward marks a task `DISPATCHED` before handing it to a run, and a dispatched workspace is never rewritten (the pilot caught a prompt refresh landing in a workspace whose run was in flight). Snapshot SHA-256 values go into the ledger.
- S2's packet carries: `task_id`, package name, `ros_generation`, `ros_distro` if known, the interaction inventory names with the side this unit takes, and the snapshot path. For excerpt-based tasks, an artifact file with only that unit's quoted artifacts: definition texts, configuration or code lines, and verbatim statements of an interface attribute made in the source (for example a reporter's "the publisher uses Best Effort"), each with its URL and nothing else. A unit with no public code and no such statement is `unassessable`. Excerpt-based units form a reported stratum, because S1 selected the excerpts knowing the failure. A QoS value the code chooses at run time (from discovered peers or external configuration) is recorded as null, since a declaration-time check cannot decide it; `declares`/`not_declared` cover provided elements only. Declaration signatures follow fixed templates (topic/service/action/param/field/api lines; a message's signature is its definition id), so that two runs describing two revisions differ only where the code differs; the assembler collapses whitespace before comparing.
- S2 may read: the snapshot; dependency **definition files** (`.msg`, `.srv`, `.action`, `.idl`) fetched as raw files from the dependency's repository at the release tag of the stated distro (URL pattern `raw.githubusercontent.com/<org>/<repo>/<tag>/...`), and nothing else from those repositories; `definition_hash.py`. It may not read issue trackers, pull requests, Q&A sites, search engines, other revisions, other workspaces, or any file outside its own workspace.
- Output `recon/<task_id>.json`: `manifest_version`; `ports` (for each inventory element this unit provides or consumes: `msg_type`, `frame`, `units`, `qos` (ROS 2: values set in code or configuration, else the API default at that version with its citation; ROS 1: null), `rate_hz` / `min_rate_hz` only if set, `definition_id` from `definition_hash.py` as `{algorithm, kind, value}`); `exclusive` claims as the code names them; `declares` (a provider's one-line declaration signature per element it provides: `topic name: Type`, `param name: type`, `field pkg/Type.field: fieldtype`, an API's declaration line); `references` (a consumer's referenced elements in canonical form); `perm_requires`, `perm_grants`, `recovery` only if declared, each with state `present`, `absent` (the code was checked and declares none), or `unknown`; `provenance` keyed by exact path (`ports[0].frame`, `ports[0].qos.reliability`, `exclusive[<token>]`, `declares[<element>]`, `references[<element>]`, `manifest_version`) with `snapshot:<path>:<line>` or `dep:<url>:<line>` and a verbatim excerpt; `confidence`; `notes`; and `blinding_guess`: after writing the description, whether S2 believes this unit-revision is defective (yes / no / cannot tell) and why, without further investigation.
- Values without provenance are null. Placeholder or illustrative values are forbidden. Identifiers are copied verbatim (no normalisation of frames, topics, or symbols).

Residual leakage the paper states: element names come from S1, which read the failure; because every unit is asked about every inventory element (an UPGRADE delta needs the absent side), S2 can see that a unit-revision does not declare a listed element; an LLM may have seen the repository or the issue in training; a snapshot's own source comments may describe the fix. None of these can supply a value, because every value must carry provenance; they can only raise suspicion, which the `blinding_guess` rate measures and the paper reports. Excerpt artifacts carry no log lines, hashes, labels, or fault statements (Section 5).

## 7. Assembly

`assemble.py` builds every composition from S2 descriptions, deterministically:

- **PAIR / CONCURRENT**: for each inventory element, an edge from the provider's `provides` port to the consumer's `consumes` port. Both ports must exist, or the edge is `unassessable_edge`. The checker runs once per edge (`edge.out_role = edge.in_role = element`). Producer/consumer `exclusive` lists and permission fields are attached to every edge.
- **UPGRADE**: `ver_delta.changed_fields` = the elements whose `declares` signature differs between the provider at the built-against revision and at the running revision, or that one revision declares and the other positively does not (`not_declared`, with provenance). An element declared at one revision and undetermined at the other is recorded as `unknown_delta`, not as changed; `ver_delta.consumer_reads` = the consumer's `references`; `semver_old` / `semver_new` = the two manifest versions. In addition a **pair view** per element: producer port = provider@running, consumer port = the consumer's port with `definition_id` and `msg_type` taken from provider@built-against. NT, DI, and DQ read the pair view; ECM reads the UPGRADE encoding; SV reads the versions.
- **SWITCH**: assembled as PAIR for raw output; scored `not_supported` (Section 10).
- Provenance is carried per token into the composition's provenance map (`producer.outputs[i].frame`, `ver_delta.changed_fields[<element>]`, `producer.exclusive[<token>]`, …).
- The composition's `type` must equal the spec's operation; otherwise the case is `unassessable` with reason `assembly_mismatch`.

## 8. Methods

All methods read the assembled encodings. `ECM` is the frozen checker (`contract_checker.py` `e9e0dbbf…`, `canonical.py` `52ac4d84…`) called through a frozen wrapper that (i) passes both semantic versions as null when either is null, so `semver_major` is `unevaluable` rather than fired on an invented `0.0.0`, and (ii) keeps every finding instance (rule, token or port, values). The wrapper is part of the evaluated method and is listed in `FREEZE.json`.

- **NT (nominal type):** rejects an edge when `msg_type` differ and the checker's own promotion table (`_types_compatible`) does not relate them. NT's rejections are a subset of ECM's `type_mismatch` by construction.
- **DI (definition identity):** rejects an edge when both ports carry a `definition_id` of the same algorithm and kind and the values differ. ROS 1 ids are genmsg md5sums (what `roscpp`/`rospy` compare at connection, except the `*` wildcard, which is modelled as "compatible"); ROS 2 ids are a normalised SHA-256 of the definition text and are a **proxy** for the type hash, labelled as such.
- **DQ (definition-and-QoS proxy):** DI plus the DDS request–offer rules for reliability, durability, and deadline (offered `deadline_ms` ≤ requested `deadline_ms`). DQ is not "the middleware": it omits liveliness, lifespan, distribution-specific behaviour, compiler, import, and resource-manager diagnostics. The paper calls it the proxy comparator throughout.
- **SV (declared semver):** flags an UPGRADE whose provider manifest major version increased. Reported as a *declared-breaking* signal only; never a right-reason detection.

DI and DQ are not subsets of ECM. NT and SV are. Coverage and assumption matrix of the checker, reported in the paper: nominal types with a hard-coded promotion table; frames collapsed by `canonical.py` (namespaced frames such as `robot1/base_link` and `robot2/base_link` collapse, so a namespaced frame clash is a checker miss); units compared as unit-token sets; QoS reliability and durability by enum, deadline by publication rate as a proxy for the offered deadline; exclusive resources by exact token intersection; permissions by set inclusion; recovery as a warning only; version by exact token intersection and declared major bump; no lifecycle, timing, or behavioural reasoning.

## 9. Failed-condition classes and rule-instance matching

S1 assigns one or more classes with implicated elements. A finding **matches** a failed condition only under the row below, only on an implicated element (exact canonical string match, lower-cased, leading `/` stripped; a `field:` element also matches its `msg:` parent when the source implicates the definition as a whole), and only when every triggering value of that finding has verified provenance (Section 11).

| Class | Matching finding (method, rule, on the implicated element) |
|---|---|
| `nominal_type_mismatch` | ECM `type_mismatch`; NT |
| `definition_mismatch` (same nominal type, different definition) | DI; DQ (definition); ECM `field_break` whose token is the implicated `msg:` or `field:` element |
| `frame_mismatch` | ECM `frame_mismatch` |
| `unit_mismatch` | ECM `unit_mismatch` |
| `qos_reliability` / `qos_durability` / `qos_deadline` | ECM the rule of the same name; DQ the rule of the same name |
| `rate_shortfall` | ECM `rate_starvation` |
| `exclusive_resource_conflict` | ECM `lock_conflict` whose token is the implicated `resource:` element |
| `permission_missing` | ECM `missing_permission` / `limit_exceeded` on the implicated permission, with the grant set in state `absent` (closed-world evidence) |
| `recovery_conflict` | none (the only recovery rule is a warning) |
| `element_removed_or_renamed` | ECM `field_break` whose token is the implicated element |
| `element_retyped` (declaration changed, element still present) | ECM `field_break` whose token is the implicated element |
| `representation_convention` (component or byte order, handedness, encoding of a value that crosses the boundary) | none |
| `other` | none |

`semver_major` and SV never match. A case with several failed conditions is detected when any one is matched; the count matched is reported. When `definition_mismatch` and `element_retyped` both apply (a renamed field inside a definition), S1 lists both; one match suffices.

## 10. Scoring states

Per case and method, from the assembled broken composition:

- `right_reason`: a matching finding with verified provenance (Section 9).
- `unverified`: a matching finding whose provenance is missing, `wrong`, or `unverifiable`.
- `wrong_reason`: rejection by findings none of which match.
- `accept`: no rejection.
- `not_supported`: SWITCH, or an `other` class with no implemented rule (raw output still recorded).
- `unassessable`: no reconstruction for a required unit, assembly mismatch, or tool failure (Section 13).

Only `right_reason` counts as detection. Binary rejection (`right_reason ∪ unverified ∪ wrong_reason`) is reported beside it. Resolved and warning-only compositions get `reject` / `accept` / `unassessable`; a rejection is a false alarm.

## 11. Adjudication

Adjudicators are adj1 (OpenAI) and withdrawn_google (Gemini), model families different from the Claude S1/S2 runs; a third adjudicator (a second adj1 run with a different seed) resolves disagreements. Independence from shared training data is not claimed.

- **Stage A1 (before any method output is shown):** for every eligible C3 case and every eligible C1/C2 failure: eligibility, failed-condition classes, implicated elements, loudness, resolution status. For a 20 % seeded sample of E2 exclusions per corpus: eligibility.
- **Stage A2 (finding evidence):** for every finding that would produce `right_reason`, and for every false alarm on a control: each triggering value's provenance is checked against the snapshot or dependency file (`verified` / `wrong` / `unverifiable`), and the operation and edge are confirmed. Methods are shown with neutral labels (`M1`…`M5`); the mapping is in the ledger.
- Adjudicators run in workspaces that hold only their packet, the eligibility tree, the specs and artifacts of their cases, and (A2) the assembled compositions and cited task workspaces; a `source_excerpt` must be the text the adjudicator read at the cited location, never the item's own provenance entry. Records are immutable (`adjudication/<who>/<item>.json`). Rules: two agreeing initial records decide; a split goes to the third; an `unverifiable` provenance remains `unverified`. Cohen's κ per decision domain is computed from the two initial records. `adjudicate.py` folds the decisions into `adjudicated/` (spec overrides and provenance verdicts), and `scoring.py` is rerun on it; both the pre- and post-adjudication results are kept.

## 12. Analyses

Per corpus (C1, C2, C3, C3-neutral) and never pooled across C3 and the re-analyses:

- Funnel: candidates → eligible → outcome classes → assessable, with reasons.
- RQ1: right-reason detection per method with Wilson 95 % intervals; per failed-condition class; binary rejection; wrong-reason and unverified counts.
- RQ2: the same on `silent_documented`, with `unknown` as its own stratum; detection stage from the source.
- RQ3: false alarms on observed-fixed (primary), recommended-fixed (sensitivity), and warning-only controls, with Wilson intervals.
- Case-control confusion matrix, precision, recall, F1 per method over failures ∪ observed-fixed ∪ warning-only, with the artificial prevalence stated; no deployment precision is claimed.
- Overlap: per-case hit matrix over all five methods; union and intersection counts; for every method pair, b, c, and the exact two-sided McNemar p; for structurally nested pairs (NT ⊂ ECM, SV ⊂ ECM) the inclusion is stated and no test is reported.
- H1 exactly as pre-registered, in its own record, with the C3 sample size actually reached.
- RQ4: undetected failures by class; derivability: per field, the share of ports with a value, by ROS generation; agreement of S2 values with adjudicated provenance on a seeded 15 % sample of ports including accepted compositions.
- Strata: ROS generation, excerpt-based, unpinned revisions, single-composition cases, adjudication-changed cases, and for UPGRADE cases whether `consumer_built_against` is documented or inferred from the consumer's references.
- Bounds: primary numbers count `unassessable` as not detected (failures) and as not accepted (controls); complete-case numbers are secondary.

Wilson intervals with n = 0 are `null` with reason `no_observations`; JSON is written with `allow_nan=False`.

## 13. Missing data and failure states

Every stage records per item one of `done`, `source_unavailable`, `revision_unresolved`, `tool_failure`, `budget_exhausted`, `evidence_inadequate`. Retry ceiling 2 per item with the same prompt; a third failure is final. `unpinned` revisions are exported at the best bound S1 justified, flagged, and reported as a stratum; no revision is chosen for convenience. No candidate is replaced after the C3 stop. Yield (specified / reconstructed / assessable) is reported per corpus.

## 14. Agents, environment, pilot

- Model and version pinned in `FREEZE.json` for S1, S2, adjudicators; S1 packets of ≤ 8 cases; **S2 one task per run**.
- No browser tools. `gh`, `curl`, `git` (steward only), WebFetch within each stage's source rules.
- Isolation: S1 reads only its packet; S2 reads only its task workspace; adjudicators read specs, recon, snapshots, and the finding instance shown to them. `build_packets.py` and `materialize.py` are steward scripts and may read the V18 pools.
- **Pilot before freeze:** six quarantined C1/C2 cases chosen to cover ROS 1 md5, an UPGRADE with a provider rename, a CONCURRENT resource claim, an excerpt-based case, an unpinned revision, and a deployment-wiring exclusion, run through S1 → materialize → S2 → assemble → scoring → adjudication. Yield, time, and disagreements are recorded in `PILOT.md`; the pilot cases are reported as pilot, not as results.

## 15. Outputs and reproduction

`candidates/`, `specs/`, `artifacts/`, `ledger/`, `s2_work/tasks/<task>/` (packet, prompt, snapshot or artifact, `recon/`), `assembled/`, `scores/`, `adjudication/`, `adjudicated/`, `results.json`, `results_adjudicated.json`, `report/` (tables and figures). `make_report.py` regenerates every table and figure from these files; `freeze.py verify` checks `FREEZE.json` before each stage and fails closed.

## 16. Freeze manifest

`FREEZE.json`: UTC timestamp; SHA-256 of `PROTOCOL.md`, `prompts/*.md`, `collect_c3.py`, `materialize.py`, `build_packets.py`, `assemble.py`, `baselines_v2.py`, `scoring.py`, `adjudicate.py`, `definition_hash.py`, `make_report.py`, `freeze.py`, `test_scoring.py`, `mutation_probe.py`, `../pathb/checker/contract_checker.py`, `../pathb/checker/canonical.py`; the C3 retrieval ledger hash (added when retrieval runs, itself hashed with a timestamp); the shuffle seed; model identifiers. A copy is written to `V19-EMSE/audit/FREEZE-<timestamp>.json`. `DEVIATIONS.md` records every post-freeze change with date, reason, and re-run scope; a change to eligibility, matching, or methods after C3 exposure relabels C3 as exploratory.
