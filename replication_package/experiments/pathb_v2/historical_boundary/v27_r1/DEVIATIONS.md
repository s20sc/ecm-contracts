# Deviations from the frozen protocol

Frozen 2026-09-25 09:18 UTC (`FREEZE.json`). Every change to PROTOCOL.md, a prompt, or a script after that point is recorded here with date, reason, and re-run scope by `python3 freeze.py amend <file> --reason ... --scope ...`, which also updates the file's hash in `FREEZE.json` under `amendments` so that `freeze.py verify` keeps failing closed on any unlogged change. PROTOCOL.md itself is left unchanged. A change to eligibility, matching, or methods after C3 exposure relabels C3 as exploratory (Section 16).

## 2026-09-26 — `collect_c3.py`

- **Change:** The first post-freeze C3 retrieval completed every search query and then aborted on one issue's timeline endpoint (gh: Not Found, HTTP 404) before the ledger was saved. The script now retries transient gh failures once, records a per-hit timeline_error instead of aborting (such a hit is not fix-linked and is excluded with that reason), and saves the ledger after the search phase and incrementally during enrichment. No eligibility, matching, or method change.
- **Re-run scope:** No C3 data existed (the ledger was never written); the search is re-run from scratch.
- **Hash:** `773c2461087f` → `71aca64b40f7` (FREEZE.json amendment 1)

## 2026-09-26 — `freeze.py`

- **Change:** Added the amend command that records post-freeze changes to a frozen file (old/new hash, time, reason, scope) in FREEZE.json and DEVIATIONS.md, so fail-closed verification keeps working with an audit trail.
- **Re-run scope:** Tooling only; no stage re-run.
- **Hash:** `42be83e71fd8` → `bf87ef3caef6` (FREEZE.json amendment 2)

## 2026-09-26 — `collect_c3.py`

- **Change:** The second post-freeze retrieval died in the search phase on a TLS handshake timeout (one retry was not enough). gh calls now retry three times with backoff; the search saves progress after every query and resumes from it; a query that still fails is recorded in failed_queries and order refuses an incomplete ledger. Retrieval frame, terms, window, repositories, ordering, and exclusions unchanged.
- **Re-run scope:** No C3 data existed; search restarted (resumable).
- **Hash:** `71aca64b40f7` → `ec851f5f8582` (FREEZE.json amendment 3)

## 2026-09-26 — `collect_c3.py`

- **Change:** Root cause of every earlier timeline failure found: the timeline call passed -f fields without -X GET, so gh api sent a POST and GitHub answered 404 for every issue (verified on one hit: POST 404, GET 15 events). The call now uses -X GET; hits whose enrichment errored are retried on resume; a query that succeeds on retry clears its failed_queries record. The frozen script had never been exercised against the live API before the freeze, which is the steward's omission. Retrieval frame unchanged.
- **Re-run scope:** Search results (253 queries, 1799 hits) are kept from the resumable partial ledger; the 2 failed queries are retried and all hits are enriched again.
- **Hash:** `ec851f5f8582` → `aa1b4ac5d76d` (FREEZE.json amendment 4)

## 2026-09-26 — `collect_c3.py`

- **Change:** A hit whose timeline call failed in an earlier run and succeeded on retry kept its stale timeline_error key, inflating the 'timeline unavailable' count; the key is now removed on success and normalised on load. Bookkeeping only.
- **Re-run scope:** Enrichment resumed from the incremental ledger; no result changes.
- **Hash:** `aa1b4ac5d76d` → `7faa5b926271` (FREEZE.json amendment 5)

## 2026-09-27 — `freeze.py`

- **Change:** Added amend-model, which records a post-freeze change of the model pinned for a stage role (old, new, time, reason, scope) in FREEZE.json and DEVIATIONS.md.
- **Re-run scope:** Tooling only.
- **Hash:** `bf87ef3caef6` → `00362f27bd84` (FREEZE.json amendment 6)

## 2026-09-27 — model for S1

- **Change:** `claude-fable-5-1` → `claude-fable-5-1 for cases specified up to 2026-09-26; claude-opus-5-5 thereafter`. The account's weekly quota for claude-fable-5-1 was exhausted on 2026-09-27 with 44 of 117 C1/C2 cases (and all of C3) still to specify; the revision deadline does not allow waiting for the reset. Each spec records its model; the model is reported as a stratum; and a seeded random sample of 10 fable-specified C1 cases is re-specified independently by claude-opus-5-5 in reliability/s1_opus/ to measure inter-model agreement on eligibility, classes, implicated elements, operation, loudness, and resolution.
- **Re-run scope:** Remaining S1 packets C1_09, C1_10, C2_00-03 and all of C3/C3N run on claude-opus-5-5; the 73 fable specs are kept; inter-model sample added.

## 2026-09-27 — model for S2

- **Change:** `claude-fable-5-1` → `claude-opus-5-5`. Same quota exhaustion. No corpus S2 task had been run (only the quarantined pilot, on fable), so every corpus S2 description is produced by one model.
- **Re-run scope:** All corpus S2 tasks.

## 2026-09-27 — `scoring.py`

- **Change:** Three pre-registered rules were stated in PROTOCOL.md but not implemented in the frozen scorer: (1) the six quarantined pilot cases (Section 14) were read from specs/ and would have entered the C1/C2 results; they are now excluded and listed as pilot_excluded. (2) The C3 stop rule (Section 3: in the frozen order, eligible failures until 40, at most 6 per repository) was not applied; c3_selection walks the order, skips unspecified candidates only in capped repositories, halts at the first other gap, and H1 counts only selected cases; specs processed beyond the stop point are funnel-only. (3) The strata for built-against basis (Section 12) and the S1 model (2026-09-27 amendment) are added. No C3 case had been specified when this change was made; eligibility, matching, and methods are unchanged.
- **Re-run scope:** No results existed for C1/C2/C3; the pilot results are unaffected (pilot cases were never reported as results).
- **Hash:** `29169e5c950e` → `2784a82322a6` (FREEZE.json amendment 7)

## 2026-09-27 — `test_scoring.py`

- **Change:** Tests for pilot exclusion, the C3 stop rule (cap, stop, gap, capped-repo skip), selected-only H1, and the new strata.
- **Re-run scope:** Tooling only.
- **Hash:** `d9e298ff55e6` → `05ce7e9b4450` (FREEZE.json amendment 8)

## 2026-09-27 — `mutation_probe.py`

- **Change:** Four mutations for the stop rule and pilot exclusion (all killed; 35 in total).
- **Re-run scope:** Tooling only.
- **Hash:** `6c9bae008d93` → `1481fb7a770a` (FREEZE.json amendment 9)

## 2026-09-27 — `materialize.py`

- **Change:** The C2 materialize run crashed on a dangling symbolic link in a navigation2 snapshot (sha_dir opened every file). sha_dir now hashes a symbolic link by its target string and never follows it, which also removes a latent host dependence (a link pointing outside the snapshot would have hashed host files). New ledger entries record sha_method; every existing snapshot hash is recomputed with the new method (old value kept as snapshot_sha256_v1). Snapshot contents are unchanged.
- **Re-run scope:** Hashes of all 201 existing snapshots recomputed; the crashed C2 run (7 cases) re-run; no S2 run had used any hash.
- **Hash:** `d45b7f27612a` → `19cf3a9b7aec` (FREEZE.json amendment 10)

## 2026-09-27 — `test_scoring.py`

- **Change:** Test for symlink-safe snapshot hashing (dangling link, link outside the snapshot).
- **Re-run scope:** Tooling only.
- **Hash:** `05ce7e9b4450` → `d27aa77c4e26` (FREEZE.json amendment 11)

## 2026-09-27 — `mutation_probe.py`

- **Change:** Mutation that follows existing symlinks (killed).
- **Re-run scope:** Tooling only.
- **Hash:** `1481fb7a770a` → `70cb15c2288d` (FREEZE.json amendment 12)

## 2026-09-27 — `adjudicate.py`

- **Change:** Before any corpus A1 packet was generated: (1) items() left pilot cases in; the six quarantined pilot cases were adjudicated in the pilot and are never results (PROTOCOL Section 14), so A1/A2 items now skip them, and the pilot's adjudication records, packets, logs, prompts and fold outputs were moved to pilot/adjudication/ so fold() cannot mix them into corpus results. (2) Cases whose eligibility another S1 judgment on the same or a same-mechanism source contradicted (RUNLOG) are added from ledger/a1_extra.json on top of the seeded 20 % exclusion sample, which the additions do not change; they carry sample=added and their reasons stay out of the packet. (3) Eligible C3-neutral cases are adjudicated like C3, so the enrichment comparison compares two equally reviewed eligible shares. (4) fold() folded loudness, class and resolution for excluded cases, whose fields are empty by construction; two records agreeing with an empty field entered the kappa and inflated agreement. Excluded cases are now folded on eligibility only.
- **Re-run scope:** adjudication item set and fold; no S1, S2, scoring or method change
- **Hash:** `54ff4ff16250` → `2da8885c4b18` (FREEZE.json amendment 13)

## 2026-09-27 — `test_scoring.py`

- **Change:** Two tests for the adjudicate.py amendment of the same date (pilot exclusion, additions added once without changing the seeded sample, C3-neutral inclusion, excluded cases folded on eligibility only); five mutants of the amendment each fail an assertion.
- **Re-run scope:** tests only
- **Hash:** `d27aa77c4e26` → `50164dbe2fcc` (FREEZE.json amendment 14)

## 2026-09-27 — `adjudicate.py`

- **Change:** The corpus A1 run of 2026-09-27 16:30 failed for every adj1 packet: adjudication/work is a symlink to local disk (moved there 13:04 the same day), and adj1's sandbox refuses a writable root reached through a symlink, so adj1 read nothing and wrote nothing. The prompt and the runners now name the resolved directory. No record was produced by the failed runs.
- **Re-run scope:** adj1 A1 re-run for all 15 packets; no item, fold or scoring change
- **Hash:** `2da8885c4b18` → `29dba0e74aa1` (FREEZE.json amendment 15)

## 2026-09-27 — `development-runner-02.sh`

- **Change:** The corpus A1 run of 2026-09-27 16:30 failed for every adj1 packet: adjudication/work is a symlink to local disk (moved there 13:04 the same day), and adj1's sandbox refuses a writable root reached through a symlink, so adj1 read nothing and wrote nothing. The prompt and the runners now name the resolved directory. No record was produced by the failed runs.
- **Re-run scope:** as adjudicate.py amendment of the same time
- **Hash:** `d160f8b722e0` → `a6527936ccd2` (FREEZE.json amendment 16)

## 2026-09-27 — `development-runner-01.sh`

- **Change:** Same path resolution as development-runner-02.sh, for uniformity (withdrawn_google was not affected).
- **Re-run scope:** none
- **Hash:** `d04c7704e2dc` → `54493576d37e` (FREEZE.json amendment 17)

## 2026-09-27 — ADJ2 (withdrawn_google) corpus A1 records withdrawn; adjudicator calibration added

- **What happened:** withdrawn_google returned all 141 A1 records in 1–6 minutes per 10-item packet (the pilot took 6 minutes for 5 items). Every verdict was `agree`: 141/141 eligibility, 141/141 loudness, 141/141 resolution, 135/135 failed-condition classes, and no missed condition. It agreed with both sides of a contradiction on one issue: C3N-001 (ros-navigation/navigation2#5386, ineligible `internal`) and C3-057 (the same issue, eligible failure). At most one of those two specifications can be right, so agreeing with both shows that the records confirm the specification rather than check it.
- **Change:** the 141 records and their logs are kept in `adjudication/withdrawn/withdrawn_google_A1_2026-09-27/` and are not folded. Before any adjudicator's corpus records are counted, it adjudicates a calibration packet (`calibrate.py`): 12 copies of real A1 specifications, 8 carrying one planted error each (class ×2, loudness ×2, resolution ×2, eligibility ×1, implicated elements ×1) and 4 unchanged, under neutral ids, with the key outside every workspace. The key, packet and script were hashed into FREEZE.json before any calibration record came back. Candidates: adj1 (ADJ1), withdrawn_google, and three provider-backed model candidates (calibration_kimi = Kimi K3, adj2 = GLM-5.2, adj3 = DeepSeek V4 Pro); the provider-runner prompts carry one added line telling the agent to use absolute paths, because its shell does not start in the workspace. The replacement ADJ2 is chosen from the candidates by planted-error sensitivity, recorded with `freeze.py` before it runs the corpus packets, and every candidate's calibration result is reported, including the one chosen, whose estimate is optimistic because it was selected on the same packet.
- **Re-run scope:** ADJ2 A1 for all 141 items with the chosen adjudicator; adj1 A1 unaffected apart from the path fix above.

## 2026-09-27 — `freeze.py`

- **Change:** add-ledger keyed records by basename, so recording calibration/v2/key.json would have replaced the record of calibration/key.json, and re-recording a changed file erased its earlier hash. Records are now keyed by the path relative to pathb_v2, and a re-recorded path moves its earlier record to ledger_history. Existing records keep their basename keys; verify() checks by the stored path, so it is unaffected.
- **Re-run scope:** ledger bookkeeping only
- **Hash:** `00362f27bd84` → `807753005490` (FREEZE.json amendment 18)

## 2026-09-27 — `test_scoring.py`

- **Change:** Test for the freeze.py add-ledger change (two same-basename files stay two records; a re-recorded file keeps its earlier hash in ledger_history); the basename-key mutant fails an assertion and the no-history mutant fails in the test body.
- **Re-run scope:** tests only
- **Hash:** `50164dbe2fcc` → `748529c6ee1f` (FREEZE.json amendment 19)

## 2026-09-27 — planned sensitivity analysis: QoS values derived from library defaults (declared before any C3 scoring)

- **Observation (S2 corpus runs, 30 of 34 tier-1 tasks returned):** where the code passes no QoS argument, or names a profile (`rclcpp::SensorDataQoS()`, rclpy service defaults, tf2_ros broadcaster defaults), some S2 runs fill `qos.reliability` / `qos.durability` from the library's documented default, with provenance "snapshot call site; documented default" (u0015, u0280, u0281, u0322, u0323, u0342, u0358, u0378 and C1 pilot-era u0014-type cases), while others record null in the same situation (u0297, u0343, u0344). S2_PROMPT.md allows only the snapshot and dependency definition files, so a default read from memory is outside the allowed sources; the prompt did not anticipate named profiles.
- **Effect:** the two treatments feed identical fields to ECM and DQ, so they do not favour either side of H1, but they change which QoS findings can fire at all, and A2 checks only values behind findings.
- **Decision (no S2 re-run, no value changed):** the primary analysis uses the recon values as written, with A2 verdicts on every triggering value. A sensitivity analysis recomputes H1 and the per-method tables with every QoS value set to null whose provenance excerpt does not contain a literal token for that value in the snapshot (`RMW_QOS_POLICY_RELIABILITY_*`, `RMW_QOS_POLICY_DURABILITY_*`, `ReliabilityPolicy.*`, `DurabilityPolicy.*`, `.reliable()`, `.best_effort()`, `.transient_local()`, `.durability_volatile()`, or the artifact line for excerpt cases). The rule is written here before any C3 composition is assembled or scored; its implementation in scoring.py will be a logged amendment with tests.

## 2026-09-27 — `ledger/adjudicators.json`

- **Change:** ADJ2 withdrawn_google withdrawn (all-agree corpus records; 0/8 on calibration v2). Chosen by planted-error sensitivity, as declared before calibration: ADJ2 = adj2 (GLM-5.2), the highest non-adj1 candidate; ADJ3 = adj3 (DeepSeek V4 Pro), the next, instead of adj1_repeat, so that a split between ADJ1 and ADJ2 is not decided by a second run of the ADJ1 model. calibration v1 (planted errors partly visible inside the copy) and v2 (planted errors consistent with the copy, visible only against the sources), 8 plants each: adj1 8/8 + 8/8, adj2 8/8 + 7/8, adj3 7/8 + 5/8, calibration_kimi 6/8 + 5/8, withdrawn_google 6/8 + 0/8; eligibility plants in v2: adj1 2/2, adj2 2/2, others 0/2. adj3's v2 eligibility misses mean a split it decides leans towards keeping the specification; reported.
- **Re-run scope:** ADJ2 A1 for all 141 items; ADJ3 on splits; A2 with the same roles
- **Hash:** `6283dac83cab` → `9fe6d2dee241` (FREEZE.json amendment 20)

## 2026-09-27 — model for ADJ2

- **Change:** `withdrawn_google/gemini-3.1-pro-high (Google model CLI)` → `adj2/GLM-5.2 (provider zai/glm-5.2, thinking high)`. calibration v1 (planted errors partly visible inside the copy) and v2 (planted errors consistent with the copy, visible only against the sources), 8 plants each: adj1 8/8 + 8/8, adj2 8/8 + 7/8, adj3 7/8 + 5/8, calibration_kimi 6/8 + 5/8, withdrawn_google 6/8 + 0/8; eligibility plants in v2: adj1 2/2, adj2 2/2, others 0/2.
- **Re-run scope:** ADJ2 corpus A1 and A2

## 2026-09-27 — model for ADJ3

- **Change:** `adj1_repeat/gpt-6-astra (second independent run, reasoning high)` → `adj3/DeepSeek V4 Pro (provider deepseek/deepseek-v4-pro, thinking high)`. Next-highest non-adj1 candidate on calibration; keeps three model families. calibration v1 (planted errors partly visible inside the copy) and v2 (planted errors consistent with the copy, visible only against the sources), 8 plants each: adj1 8/8 + 8/8, adj2 8/8 + 7/8, adj3 7/8 + 5/8, calibration_kimi 6/8 + 5/8, withdrawn_google 6/8 + 0/8; eligibility plants in v2: adj1 2/2, adj2 2/2, others 0/2.
- **Re-run scope:** ADJ3 on splits

## 2026-09-27 — excerpt artifacts carry source URLs and reporter statements; excerpt-exclusion sensitivity declared (before any C3 scoring)

- **Observation:** PROTOCOL.md §5 says excerpt artifacts carry no log lines, hashes, labels, or fault statements. A scan on 2026-09-27 found source URLs (issue, pull request, Q&A) in 21 of the 30 case artifacts and in 24 excerpt task workspaces; most lines are verbatim reporter or maintainer quotes in the form `"quote" -- URL`, and some of them describe the fault or the fix (for example B-Beh-02's changelog sentence about automatic subscriber QoS). S1 wrote the artifacts in its provenance style; neither the pilot check (which looked at C3-048 only) nor `check_specs.py` tested for this. S2 agents report not opening the URLs, but the text itself can tell them what went wrong, so S2 on excerpt-based units was not blind.
- **Effect:** none on H1's matchable cases (all 11 are snapshot-based). Excerpt-based cases enter the per-method tables, the C1/C2 re-analyses, and the blinding-guess rate.
- **Decision (no re-run, no artifact edited):** every per-method and per-corpus table is also reported with excerpt-based cases excluded, next to the primary table; the paper states the leak, the counts above, and the blinding-guess rate split by excerpt versus snapshot tasks. Declared here before any C3 composition is assembled or scored.

## 2026-09-27 — `assemble.py`

- **Change:** Declared before any C3 composition is assembled or scored. The UPGRADE delta compared the two provider records by whitespace-collapsed string, but the two records come from two independent S2 runs: across 35 same-element declaration pairs in the returned recons, differences included macros and labels (formatting), another line of the same declaration (#define vs #ifndef of an include guard), another representation of the same definition (a MAVLink C++ struct vs its XML), a C implementation vs a Python signature (numpy), and C parameter names. Such a transcription difference on an implicated element would give ECM a field_break right_reason that A2 cannot catch, because both excerpts are real. Fix, in two layers: (1) assemble.py compares a canonical form (label, visibility/attribute macros and punctuation spacing dropped; types, parameters, defaults and values kept); (2) A2 question 4 asks both adjudicators whether each changed field differs in substance or only in transcription, and fold() demotes the path unless the final verdict is substantive (missing answer = unverifiable; a pending split does not count).
- **Re-run scope:** assembly of every UPGRADE composition (none assembled yet for the corpora)
- **Hash:** `e2edbeff5108` → `77fec55d0f28` (FREEZE.json amendment 21)

## 2026-09-27 — `adjudicate.py`

- **Change:** Declared before any C3 composition is assembled or scored. The UPGRADE delta compared the two provider records by whitespace-collapsed string, but the two records come from two independent S2 runs: across 35 same-element declaration pairs in the returned recons, differences included macros and labels (formatting), another line of the same declaration (#define vs #ifndef of an include guard), another representation of the same definition (a MAVLink C++ struct vs its XML), a C implementation vs a Python signature (numpy), and C parameter names. Such a transcription difference on an implicated element would give ECM a field_break right_reason that A2 cannot catch, because both excerpts are real. Fix, in two layers: (1) assemble.py compares a canonical form (label, visibility/attribute macros and punctuation spacing dropped; types, parameters, defaults and values kept); (2) A2 question 4 asks both adjudicators whether each changed field differs in substance or only in transcription, and fold() demotes the path unless the final verdict is substantive (missing answer = unverifiable; a pending split does not count).
- **Re-run scope:** A2 fold; A1 fold unchanged
- **Hash:** `29dba0e74aa1` → `b13b4c824c9f` (FREEZE.json amendment 22)

## 2026-09-27 — `prompts/A_adjudicate.md`

- **Change:** Declared before any C3 composition is assembled or scored. The UPGRADE delta compared the two provider records by whitespace-collapsed string, but the two records come from two independent S2 runs: across 35 same-element declaration pairs in the returned recons, differences included macros and labels (formatting), another line of the same declaration (#define vs #ifndef of an include guard), another representation of the same definition (a MAVLink C++ struct vs its XML), a C implementation vs a Python signature (numpy), and C parameter names. Such a transcription difference on an implicated element would give ECM a field_break right_reason that A2 cannot catch, because both excerpts are real. Fix, in two layers: (1) assemble.py compares a canonical form (label, visibility/attribute macros and punctuation spacing dropped; types, parameters, defaults and values kept); (2) A2 question 4 asks both adjudicators whether each changed field differs in substance or only in transcription, and fold() demotes the path unless the final verdict is substantive (missing answer = unverifiable; a pending split does not count). The A1 section is unchanged, so A1 records written with the earlier prompt (adj1, adj2 A1_00-A1_07) and with this one are comparable.
- **Re-run scope:** A2 prompts
- **Hash:** `c07c62e70318` → `a4476aa0af49` (FREEZE.json amendment 23)

## 2026-09-27 — `test_scoring.py`

- **Change:** Three tests for the canonical signature, the macro-only vs type-change delta, and the substance fold (both transcription_only demotes, both substantive keeps, split pending and missing answers demote); five mutants each fail an assertion.
- **Re-run scope:** tests only
- **Hash:** `748529c6ee1f` → `76b653bef29a` (FREEZE.json amendment 24)

## 2026-09-27 — `assemble.py`

- **Change:** Declared before any C3 composition is assembled or scored. The frozen checker and the NT baseline compare msg_type by exact string (plus the promotion table); S2 runs spell one type as pkg/Type (274 ports) or pkg/kind/Type (24 ports, e.g. rcl_interfaces/srv/GetParameters, sensor_msgs/msg/Image, nav2_msgs/action/FollowPath). A spelling difference in one composition would make a type_mismatch for ECM and NT (not for DQ, which does not read type names): a spurious right_reason on a nominal-type condition, or a spurious false alarm on a control. assemble.port_of now writes one spelling per type (pkg/Type; C++ :: form converted); a different package or type name still differs. The checker is not modified.
- **Re-run scope:** assembly of every composition (none assembled yet for the corpora)
- **Hash:** `77fec55d0f28` → `ee6c03adec33` (FREEZE.json amendment 25)

## 2026-09-27 — `test_scoring.py`

- **Change:** Test for canonical_type and port_of (spellings of one type join; different types stay different); removing the call in port_of and restricting the kinds to msg each fail an assertion.
- **Re-run scope:** tests only
- **Hash:** `76b653bef29a` → `3523e15cc775` (FREEZE.json amendment 26)

## 2026-09-27 — `scoring.py`

- **Change:** Implements the two sensitivity analyses declared in DEVIATIONS.md before any C3 scoring (QoS values without a literal token; excerpt-based cases excluded) and the S2 blinding-guess split by task kind declared with the second. main() now builds rows through build_rows(), and each sensitivity analysis reruns that path with a composition transform. On a temporary full assembly of all 133 eligible cases, primary results and per-case scores are byte-identical to the previous version; the check printed equality only, with method outcomes suppressed. The QoS rule (qos_literal.py, new) reads the lines each value's provenance cites in that unit's own task workspace, never the provenance text, because S2 wrote the library default it looked up into its explanation. Tokens per value are the C macro, the rclcpp enum and builder, the rclpy enum, and a YAML or keyword assignment; in an excerpt artifact the value's words count. Named profiles (SensorDataQoS(), qos_profile_parameters) are not literal, as declared; a variant that keeps them is reported and labelled as not declared in advance. On the current recons, 45 value instances across compositions would be nulled: 15 named profile, 21 no token, 9 no readable location. The 9 are 5 distinct values, one of them u0359 citing rclpy/node.py for rclpy/rclpy/node.py.
- **Re-run scope:** Scoring only; no S2 or A1 record changes. 48 tests pass. 10 mutants each fail an assertion; M8 was written wrongly twice (a syntax error, then a no-op) before the corrected mutant was killed.
- **Hash:** `2784a82322a6` → `6fd7d09863ea` (FREEZE.json amendment 27)

## 2026-09-27 — `assemble.py`

- **Change:** Each assembled unit now records the S2 task behind each side (tasks: producer/consumer; built/running/consumer for UPGRADE; producer/consumer/built for a pair view), so the declared QoS-literal sensitivity can read the lines a value cites in the right workspace. Metadata only; no method reads it. For all 133 eligible cases the assembly is identical to the previous version apart from this field; all 611 units carry a task id on every side. See the scoring.py entry of the same date.
- **Re-run scope:** No re-run; assembly output otherwise unchanged.
- **Hash:** `ee6c03adec33` → `f2951d354070` (FREEZE.json amendment 28)

## 2026-09-27 — `test_scoring.py`

- **Change:** Four tests for the declared sensitivity analyses: the literal check reads cited lines and not the explanation, stays inside the unit's snapshot, and treats artifact prose separately; nulling works per side, copies the unit, and removes a DQ detection; assembled units name their tasks; main reports both sensitivity blocks, the excerpt exclusion and the state changes. See the scoring.py entry of the same date.
- **Re-run scope:** Tests only.
- **Hash:** `3523e15cc775` → `267b47bd94f6` (FREEZE.json amendment 29)

## 2026-09-27 — `mutation_probe.py`

- **Change:** The probe counted any non-zero test exit as a kill, so a mutant that fails with a syntax, import, or collection error looked killed whatever the tests check. A kill now requires a test to fail on an assertion; any other failure is reported as ERROR, and the run stops if the unmodified baseline fails. The base copy keeps symbolic links instead of following them (adjudication/work points to local disk). The anchor of asm.signature_not_normalised was updated to the canonical_sig code, since the 2026-09-27 assemble amendment removed the old line, and the code hash now also covers qos_literal.py and freeze.py. 17 mutants were added for the amendments of 2026-09-27: canonical signature and type spelling, the unit task ids, the A2 substance fold, A1 pilot exclusion, freeze ledger keys, the QoS-literal rule, and both sensitivity blocks. The classifier was checked on synthetic outputs (a syntax error, an import error, a mixed failure and error, an assertion failure). The previous report is kept as MUTATIONS_2026-09-27_pre-assertion-rule.md.
- **Re-run scope:** Tooling only. 53 of 53 mutants killed on an assertion; 0 survived, 0 error, 0 not applied (MUTATIONS.md).
- **Hash:** `70cb15c2288d` → `c7c49db0cc0e` (FREEZE.json amendment 30)

## 2026-09-27 — `adjudicate.py`

- **Change:** items() deleted every packet before regenerating, so building the A2 packets after scoring would also rewrite the A1 packets; if the A1 item set had changed in the meantime (a spec added, an extra case), items would move between packets under existing A1 records. items() now compares the regenerated A1 packets with the existing ones and refuses, deleting nothing, if they differ while any adjudicator record exists for an existing A1 item. Unchanged inputs regenerate identical A1 packets, and A2 packets are built as before.
- **Re-run scope:** No record or packet changed; guard only.
- **Hash:** `b13b4c824c9f` → `90d20ae6c90e` (FREEZE.json amendment 31)

## 2026-09-27 — `test_scoring.py`

- **Change:** Test for the adjudicate.py guard of the same date: an unchanged rerun keeps the A1 packets identical; a new case after records exist raises and deletes nothing.
- **Re-run scope:** Tests only; 49 pass.
- **Hash:** `267b47bd94f6` → `fbe85881c376` (FREEZE.json amendment 32)

## 2026-09-27 — `mutation_probe.py`

- **Change:** Two mutants for the A1 guard. The kill rule now also accepts a test whose pytest.raises did not raise (an explicit expectation of the test, reported by pytest as 'Failed: DID NOT RAISE'); an exception from the code under test still counts as ERROR. Checked on synthetic outputs.
- **Re-run scope:** Tooling only. 55 of 55 mutants killed; 0 survived, 0 error, 0 not applied (MUTATIONS.md).
- **Hash:** `c7c49db0cc0e` → `25a78045b47b` (FREEZE.json amendment 33)

## 2026-09-27 — `scoring.py`

- **Change:** In adjudicated mode, main() computed the C3 selection on the adjudicated specifications. If adjudication excluded a selected case, the walk continued past the S1 stop point and selected the next eligible failure, which is a replacement that PROTOCOL.md Section 13 forbids ('No candidate is replaced after the C3 stop'). The selection is now always computed on the specifications as S1 wrote them. Adjudication can exclude a selected case, which shrinks H1's sample and is reported. A case that adjudication makes eligible enters the descriptive C3 tables but not H1, because only a seeded sample of exclusions and a listed set of contradicted cases were adjudicated, and adding them would make H1's sample depend on that sampling. results now lists both kinds under c3_adjudication_effect. Found by reading the code before fold or scoring had run on corpus data.
- **Re-run scope:** No results existed. Tests: selection, H1 size, the effect record, no pull-in past the stop.
- **Hash:** `6fd7d09863ea` → `5441ebade31f` (FREEZE.json amendment 34)

## 2026-09-27 — `adjudicate.py`

- **Change:** fold() added a missed condition only when both adjudicators named its class, and silently dropped one named by a single adjudicator: no split, no third adjudicator. That is inconsistent with the rule for every other A1 domain, where a disagreement between the first two records goes to the third. A missed condition named by one record is now a split. It is added when the third adjudicator, who does not see the proposal, names the same class in its own record; two records naming it still add it directly. Proposal counts (both, ADJ1 only, ADJ2 only) are written to kappa.json. Found by reading fold() before it had run on corpus data. The interim adj1 and adj2 records already show ADJ1-only proposals on 7 items, which A3 will now decide instead of dropping.
- **Re-run scope:** fold and A3 packet only; no record changed.
- **Hash:** `90d20ae6c90e` → `322179d80dd0` (FREEZE.json amendment 35)

## 2026-09-27 — `test_scoring.py`

- **Change:** Tests for the scoring.py and adjudicate.py amendments of the same time: the adjudicated H1 keeps the S1 selection and never replaces; a missed condition named by one record goes to the third, is added only if the third names it, and is added directly when both first records name it.
- **Re-run scope:** Tests only; 51 pass.
- **Hash:** `fbe85881c376` → `6d56436b1811` (FREEZE.json amendment 36)

## 2026-09-27 — `mutation_probe.py`

- **Change:** Three mutants for those amendments: selection on adjudicated specs, a single-record missed condition dropped, the third adjudicator's answer ignored.
- **Re-run scope:** Tooling only. 58 of 58 mutants killed; 0 survived, 0 error, 0 not applied.
- **Hash:** `25a78045b47b` → `ac9879c5d3c3` (FREEZE.json amendment 37)

## 2026-09-27 — `adjudicate.py`

- **Change:** third() wrote every split item into one packet A3_00. With an expected 40 or so A1 splits, one agent run would exceed the runner's one-hour timeout; adj2 needed 13-38 minutes per ten items. third() now writes packets of ten (A3_00, A3_01, ...) in split order and removes stale A3 packets first. The items and their content are unchanged.
- **Re-run scope:** Packaging only.
- **Hash:** `322179d80dd0` → `784cc033fb3e` (FREEZE.json amendment 38)

## 2026-09-27 — `test_scoring.py`

- **Change:** Test for third(): packets of ten, every split item exactly once in order, stale packets removed.
- **Re-run scope:** Tests only; 52 pass.
- **Hash:** `6d56436b1811` → `7d643bbe521d` (FREEZE.json amendment 39)

## 2026-09-27 — `mutation_probe.py`

- **Change:** Two mutants for third(): a single packet, stale packets kept.
- **Re-run scope:** Tooling only. 60 of 60 mutants killed.
- **Hash:** `ac9879c5d3c3` → `2cd53fcc014c` (FREEZE.json amendment 40)

## 2026-09-27 — adjudicator agreement pattern; ADJ1-only sensitivity declared (before any C3 scoring, written 20:07 local)

- **Observation (A1 records only; no method output exists):** ADJ1 (GPT-6-astra) disagreed with at least one field of 46 of 141 specifications or named a missed condition. ADJ2 (GLM-5.2) did so for 1 of the 131 records returned so far, and the withdrawn Gemini run for 0 of 141. GLM-5.2 quotes the source for every eligibility verdict, and its one disagreement is a detailed check against the code, so it reads the sources and defers on judgement calls rather than confirming blindly; its calibration (8/8, 7/8) shows that it catches clear planted errors. Under the declared roles almost every ADJ1 disagreement therefore becomes a split that ADJ3 (DeepSeek V4 Pro) decides, and ADJ3 missed both eligibility plants of calibration v2.
- **Correction to the entry "ADJ2 (withdrawn_google) corpus A1 records withdrawn":** GPT-6-astra also agreed with both specifications of ros-navigation/navigation2#5386 (C3N-001 ineligible `internal`, following the reporter's diagnosis; C3-057 eligible with one condition of class `other`, following the fix author's explanation). The pair therefore does not separate the adjudicators. The withdrawal of Gemini rests on its all-agree records (0 of 141, against 46 for GPT-6-astra) and on its calibration (0 of 8 errors that are consistent with the copy). The pair is reported as an unresolved S1 test-retest disagreement. C3-057's only condition is class `other`, which no method can match, so the case cannot enter H1's discordant counts.
- **Decision (roles unchanged; no adjudicator is replaced after its corpus records were seen):** the primary analysis uses the declared roles. Declared here, before any C3 composition is scored: a sensitivity analysis in which ADJ1 decides every A1 and A2 item alone (`adjudicate.py fold --adj1-only` → `adjudicated_adj1only/`; `scoring.py --adj1-only`). Together with the unadjudicated scores (specifications as written), it brackets the effect of adjudication. The A2 item set is the union of the findings under both adjudicated variants, so that every finding that can count in either is adjudicated by the first two adjudicators.
- **Defect fixed at the same time:** unadjudicated and adjudicated scoring runs wrote their per-case scores to one directory, and items() read the A2 findings from it, so the A2 item set depended on which run came last. Each mode now writes its own scores directory and results file, and A2 item ids are derived from the evidence rather than from a position in one score file.

## 2026-09-27 — `adjudicate.py`

- **Change:** ADJ1-only fold (--adj1-only, output adjudicated_adj1only/, no kappa) for the sensitivity declared in DEVIATIONS.md today before any C3 scoring; A2 items read findings from scores_adjudicated/ and scores_adjudicated_adj1only/ and take ids derived from the evidence key (a position in one score file could give two different findings one id). See the DEVIATIONS entry 'adjudicator agreement pattern'.
- **Re-run scope:** No record changed; fold not yet run on corpus data.
- **Hash:** `784cc033fb3e` → `680542c9e623` (FREEZE.json amendment 41)

## 2026-09-27 — `scoring.py`

- **Change:** Each mode writes its own per-case scores and results (scores/ and results.json unadjudicated; scores_<dir>/ and results_<dir>.json adjudicated, dir = adjudicated or adjudicated_adj1only); before, both modes wrote scores/, so one overwrote the other and the A2 item set depended on run order. --adj1-only selects the ADJ1-only fold. See the DEVIATIONS entry of the same time.
- **Re-run scope:** No results existed.
- **Hash:** `5441ebade31f` → `deb59a1193eb` (FREEZE.json amendment 42)

## 2026-09-27 — `test_scoring.py`

- **Change:** Tests: the ADJ1-only fold decides alone in its own directory and leaves the primary fold untouched; scoring modes write separate scores and results; A2 items union both variants with evidence-derived ids that stay stable and unique.
- **Re-run scope:** Tests only; 54 pass.
- **Hash:** `7d643bbe521d` → `81b9124631c1` (FREEZE.json amendment 43)

## 2026-09-27 — `mutation_probe.py`

- **Change:** Six mutants for the ADJ1-only fold, the A2 union and ids, and per-mode score directories.
- **Re-run scope:** Tooling only. 66 of 66 mutants killed.
- **Hash:** `2cd53fcc014c` → `74b70bbc540d` (FREEZE.json amendment 44)

## 2026-09-27 — same-repository stratum declared (before any C3 scoring, written 20:28 local)

- **Observation:** when both units of a case are packages of one git repository (tf2_py and tf2_ros in geometry2, mavros and mavros_msgs, kobuki packages), each unit's S2 snapshot also holds the other unit at the same revision. Several S2 runs used the peer's code for their blinding guess (u0148, u0149, u0150). Eligible cases with both units in one repository: C1 15, C2 4, C3 1 (C3-115), C3-neutral 1.
- **Decision:** reported as a stratum (`same_repository`) with per-method detection next to the other strata, and the blinding-guess rate for those tasks. No re-run, and no value changed.

## 2026-09-27 — `scoring.py`

- **Change:** Stratum same_repository (both units from one git repository, so each S2 snapshot holds the peer at the same revision), declared in DEVIATIONS.md before any C3 scoring.
- **Re-run scope:** Strata only.
- **Hash:** `deb59a1193eb` → `52e24a4e0412` (FREEZE.json amendment 45)

## 2026-09-27 — `test_scoring.py`

- **Change:** Test for the same_repository stratum, including units without a repository.
- **Re-run scope:** Tests only; 55 pass.
- **Hash:** `81b9124631c1` → `7b84e9eeacc5` (FREEZE.json amendment 46)

## 2026-09-27 — `mutation_probe.py`

- **Change:** Two mutants for same_repository; the first survived until a both-excerpt case was added to the test.
- **Re-run scope:** Tooling only. 68 of 68 mutants killed.
- **Hash:** `74b70bbc540d` → `4af90b3b295a` (FREEZE.json amendment 47)

## 2026-09-29 — frame-literal sensitivity declared, and the cited-line reader extended (before any full scoring run, written 09:33 local)

- **Observation:** during S2 tier 4, a scan of every returned record's port frames found values that are descriptions, not frames written in code: u0005 records "ENU (ROS input) -> FCU frame via UAS::transform_frame_enu_ned" on four ports. The frozen checker's canon_frame() maps any string to a frame token by substring ("enu" and "ned" anywhere, else the first word), so a description can produce a frame, and a frame mismatch, that no line of the unit names. The S2 rule asks for the frame "exactly as the code declares or hard-codes it". Some long values are genuine literals: "From real-time state data" is the frame_id ur_driver hard-codes (driver.py:333), and u0362's MAVLink frame descriptions are the header comments it cites, so a rule based on spaces would be wrong.
- **Declaration:** a sensitivity analysis `sensitivity.frame_literal` (frame_literal.py): a port frame is kept if it is the token per_message or none, or if it appears verbatim in a line that its provenance cites in the unit's own workspace; every other frame value is nulled, with the reason not_in_cited_lines or no_location. The primary analysis is unchanged. Over the 1,069 frame values in the records returned so far: 965 tokens, 91 verbatim, 9 not in the cited lines (u0005 x2, u0166 x7), 4 without a readable location (u0005 x2, u0392 x2, the latter empty strings).
- **Reader change (qos_literal.cited_text, shared by both literal sensitivities):** 51 frame and 25 QoS provenance entries cite a second line of the same file as a bare ":<lines>" after a space or "(" ("global_position.cpp:338 (...) with parameter default at :70"). The reader now takes such a reference as a line of the last snapshot path named before it; a bare reference with no path before it, or inside a clock time, is not a location. Effect on the records so far: no QoS classification changes (98 values); u0322's "map" and "base_link" frames become verbatim (their parameter defaults are on the second cited line).
- **Order:** no scoring run has used the full set. The only results files are the pre-freeze pilot run of 2026-09-25 (results.json 17:04, results_adjudicated.json 17:17, six quarantined cases). No C3 method outcome has been computed or seen.

## 2026-09-29 — `scoring.py`

- **Change:** Sensitivity frame_literal (frame_literal.py), declared in DEVIATIONS.md on 2026-09-29 before any full scoring run: frames neither a token nor verbatim in a cited line are nulled; reported next to qos_literal and excerpt_excluded.
- **Re-run scope:** Sensitivity analyses only; the primary analysis is unchanged.
- **Hash:** `52e24a4e0412` → `1d5cb11c24db` (FREEZE.json amendment 48)

## 2026-09-29 — `test_scoring.py`

- **Change:** Tests for the bare line-reference reader and the frame-literal rule, including a frame mismatch that rests on a description and a QoS detection that must not change.
- **Re-run scope:** Tests only; 57 pass.
- **Hash:** `7b84e9eeacc5` → `fecdcc6520fc` (FREEZE.json amendment 49)

## 2026-09-29 — `mutation_probe.py`

- **Change:** Seven mutants for the bare line-reference reader, the frame-literal rule and its scoring block; frame_literal.py added to the hashed code files.
- **Re-run scope:** Tooling only. 75 of 75 mutants killed.
- **Hash:** `4af90b3b295a` → `25b3def2851d` (FREEZE.json amendment 50)

## 2026-09-29 — S2 isolation: the session scratchpad was shared (observation, written 09:42 local)

- **Observation:** S2 agents were told to work only inside their task directory, but the agent harness also gives every agent of the session one scratch directory, and many S2 runs used it to fetch dependency definitions (common_msgs, std_msgs, rcl_interfaces and similar tags) for the hashing tool. The same scratch directory held material from earlier stages: the ROBUST bug descriptions S1 read, fix-commit diffs and case texts from S1 runs, and the pilot's repository clones. Isolation of S2 from case knowledge was therefore enforced by the instruction, not by the file system, for this directory.
- **Audit:** every S2 transcript (402) was scanned for tool calls that reference the scratch directory. Every reference is to a subdirectory that one task created for itself (for example u0102_deps), each used by exactly one task, or to the scratch root when a task created its own subdirectory. One run (u0220) listed the scratch root once, which shows directory names (among them 'robust', 's108', 'S1_C1_04') but no contents; no S2 run read, listed or searched any directory it did not create. No S2 run touched another task's workspace.
- **Decision:** no re-run. The threats paragraph states that S2's isolation from upstream material relied on instruction for the shared scratch directory, with the transcript audit as evidence; the audit script's counts are kept with the run log.
- **Audit, final (2026-09-29 10:25 local):** after the seven C3-neutral cases were described, the audit was redone with `audit_s2_scratch.py` (ledger-recorded) over every S2 transcript of the session: 427 tasks, 253 tool-call references to the scratch directory, none to a directory the task did not create, one listing of the root (u0220), and no tool call naming a specification-stage directory (robust, s108, S1_C1_04, S1_C1_05, s1c103) by any path. Output: V19-EMSE/audit/2026-09-29-s2-scratch-audit.json. All agent transcripts of the session were archived to local disk (agent_transcripts_2026-09-29.tgz) because the harness deletes old session transcripts.

## 2026-09-29 — the assembly amendments came after C3 description runs had returned; H1 declared under three readings (written 12:04 local, before any results file was read)

- **Correction of the record.** FREEZE.json stamps are UTC and RUNLOG rows are local (UTC+8). Read in one zone: the first C3 description tasks were dispatched 2026-09-27 17:02 local (u0280–u0283, C3-032); all 34 tier-1 tasks, which cover every selected C3 failure with a matchable class, had returned by 17:50; the steward's notes on u0344 (C3-094), u0355 (C3-099) and on QoS provenance across returned records (u0280, u0281 among them) precede 19:00; the memory note on transcription differences between two description runs was written 19:10; amendments 21 (assemble.py, signature canonicalisation), 22 (adjudicate.py, A2 substance question), 23 (A_adjudicate.md) are stamped 19:09 local, 25 (assemble.py, type-spelling canonicalisation) 19:21, 28 (assemble.py, task ids on units) 19:34. The amendment texts say "declared before any C3 composition is assembled or scored", which is true of the tally (assembly and scoring ran 2026-09-29 10:10); it is not true of the inputs. A note written earlier today in V19-EMSE/audit/2026-09-29-framing-stress-test.md called this refuted on timing; that note mixed the zones and is corrected there.
- **What the amendments do.** Signature canonicalisation removes changed fields that differ only in whitespace, macros or another spelling of one declaration; type canonicalisation joins spellings of one message type; the substance question lets adjudicators demote a change to transcription-only. Each can only remove a finding that the frozen assembly would produce, never add one: the frozen assembly's findings are a superset. DQ reads neither the version delta nor the nominal type, so under the frozen assembly the ECM-only discordant count b can only be equal or higher and the DQ-only count c is unchanged. The amendments therefore act against H1, not for it. This is stated from the code, before any count is known.
- **§16 reading.** PROTOCOL.md §16: "a change to eligibility, matching, or methods after C3 exposure relabels C3 as exploratory." Whether assembly canonicalisation is a change to matching or to a method is a judgement the authors do not get to make alone. The paper will present both readings instead of asserting that C3 remains confirmatory: under the reading that it is not such a change, H1 is confirmatory as frozen; under the reading that it is, C3 is exploratory and no confirmatory test remains, and the H1 record under the frozen assembly is the one that reading calls for.
- **Declared now, before unsealing.** H1 (b, c, exact two-sided McNemar p) is reported under three readings in one table: (i) primary: current assembly, adjudicated fold under the declared roles; (ii) current assembly, fold without the substance demotion (an adjudicate.py flag to be added and logged); (iii) frozen assembly: the freeze-time assemble.py (SHA-256 e2edbeff5108ee26…, recovered from the 2026-09-27 16:27 mutation-probe copy and recorded in the ledger) run on the same specifications, ledger and descriptions, scored with the current scorer. Under (iii) a finding the current assembly does not produce has no A2 record; such findings are reported as provisional and, if any of them changes b on the H1 sample, they are sent to A2 under the same protocol before the paper states (iii) as adjudicated. The ADJ1-only bracket applies to (i) and (ii) as declared on 2026-09-27. Readings (ii) and (iii) leave the primary analysis unchanged.
- **Every other post-exposure change is a sensitivity** (QoS-literal, excerpt-excluded, frame-literal, ADJ1-only, same-repository stratum): each is reported beside the primary and none alters the primary tally.

## 2026-09-29 — `adjudicate.py`

- **Change:** fold --no-substance (reading ii of DEVIATIONS.md 2026-09-29): the declared-role fold without the A2 substance demotion, written to adjudicated_nosubstance/; refused together with --adj1-only.
- **Re-run scope:** Adds a fold variant; the primary fold and the ADJ1-only fold are unchanged.
- **Hash:** `680542c9e623` → `e8307bf5d27c` (FREEZE.json amendment 51)

## 2026-09-29 — `scoring.py`

- **Change:** CLI --adj-dir <name> selects any fold output directory (used for reading ii); existing modes unchanged.
- **Re-run scope:** CLI only.
- **Hash:** `1d5cb11c24db` → `c9752672dfea` (FREEZE.json amendment 52)

## 2026-09-29 — `test_scoring.py`

- **Change:** Reading (ii) test: no-substance fold restores right_reason in its own directory, leaves the primary fold untouched, and is refused with --adj1-only.
- **Re-run scope:** Tests only; 57 pass.
- **Hash:** `fecdcc6520fc` → `f0e01a638d58` (FREEZE.json amendment 53)

## 2026-09-29 — `mutation_probe.py`

- **Change:** Two mutants for the no-substance fold (flag ignored; output directory not separated).
- **Re-run scope:** Tooling only.
- **Hash:** `25b3def2851d` → `c410ad08d578` (FREEZE.json amendment 54)

## 2026-09-29 — reporting decision F′ recorded before unsealing (V agreed at 12:31 local; no results file read before this entry)

- **Decision (V):** framing F′ from V19-EMSE/audit/2026-09-29-framing-stress-test.md. H1 is reported exactly as pre-registered on the 40 selected C3 failures, under the three readings declared above, with the structural power statement (at most 8 assessable in-scope cases; b ≥ 6 with c = 0 needed for p < 0.05; b − c reported as the effect) and the admission that three pre-freeze reviews warned the 40-failure stop was underpowered and the promised power statement was omitted from the frozen protocol, both placed before the result.
- **Rules fixed for every outcome.** If H1 is rejected: reported as confirmatory under reading (i), with readings (ii) and (iii) beside it. If not: the abstract says H1 was not rejected and the empirical part is a bounded retrospective feasibility study (PROTOCOL §1); no superiority claim is made anywhere. In both cases the C1/C2 re-analyses carry the per-dimension account (per-method right-reason detection with Wilson intervals, per class, binary rejection, wrong-reason and unverified counts, false alarms on the three control types, case-control precision/recall/F1 with the prevalence stated, per-case hit matrix with union and intersection, undetected failures by class, derivability by field and ROS generation), and the abstract carries one honest result sentence and no p-value.
- **The 11-of-40 share.** PROTOCOL §1 classed per-class coverage as secondary; promoting it to one abstract clause is a reporting choice made after the class distribution was known (RUNLOG 2026-09-27) and before any outcome was seen. It is named as what it measures: the share of selected C3 failures whose specification carries a class in the matching table (11 of 40, 8 assessable), reported with the ADJ1-only variant, the S1 inter-model class agreement, and the classes of the other 29; the C3-neutral share stays under RQ4 with its interval and is not in the abstract. It is an empirical finding of the held-out corpus, not a listed contribution.
- **Secondary comparison on the 8 assessable in-scope C3 cases:** per case (documented condition, firing rule, A2 verdict, detection stage), counts only, under RQ4, labelled as declared after the class distribution was known and before any outcome was seen; no test statistic.
- **Contributions:** the contract model; the release discipline, labelled specification-only and not evaluated; the blind reconstruction protocol with adjudicated provenance, worded as a protocol with measured limits (κ near zero, ADJ2 1 of 141, 21 of 30 excerpt leak, mid-study model change as a stratum); the per-dimension account and the scoping finding. Novelty (R1#1) is answered from the C1/C2 per-condition counts and the C3 class distribution, not from H1. Runtime cases are relabelled mechanism demonstrations.
- **Frozen-assembly follow-up:** if reading (iii) produces a right-reason finding on the H1 sample that the current assembly does not, it goes to A2 under the same protocol before (iii) is stated as adjudicated.
- **Sealed files at this moment (SHA-256, from V19-EMSE/audit/blind_logs/2026-09-29-results-SHA256SUMS):** results.json d4871fad…, results_adjudicated.json 2cdc2c95…, results_adjudicated_adj1only.json e9ebf76f…, results_adjudicated_nosubstance.json 2cdc2c95…, results_frozenasm.json edc5f541…, results_frozenasm_adjudicated.json 1c0ab974…, results_frozenasm_adjudicated_adj1only.json 844ddc2d…. Unsealed immediately after this entry.

## 2026-09-29 — `mutation_probe.py`

- **Change:** Targets of two existing mutants updated to the fold output-directory expression after the no-substance flag; rerun 77 of 77 killed.
- **Re-run scope:** Tooling only.
- **Hash:** `c410ad08d578` → `41eb1e5c3703` (FREEZE.json amendment 55)

## 2026-09-29 — `freeze.py`

- **Change:** amend() refreshes the DEVIATIONS.md ledger record after appending its entry (the log is append-only; the pre-unsealing record stays in ledger_history).
- **Re-run scope:** Tooling only.
- **Hash:** `807753005490` → `ba462c8426fd` (FREEZE.json amendment 56)

## 2026-09-29 — `freeze.py`

- **Change:** Ledger refresh record written in the manifest's own field names (path, sha256, added_utc); the first version of amendment 56 used other names and broke verify.
- **Re-run scope:** Tooling only.
- **Hash:** `ba462c8426fd` → `83714490b9ae` (FREEZE.json amendment 57)

## 2026-09-29 — `make_report.py`

- **Change:** Full table generator for Section 4: funnel, per-corpus detection/by-class/case-control/pairwise/overlap/undetected, H1 under the three readings plus ADJ1-only and pre-adjudication, strata, sensitivities, kappa, the in-scope C3 cases; writes paper_source/tables_v2/ and report/numbers.json.
- **Re-run scope:** Reporting only; reads the results files, changes no score.
- **Hash:** `ff40d1c5f092` → `4c0fa928be87` (FREEZE.json amendment 58)

## 2026-09-29 — `make_report.py`

- **Change:** Adds the field-derivability table by ROS generation, one overlap table over the four corpora, and the Appendix B ledger (V18 verdict, mechanism-audit match, re-derivation relation, encoding-audit change, v2.1 outcome) for every case the submitted version scored.
- **Re-run scope:** Reporting only.
- **Hash:** `4c0fa928be87` → `cb0c0ecd72da` (FREEZE.json amendment 59)

## 2026-09-29 — `make_report.py`

- **Change:** Appendix B ledger: an encoding-audit row without a corrected record is one in which the audit found no unfaithful value and did not re-score; labelled so instead of 'not scorable after correction'.
- **Re-run scope:** Reporting only.
- **Hash:** `cb0c0ecd72da` → `8df30460e2ea` (FREEZE.json amendment 60)

## 2026-09-29 — `make_report.py`

- **Change:** Adds the per-dimension evidence table of Section 3 (failures with a matchable class, unassessable, right-reason detections per dimension) and the count of v2.1 states in the Appendix B ledger.
- **Re-run scope:** Reporting only.
- **Hash:** `8df30460e2ea` → `515804a1f4a8` (FREEZE.json amendment 61)

## 2026-09-29 — `make_report.py`

- **Change:** The per-dimension table read the C3 selection from a dictionary that main() fills only after the tables are built, so the previous amendment recorded a generator that raised KeyError; it now reads the selection from results_adjudicated.json. Tables regenerated and the per-dimension counts checked against an independent count.
- **Re-run scope:** Reporting only.
- **Hash:** `515804a1f4a8` → `808cf016b3ea` (FREEZE.json amendment 62)

## 2026-09-29 — `make_report.py`

- **Change:** Table widths: the funnel is transposed (one column per corpus), detection cells drop the redundant percentages (k/n with the Wilson interval), the H1, overlap, sensitivity, in-scope, undetected and per-dimension tables use wrapped paragraph columns, and the Appendix B ledger is a longtable that takes its 48 case identifiers from the encoding audit instead of the replaced V18 appendix file (which had emptied the table). Counts re-asserted: 20 V18 hits, 4 without mechanism match, 6 right-reason in v2.1; v2.1 states 10 ineligible, 7 undocumented, 4 warning-only, 6 pilot, 1 not specified, 6 accept, 5 unassessable, 2 not supported, 1 wrong reason.
- **Re-run scope:** Reporting only.
- **Hash:** `808cf016b3ea` → `e88e35475fcd` (FREEZE.json amendment 63)

## 2026-09-29 — `make_report.py`

- **Change:** Width fixes after compiling: one detection table and one false-alarm table over the four corpora replace the four nine-column per-corpus tables; eligibility exits use short names (E2 wiring, E2 internal, E2 build, E2 units); identifiers in paragraph columns may break after an underscore; the sensitivity table drops the Declared column (the exploratory analysis is labelled in its name); column widths of the H1, overlap, in-scope, funnel and ledger tables reduced. No number changes.
- **Re-run scope:** Reporting only.
- **Hash:** `e88e35475fcd` → `d5fb1b24a70f` (FREEZE.json amendment 64)

## 2026-09-29 — `make_report.py`

- **Change:** Column widths only: the class label 'element removed/renamed' becomes 'element removed or renamed' so it can break, the sensitivity H1 column widens, the ledger's mechanism-match column widens and its last column narrows. No number changes.
- **Re-run scope:** Reporting only.
- **Hash:** `d5fb1b24a70f` → `f158c619e2cf` (FREEZE.json amendment 65)

## 2026-09-29 — `make_report.py`

- **Change:** Header widths of the sensitivity and ledger tables (State changes, Mechanism match). No number changes.
- **Re-run scope:** Reporting only.
- **Hash:** `f158c619e2cf` → `69fbb86f7df7` (FREEZE.json amendment 66)

## 2026-09-29 — `make_report.py`

- **Change:** Paragraph columns are set ragged right (no justified rivers in narrow cells). No number changes.
- **Re-run scope:** Reporting only.
- **Hash:** `69fbb86f7df7` → `939458a69ed5` (FREEZE.json amendment 67)

## 2026-09-29 — `make_report.py`

- **Change:** Ledger last column widened by 1 mm so 'undocumented' fits. No number changes.
- **Re-run scope:** Reporting only.
- **Hash:** `939458a69ed5` → `1b269e470ee8` (FREEZE.json amendment 68)

## 2026-09-29 — `make_report.py`

- **Change:** Sensitivity table gains the strict-adjudicator fold as a row (per-corpus right-reason counts from results_adjudicated_adj1only.json, the 9 admitted exclusions, the 6 excluded eligible cases, the 2 detections it removes), which is the expanded-boundary sensitivity PROTOCOL.md promises; numbers.json records the case lists.
- **Re-run scope:** Reporting only.
- **Hash:** `1b269e470ee8` → `a1e9cbae343a` (FREEZE.json amendment 69)

## 2026-09-29 16:34 (local) — scorer did not implement the control bound of Section 15; corrected, both readings reported

**What.** PROTOCOL.md Section 15 ("Bounds") says the primary numbers count `unassessable` as not detected for failures and as **not accepted** for controls; the complete-case numbers drop unassessable cases instead. `scoring.py` `aggregate()` implemented the failure half (an unassessable failure counts as not detected) but not the control half: an unassessable control was left in the denominator and counted as *not rejected*, that is, as a true negative in the case-control matrix. The manuscript's Section 4.2 restated the protocol's rule while its tables carried the lenient count.

**How found.** The pre-dispatch adversarial audit of 2026-09-29 (workflow p5-v19-claim-refutation) reported that the false-alarm denominators include controls the checker could not assess; both verification lenses judged that finding a non-issue, but checking it against the protocol text showed the code and the protocol disagree. The discrepancy is the authors' implementation error, present since the frozen scorer; it does not touch detection states, H1, the sensitivities' H1 records, or any right-reason count.

**Fix.** `aggregate()` now counts an unassessable control as a false alarm for every method in the primary numbers (fixed-observed, fixed-recommended, warning-only, and the case-control matrix); the complete-case numbers are unchanged. Amendment recorded by `freeze.py amend scoring.py`. All readings are rescored (results.json, results_adjudicated.json, results_adjudicated_adj1only.json, results_adjudicated_nosubstance.json, results_frozenasm*.json); the new hashes are in RUNLOG.md.

**Effect (primary, adjudicated).** Unassessable controls: C1 2 observed-fixed, 8 recommended-fixed, 2 warning-only; C2 3 recommended-fixed; C3 1, 14, 1; C3-neutral none. The checker's false alarms become C1 4/10, 10/45, 4/8 and C3 1/6, 15/44, 3/6 (of which 2/10, 2/45, 2/8 and 0/6, 1/44, 2/6 are rejections by findings); every comparator carries the same unassessable counts; case-control precision of the checker 0.43 on C1 and C3 (was 0.60). H1: n 40, b 2, c 0, p 0.5, unchanged.

**Reporting.** The paper reports the protocol rule as primary, states the rejections by findings beside it, and keeps the complete-case numbers as the secondary reading (Section 4.6, Tables of false alarms and case-control).

## 2026-09-29 — `scoring.py`

- **Change:** aggregate(): an unassessable control now counts as not accepted (a false alarm for every method) in the primary numbers, as PROTOCOL.md Section 15 'Bounds' states; the scorer had counted it as not rejected. Complete-case numbers unchanged; detection states and H1 untouched. Found by the 2026-09-29 pre-dispatch audit; DEVIATIONS.md entry of the same time.
- **Re-run scope:** Control false alarms and the case-control matrix in every reading; all results files rescored.
- **Hash:** `c9752672dfea` → `90932768c5dc` (FREEZE.json amendment 70)

## 2026-09-29 — `test_scoring.py`

- **Change:** Regression test: an unassessable control counts as a false alarm for every method in the primary numbers and is dropped in the complete-case numbers (the control half of PROTOCOL.md Section 15 'Bounds'), which no earlier test covered.
- **Re-run scope:** Tests only.
- **Hash:** `f0e01a638d58` → `b22f1b9fcd6a` (FREEZE.json amendment 71)

## 2026-09-29 — `mutation_probe.py`

- **Change:** Two mutants that restore the pre-2026-09-29 control counting (unassessable control not a false alarm; unassessable warning-only not a false alarm) and the updated target line of agg.false_alarm_on_broken; 79 mutants, all killed on assertions.
- **Re-run scope:** Probe only.
- **Hash:** `41eb1e5c3703` → `c08fa3ac95f3` (FREEZE.json amendment 72)

## 2026-09-29 — `make_report.py`

- **Change:** Tables regenerated after the control-bound correction (false alarms, case-control, sensitivity rows carry the protocol rule); the derivability table splits the frame row into identifier / per message / none; the Appendix B ledger labels B-Ver-03 as merged into B-Res-05 and the encoding-audit column reads 'no corrected encoding' where the auditor supplied none.
- **Re-run scope:** Reporting only.
- **Hash:** `a1e9cbae343a` → `6de580bbf5d2` (FREEZE.json amendment 73)

## 2026-09-30 09:29 (local) — wording of the power omission in the manuscript (V decision; reporting only)

- **Change:** The F′ entry of 2026-09-29 committed the manuscript to an admission that named the three pre-freeze protocol reviews and the omitted power statement. V decided on 2026-09-30 that the manuscript states the fact without naming the reviews: "The protocol fixed the H1 sample at 40 eligible held-out failures without a class condition and stated no power analysis for that sample; the deviation log records the omission." (V19-EMSE/paper_source/sec4_results_v2.tex, Section 4.4). The structural power statement (at most 8 assessable in-scope cases; b ≥ 6 with c = 0 needed for p < 0.05; b − c reported as the effect) follows it unchanged and still precedes the result.
- **Record kept here:** protocol v2 was reviewed by three adversarial readers on 2026-09-25 (V19-EMSE/audit/2026-09-25-{OpenAI review,gemini,fable}-protocol-review.md); the triage (2026-09-25-protocol-review-triage.md, row "OpenAI review M9, Google review M2, fable F5 power") adopted a pilot-based power statement; the frozen PROTOCOL.md of 2026-09-25 contains none (the word "power" does not occur in it). The omission is the authors'. The replication package carries a sanitised summary of that triage (protocol/REVIEWS.md), not the review transcripts.
- **Re-run scope:** none (wording only; no code, data or protocol file changed).

## 2026-09-30 09:33 (local) — port sample run 1 withdrawn; prompts/P_ports.md amended; both seats rerun from P_00

- **Change:** Run 1 of the seeded port sample (dispatched 09:03 local) produced 201 ADJ1 records and 80 ADJ2 records before it was stopped at 09:31. ADJ1 treated the `snapshot` symbolic links in its workspace as outside the working directory and marked 147 of 201 records `unverifiable` without opening the source (22 values verified and 3 judged wrong in records where it did open the file); ADJ2 followed the links in all but 3 of 80 records. The cause is the prompt sentence "you may not read anything outside it" together with links that resolve to the snapshot store. `prompts/P_ports.md` now states that the links are part of the working directory and must be read through, and that a provenance string giving a command, a URL or a statement instead of a location is `unverifiable`, except a `definition_hash.py` command over a snapshot file, which the seat runs and compares. Ledger: P_ports.md 9ad2adfc… → 1681b79d… (add-ledger; the earlier hash stays in ledger_history).
- **Records:** run-1 records moved to `adjudication/withdrawn/ports_run1_{adj1,adj2}_2026-09-30/` with READMEs; run-1 logs to `adjudication/logs/ports_run1/`; the preview fold written from run 1 deleted. Both seats rerun from P_00 under the amended prompt; only the rerun is folded into `reliability/port_sample_agreement.json`.
- **Re-run scope:** port sample only (RQ4 provenance agreement, reporting). Nothing in the scoring pipeline reads these files.

## 2026-09-30 10:27 (local) — port sample: records moved to their own directory, collect checks membership, splits go to ADJ3

- **Record location.** Port records were collected into `adjudication/adj1/` and `adjudication/adj2/`, the directories whose every `*.json` file `adjudicate.py fold` reads. A port record has `kind: "P"` and no `case_id`, so with them present the main fold stops with `KeyError: 'case_id'` (reproduced on a scratch copy). No fold ran in that window: the newest files of `adjudicated/`, `adjudicated_adj1only/` and `adjudicated_nosubstance/` date from 2026-09-29. The 402 port records now live in `adjudication/ports/{adj1,adj2}/`; on a scratch copy with the restored layout, the main fold in all three modes reproduces the three output directories byte for byte.
- **Collect.** In packet P_07, ADJ2 judged `P-u0127-4` but wrote the record as `P-u0127-0` (not a sampled port), and the collect step copied it. The record is kept unchanged in `adjudication/withdrawn/ports_run2_adj2_misnamed_2026-09-30/` with a README. `collect` now copies a record only if its file name equals its item_id and the item belongs to the packet. `P-u0127-4` is re-run on ADJ2 alone (`repack` → packet `PR_ADJ2_00`). ADJ1's 201 records were checked the same way: none misnamed, none outside its packets.
- **Adjudication rule (from PROTOCOL.md Section 11, applied to the port sample before its final fold).** Two initial seats judge every value (ADJ1, ADJ2 as in the main run). A value they judge differently goes to ADJ3 (adj3, DeepSeek V4 Pro; DEVIATIONS 2026-09-27), which receives the same port items (packets `PT_*`, ten ports each, all values of each port) under the same prompt and never sees the initial records; its verdict decides that value. Agreement (κ) is computed from the initial records, over the three verdicts and over verified-versus-not. The initial records were read before this entry (they show that most splits are on `frame = none`, which ADJ1 accepts only where the source states the absence); the rule is the protocol's own and was not chosen for this sample.
- **Code.** `sample_ports.py` (collect, repack, third, fold) and `development-runner-06.sh` (packet prefix argument) re-recorded with add-ledger.
- **Re-run scope:** port sample only (reporting). Main adjudication outputs unchanged (byte comparison above).

## 2026-09-30 — `make_report.py`

- **Change:** port_sample(): the provenance check of described values on the seeded 15 % port sample (PROTOCOL.md Section 12, RQ4) as tables_v2/port_sample.tex and NUMBERS['port_sample'], read from reliability/port_sample_agreement.json; refuses while any value is pending the third seat or lacks an initial record. No other table function changed.
- **Re-run scope:** Adds one table; every existing table and number must regenerate byte-identical (checked by SHA-256 before and after).
- **Hash:** `6de580bbf5d2` → `2ce4372a18f4` (FREEZE.json amendment 74)

## 2026-09-30 — `make_report.py`

- **Change:** port_sample(): per group, also the values each initial seat verified on its own and the unverifiable values whose provenance cites no file location, so the stricter reading and the provenance kinds are reported from numbers.json.
- **Re-run scope:** numbers.json port_sample block only; every table must regenerate byte-identical.
- **Hash:** `2ce4372a18f4` → `1f17b6c0360c` (FREEZE.json amendment 75)

## 2026-09-30 — `make_report.py`

- **Change:** port_sample(): layout only (wrapping first column, stacked headers); the table was 72 pt wider than the text.
- **Re-run scope:** tables_v2/port_sample.tex layout; every other table and every number byte-identical.
- **Hash:** `1f17b6c0360c` → `4ca7619100ac` (FREEZE.json amendment 76)

## 2026-09-30 — `scoring.py`

- **Change:** by-class credit (pre-dispatch audit S9/code:F3/SUP-8, 2026-09-30): aggregate() credited a right-reason detection to every class a case carries, so the by-class tables showed detections under 'other' (no matching rule) and DI/DQ detections under element_retyped (a class DI/DQ cannot match), all from C3-099. PROTOCOL.md Section 9 credits a detection to the class its rule matched; the scorer now counts a class only if the method's matched findings name it. Test test_by_class_credits_only_the_matched_class and mutant agg.by_class_every_carried_class (killed; 80/80).
- **Re-run scope:** results*.json by_class only; every other key must be byte-identical after rescoring (checked).
- **Hash:** `90932768c5dc` → `5768ef7cd573` (FREEZE.json amendment 77)

## 2026-09-30 — `test_scoring.py`

- **Change:** by-class credit (pre-dispatch audit S9/code:F3/SUP-8, 2026-09-30): aggregate() credited a right-reason detection to every class a case carries, so the by-class tables showed detections under 'other' (no matching rule) and DI/DQ detections under element_retyped (a class DI/DQ cannot match), all from C3-099. PROTOCOL.md Section 9 credits a detection to the class its rule matched; the scorer now counts a class only if the method's matched findings name it. Test test_by_class_credits_only_the_matched_class and mutant agg.by_class_every_carried_class (killed; 80/80).
- **Re-run scope:** results*.json by_class only; every other key must be byte-identical after rescoring (checked).
- **Hash:** `b22f1b9fcd6a` → `a1e747ad4d98` (FREEZE.json amendment 78)

## 2026-09-30 — `mutation_probe.py`

- **Change:** by-class credit (pre-dispatch audit S9/code:F3/SUP-8, 2026-09-30): aggregate() credited a right-reason detection to every class a case carries, so the by-class tables showed detections under 'other' (no matching rule) and DI/DQ detections under element_retyped (a class DI/DQ cannot match), all from C3-099. PROTOCOL.md Section 9 credits a detection to the class its rule matched; the scorer now counts a class only if the method's matched findings name it. Test test_by_class_credits_only_the_matched_class and mutant agg.by_class_every_carried_class (killed; 80/80).
- **Re-run scope:** results*.json by_class only; every other key must be byte-identical after rescoring (checked).
- **Hash:** `c08fa3ac95f3` → `2767e18da240` (FREEZE.json amendment 79)

## 2026-09-30 12:39 (local) — scorer: by-class credit counted every class a case carries; corrected, all readings rescored

- **Found by** the pre-dispatch adversarial audit of 2026-09-30 (V19-EMSE/audit/2026-09-30-predispatch-audit-triage.md, findings S9, code:F3, SUP-8).
- **Defect.** `aggregate()` credited a right-reason detection to every failed-condition class the case carries. PROTOCOL.md Section 9 credits a detection to the class its rule matched. Only C3-099 carries more than one class among detected cases (definition_mismatch, element_retyped, other); the by-class tables therefore showed ECM, DI and DQ detections under `other` (no rule matches it) and DI and DQ detections under `element_retyped` (a class they cannot match).
- **Fix.** A class is credited only if the method's matched findings name it. Test `test_by_class_credits_only_the_matched_class`; mutant `agg.by_class_every_carried_class` killed (80/80, 0 error). Amendments to scoring.py, test_scoring.py, mutation_probe.py recorded with `freeze.py amend`.
- **Rescore.** All seven results files (four readings in the main tree, three in frozen_run/pathb_v2 copied to results_frozenasm*.json). Compared with the files published on 2026-09-29 (hashes in V19-EMSE/audit/blind_logs/2026-09-29-results-SHA256SUMS-after-control-bound, matched by an untouched copy taken at 11:20 today): every difference lies under `by_class`; reading (ii) is again byte-identical to the primary; every per-case score file is unchanged. New hashes: V19-EMSE/audit/blind_logs/2026-09-30-results-SHA256SUMS-after-byclass. No detection, false alarm, H1 record or other table changes.

## 2026-09-30 — `make_report.py`

- **Change:** pre-dispatch audit 2026-09-30 (V19-EMSE/audit/2026-09-30-predispatch-audit-triage.md): false-alarm table with Wilson intervals (S1/PC-10); strata per corpus with readable labels and an appendix table for every method (PC-02, code:F2, TF-10); sensitivity table counts distinct described values and reports checker detections lost under one definition, exploratory row labelled (N1/N2/TF-2/TF-5/code:F6/F7/PC-16); kappa table states units (TF-6); case-control rounds half up (TF-7); in-scope table gains stage and A2 verdict (PC-14); Rec row marked as having no rule (code:F12); new tables in report_extra.py (detection stage with the unknown-loudness stratum, hit matrix, complete-case detection, sensitivity detail, unassessable list) and numbers (blinding answer by revision class, enrichment shares, C2 generation mix, S1 inter-model agreement, submodule scan).
- **Re-run scope:** tables and numbers.json only; results*.json untouched
- **Hash:** `4ca7619100ac` → `e43081ebde42` (FREEZE.json amendment 80)

## 2026-09-30 — `test_scoring.py`

- **Change:** pre-dispatch audit 2026-09-30 (V19-EMSE/audit/2026-09-30-predispatch-audit-triage.md): false-alarm table with Wilson intervals (S1/PC-10); strata per corpus with readable labels and an appendix table for every method (PC-02, code:F2, TF-10); sensitivity table counts distinct described values and reports checker detections lost under one definition, exploratory row labelled (N1/N2/TF-2/TF-5/code:F6/F7/PC-16); kappa table states units (TF-6); case-control rounds half up (TF-7); in-scope table gains stage and A2 verdict (PC-14); Rec row marked as having no rule (code:F12); new tables in report_extra.py (detection stage with the unknown-loudness stratum, hit matrix, complete-case detection, sensitivity detail, unassessable list) and numbers (blinding answer by revision class, enrichment shares, C2 generation mix, S1 inter-model agreement, submodule scan).
- **Re-run scope:** tables and numbers.json only; results*.json untouched
- **Hash:** `a1e747ad4d98` → `14156804bd7e` (FREEZE.json amendment 81)

## 2026-09-30 — `mutation_probe.py`

- **Change:** pre-dispatch audit 2026-09-30 (V19-EMSE/audit/2026-09-30-predispatch-audit-triage.md): false-alarm table with Wilson intervals (S1/PC-10); strata per corpus with readable labels and an appendix table for every method (PC-02, code:F2, TF-10); sensitivity table counts distinct described values and reports checker detections lost under one definition, exploratory row labelled (N1/N2/TF-2/TF-5/code:F6/F7/PC-16); kappa table states units (TF-6); case-control rounds half up (TF-7); in-scope table gains stage and A2 verdict (PC-14); Rec row marked as having no rule (code:F12); new tables in report_extra.py (detection stage with the unknown-loudness stratum, hit matrix, complete-case detection, sensitivity detail, unassessable list) and numbers (blinding answer by revision class, enrichment shares, C2 generation mix, S1 inter-model agreement, submodule scan).
- **Re-run scope:** tables and numbers.json only; results*.json untouched
- **Hash:** `2767e18da240` → `b8b7490bce53` (FREEZE.json amendment 82)

## 2026-09-30 — `make_report.py`

- **Change:** pre-dispatch audit follow-up 2026-09-30: in-scope table narrowed to fit the text width (A2 column shows -- where the broken composition has no right-reason finding, caption explains; column widths); no value changes
- **Re-run scope:** tables only; results*.json untouched; every other table byte-identical
- **Hash:** `e43081ebde42` → `aa7c8ce27368` (FREEZE.json amendment 83)

## 2026-09-30 14:19 (local) — pre-dispatch audit follow-up: disclosures and reporting corrections (reporting only)

- **C3-063 has no A2 record (SUP-4).** PROTOCOL.md Section 11 asks for A2 on every false alarm on a control. The A2 item builder (adjudicate.py, items) builds an item for every right-reason finding on a broken composition and for every rejection of a fixed composition; a warning-only composition rejected for the wrong reason gets none. There is one: C3-063 (numpy upgrade), rejected by the checker on elements other than the documented one. A verdict cannot change its count: a rejected warning-only composition is a false alarm whatever its reason, and A2 moves a state only between right_reason and unverified (scoring.py, fold). The manuscript now states the A2 scope as built and names C3-063 (sec4, RQ3 and Section 4.8). No item was added after unsealing.
- **Expanded-boundary sensitivity (PC-06).** PROTOCOL.md Section 4 promises an expanded-boundary sensitivity "in which adjudicated disagreements are included". Under the declared roles no sampled exclusion was overturned, so it is a stated zero. Reporting the strict-adjudicator fold (nine exclusions admitted but never described, six eligible cases excluded) in its place was decided after unsealing; the manuscript now says so (Section 4.8).
- **Order note of the 2026-09-29 09:33 entry (PC-17).** That entry says "no scoring run has used the full set". The 2026-09-27 19:34 check (RUNLOG row of that time; DEVIATIONS entry for scoring.py of 2026-09-27) ran the scorer on a temporary assembly of all 133 eligible cases, printed equality only with method outcomes suppressed, and deleted the scratch results. The note should have read "no scoring run whose outcomes were shown has used the full set". The frame-literal sensitivity was therefore declared after that suppressed run and before any outcome was seen. The manuscript's wording is "declared before any method outcome was seen" (Section 4.8 and Table 25 caption).
- **Loudness of robust_bdda1fa (S11).** The specification codes it loud_documented with detection stage run (a Python AttributeError at the first call of a removed function); all three A1 adjudicators agreed. PROTOCOL.md Section 5 item 7 defines loud_documented by a diagnostic at build, connection, or activation. The primary analysis keeps the adjudicated coding; the manuscript reports both readings (Section 4.5: under the strict definition it is the checker's one detection of a silent C1 failure).
- **Abstract (F′ compliance, EMSE limit).** The F′ entry (2026-09-29) fixed one honest result sentence and no p-value in the abstract. An intermediate draft of 2026-09-30 had drifted to 416 words with the discordant counts and p; the abstract was rewritten to 248 words (EMSE: 150-250), with no p-value and the 11-of-40 clause. Response letter r3 no longer says the abstract carries the p-value.
- **Post-hoc contrasts computed after unsealing, reported as such.** The describer's blinding answer by revision class (62 of 118 at the revision the fix changed; 48 of 216 at an unchanged or the fixed revision) and, for the 14 detections, whether a changed unit was answered defective (10 of 14) (report_extra.blinding). The strict fold's resolution changes (13 fixes recorded as observed graded recommended, one unfixed case graded recommended; report_extra.resolution_shift, recounted independently from the score files with the same counts), which explain that fold's smaller observed-fixed denominators (Appendix C, Table 44 caption).
- **Report additions.** Appendix C (app_percorpus.tex) carries the per-corpus tables the protocol lists that Section 4 does not show; the detection-stage table (tab:v2_stage) is in Section 4.5. Strata are reported per corpus; the word "concentrate" is replaced by counts in Sections 4.8, 5, and 6. make_report.py amendment 83 and report_extra.py (ledger) changed labels and column widths only: tables affected are c3_inscope, complete_case, strata, strata_all_methods (derived from the code diff, not byte-compared; no value changed).
- **Re-run scope:** none (reporting and disclosure only; no results file changed).
- **Correction to this entry (written 14:19 local, after checking the build's .aux).** Three numbers in it are wrong for the current build: the adjudication and sensitivity subsection is Section 4.9 (label sec:eval_adjudication), not 4.8; the sensitivity table is Table 28 (tab:v2_sens), not 25; the appendix sensitivity table is Table 43 (tab:app_sens), not 44. Section and table numbers move with every build; the labels are the stable references.

## 2026-09-30 — `make_report.py`

- **Change:** internal re-audit of 2026-09-30 (V19-EMSE/audit/2026-09-30-reaudit-{numbers,letters,relatedwork-prose}.md): strict-fold row relabelled 'strict-adjudicator fold (first adjudicator alone)' (the term ADJ1 was undefined in the paper); Rec row of the dimension table says its one rule only warns (it said no rule, contradicting Tables 6-7)
- **Re-run scope:** labels in h1, sensitivity, dimensions tables; no value changes
- **Hash:** `aa7c8ce27368` → `4bc4fb377b56` (FREEZE.json amendment 84)

## 2026-09-30 — `test_scoring.py`

- **Change:** internal re-audit of 2026-09-30 (V19-EMSE/audit/2026-09-30-reaudit-{numbers,letters,relatedwork-prose}.md), finding F7: test that a failure of unknown loudness is counted once in the detection-stage table
- **Re-run scope:** tests only
- **Hash:** `14156804bd7e` → `5646caf79822` (FREEZE.json amendment 85)

## 2026-09-30 — `mutation_probe.py`

- **Change:** internal re-audit of 2026-09-30 (V19-EMSE/audit/2026-09-30-reaudit-{numbers,letters,relatedwork-prose}.md), finding F7: mutant report.stage_double_counts_unknown (restores the double count); 83/83 killed
- **Re-run scope:** tests only
- **Hash:** `b8b7490bce53` → `e93a59af954b` (FREEZE.json amendment 86)

## 2026-09-30 15:02 (local) — internal re-audit of the rewritten passages: corrections (reporting only)

- **Source.** Three read-only re-audit agents on today's changed text (reports V19-EMSE/audit/2026-09-30-reaudit-numbers.md, -letters.md, -relatedwork-prose.md): numbers 0 blocking/0 major/10 minor; letters 1 blocking/3 major/18 minor; related work and prose 3 major/37 minor/5 nit. Every finding was checked against the files before it was fixed; none changed a detection, a false-alarm count, the H1 record or a sensitivity result.
- **Generator corrections (report_extra.py, re-ledgered; test and mutant added).** (1) The detection-stage table counted a failure of unknown loudness (robust_c4e1187) both under its stage and in its own row; stage rows now exclude it, so C1's rows sum to its 34 failures (C1 build 4 → 3). (2) The blinding contrast put the 46 provider snapshots at a consumer's built-against revision into an "unmatched" class and left them out of the comparison group; they are now their own class. The comparison group is 56 of 262 (other revisions of the same cases), not 48 of 216; 118 + 262 = 380. The contrast (62 of 118 against 56 of 262) is unchanged in direction.
- **Letter correction of substance.** Three letter passages (ae, r1, r3) said the pre-registered hypothesis "is not rejected", which states the result the wrong way round; they now say the test does not reject the null and H1 is not supported, as the manuscript does.
- **Manuscript corrections.** Fig. 1 caption listed "version skew" among the four conflicts while the figure marks the version dimension compatible and the recovery dimension as the fourth; the evaluated checker only warns on recovery. The figure (figures/fig_hero_tikz.tex) now shows 3 conflicts and 1 warning, its vertical connectors start on the connecting edge, and the caption says it is illustrative and that none of the 14 detections came from frame, resource, permission, or recovery. Two different Canelas et al. 2024 papers rendered identically; bib years set to 2024a/2024b. Other corrections: the Empirical Grounding paragraph said the evaluation reuses all listed sources as ground truth (it reuses ROBUST only); the Introduction's "point solutions" paragraph now names ROSpec; new Section 2 sentences restated to what the verified abstracts support (QoS Guard, ROSInfer, Roseau, VASO, unit mismatches); controls qualified as coming from scored eligible cases (C3-132 and C3-153, beyond the pre-registered walk, were not assembled); A2 scope stated as executed in Methods; American spelling throughout; hyperref anchors made unique.
- **Re-run scope:** tables regenerated (detection_stage, dimensions, h1, sensitivity, sensitivity_detail changed; labels and the one stage count only); no results file changed.

## 2026-09-30 — `make_report.py`

- **Change:** R1 review 2026-09-30 (V19-EMSE/audit/2026-09-30-*-review-R1.md; triage audit/2026-09-30-R1-triage.md): derivability table gains min_rate_hz (peer review m10); Appendix B ledger labels an ineligible case by its first failed criterion, as the funnel does (peer review m13)
- **Re-run scope:** tables derivability and ledger_v18; no value elsewhere changes
- **Hash:** `4bc4fb377b56` → `5838bf2619ae` (FREEZE.json amendment 87)

## 2026-09-30 — `test_scoring.py`

- **Change:** R1 review 2026-09-30 (V19-EMSE/audit/2026-09-30-*-review-R1.md; triage audit/2026-09-30-R1-triage.md): test for report_extra.alert_ratios (an unassessable control is not an emitted alert; a wrong-reason rejection is)
- **Re-run scope:** tests only
- **Hash:** `5646caf79822` → `8ddf79eb764d` (FREEZE.json amendment 88)

## 2026-09-30 — `mutation_probe.py`

- **Change:** R1 review 2026-09-30 (V19-EMSE/audit/2026-09-30-*-review-R1.md; triage audit/2026-09-30-R1-triage.md): mutant report.alert_counts_unassessable_control; 84/84 killed
- **Re-run scope:** tests only
- **Hash:** `e93a59af954b` → `581fe8a22611` (FREEZE.json amendment 89)

## 2026-09-30 16:28 (local) — R1 external review: corrections and disclosures (reporting only; primary analysis unchanged)

- **Two detections rest on the platform's own record (peer review M1).** B-Ver-05's credited consumer reference cites `artifact.txt:2`, the ROS 1 md5-mismatch message quoted in the source; B-Sig-02's two message types are fields of the connection record the question quotes (spec revision_basis). Stage A2 verified them because the text is at the cited location: it checks location, not the kind of source. The protocol meant excerpt artifacts to carry no log lines. The primary counts stay as frozen; the manuscript now reports the reading without these two (C2 1/12, 12 detections, 12 version, 0 signature) in sec4 (RQ1 detections), Sec. 3.2.8, Discussion, Conclusion and Threats, and corrects the sentence that said provenance verification rules this out. Artifacts with fault material: at least 23 of 30 (21 with URLs, plus B-Ver-02 and B-Sig-02 quoting the platform's record).
- **tf2 false alarms (peer review M2).** The fixed tf2 revision declares _allFramesAsDot twice (buffer_core.h:300-301) where the built-against revision declared it once (:296): a real code change that the one-declaration-per-element version rule reports as a break. Stage A2's "transcription_only" verdicts on those paths (adjudicated/substance_verdicts.json, robust_0481047 and robust_7284788 resolved) are adjudicator errors; the counts do not change (a rejected control is a false alarm whatever its verdict). The limit is now stated with the version rule (Sec. 3.3.5), in the coverage table (tab:coverage) and in RQ3.
- **NT nesting (peer review m4, OpenAI review F1).** NT is nested on PAIR and CONCURRENT edges; on UPGRADE it reads pair views that ECM does not read. Observed: 0 of 371 assembled upgrade pair views carry two different message types (report_extra.nt_pair_views). Text changed from "by construction" to this statement; no test added.
- **Precision (OpenAI review F3).** The case-control precision is a ratio of right-reason detections to right-reason detections plus rejected controls, not a binary classifier's precision. The manuscript says so and reports, as post-unsealing supplements, binary PPV by findings (C1 11/15, C3 4/6) and the share of rejections naming the documented cause (C1 6/15, C3 3/6) (report_extra.alert_ratios, test and mutant added).
- **Canonical form is lossy (OpenAI review F2, peer review m7, Kimi review F5).** It removes all __attribute__ annotations and deprecation macros, ignores spacing inside quoted literals, and drops the msg/srv/action category. Enumerated effect: four records in C3N-008 and C3N-027, each a visibility macro kept by one description run and dropped by the other; on RQ3 it removed the freeze-time assembly's false alarm on C3N-027's observed fix. Disclosed in Sec. 4.2.
- **Other corrections.** Permission requirement recorded on 4 tasks / 3 cases (C3-119, an upgrade, not evaluated by the rule); loudness definition now includes runtime-enforced refusals (PROTOCOL Sec. 5 item 4 wording); conditions (ii)-(iv) could not be evaluated (0 deadlines, 2 of 2,144 minimum rates, exclusive claims in 15 of 409 descriptions); strict-adjudicator fold stated as one-sided; eight in-scope held-out cases have at least one assembled unit, two without the implicated element; OpenAI review F6/F9 corrections to null-field and frame/unit fallback descriptions; coverage-and-assumption table added (PROTOCOL Sec. 1 commitment); PhysFrame 190 inconsistencies / 154 true positives; dependency-bug sentence restated from the abstract; Fig. 1 redrawn to show only composition rules; Fig. 4 without rotated text or hatching; Fig. 2 upgrade box "version check implemented"; orphaned withdrawn-evaluation files moved from paper_source/ to V19-EMSE/audit/withdrawn-from-paper_source/; five references added (ROSDiscover, ROS computation graph, Foo et al. 2018, Beugnard et al. 1999, and raemaekers2017 now cited).
- **Correction of earlier entries.** (1) The 2026-09-27 excerpt-artifact entry says "none on H1's matchable cases (all 11 are snapshot-based)"; C3-035 and C3-065 are excerpt-based (results_adjudicated.json sensitivity.excerpt_excluded.excluded). (2) Entries and code comments citing "PROTOCOL.md Section 15 ('Bounds')" mean the bounds bullet of Section 12; Section 15 is "Outputs and reproduction".
- **Held for V:** re-anchoring the introduction and possibly the title on version breakage (peer review m15, DeepSeek review F1); the Appendix D authoring walkthrough, whose V11 records name a former co-author (OpenAI review F4).
- **Re-run scope:** tables regenerated (derivability, ledger_v18, detection_stage earlier today); numbers.json gains unit_fields, perm_requires_present, nt_upgrade_pair_views, alert_ratios; no results file changed.
- **Correction to this entry (16:29 local, checked against PROTOCOL.md headings):** the runtime-enforced refusal clause of the loudness coding is in PROTOCOL.md Section 4 (Eligibility, the paragraph on failed conditions), not "Sec. 5 item 4".

## 2026-09-30 16:41 (local) — Appendix D (authoring walkthrough) withdrawn (manuscript only)

- **Found by** OpenAI review R1 (F4): the V11 records attribute the timed walkthrough to Zeyd Boukhers, the manuscript to "a co-author who did not participate in the contract-checker design", and no original packet is in the V19 delivery. V stated on 2026-09-30 that Boukhers did nothing of the kind and that the attribution was written by the agent working on V11. No record shows any person performing the session.
- **Change.** Appendix D (narrative, timing and difficulty table, the manifest excerpt from that session, take-away) and the Discussion sentence citing it are removed; the Discussion now says only that authoring cost was not measured. The removed text is kept in V19-EMSE/audit/withdrawn-from-paper_source/appendixD-authoring-walkthrough-removed-2026-09-30.tex. The declaration "does not involve human participants" is now accurate without qualification.
- **Re-run scope:** none (no data, code or results involved).

## 2026-09-30 16:59 (local) — Introduction re-anchored on version breakage (manuscript only)

- **Found by** peer review R1 (m15) and DeepSeek review R1 (F1): the introduction motivated six dimensions while the evaluation supports one. V decided on 2026-09-30 to re-anchor the introduction and keep the title.
- **Change.** The introduction now opens on an upgrade that breaks one consumer of a provider and not another, and states that 25 of the 93 documented failures are of this kind (tab:dim_evidence). Its second paragraph ends by explaining why a retrospective study can test only the version dimension, with exact coverage counts from RQ4 (a coordinate frame on 182 of 2,144 described ports, a unit on 190, a quality-of-service value on 43; exclusive claims in 15 of 409 descriptions). Fig. 1 is redrawn as an illustrative upgrade (version-number view vs. the consumer-aware version rule); its caption says it is not one of the documented cases. Scenario 2 now renames a field that one consumer reads and another does not, and says semantic versioning takes the provider's word for the release type. The Sig paragraph of sec:evidence_tiers said a frame is recorded on "about half" of ports, which counts the literal `none`; it now gives 8 %, and RQ4 states the totals it rests on.
- **Backups:** V19-EMSE/audit/Paper5_ECM_Contracts_v19.before-intro-reanchor-2026-09-30.tex, .before-R2-prefreeze-2026-09-30.tex, sec4_results_v2.before-R2-prefreeze-2026-09-30.tex; audit/figures-before-R1fix/fig_hero*.composition-version.*.
- **Re-run scope:** none (counts read from report/numbers.json; the port totals recomputed read-only with make_report.derivability's own iteration, agreeing with its per-generation counts).

## 2026-09-30 — `make_report.py`

- **Change:** Pre-R2 audit (hostile lens F11): the case-control table columns are renamed 'Prec.\ ratio' and '$F_1$ (ratio)', because unassessable controls are false positives under the protocol's bound and the column is not a binary classifier's precision. Labels only; no number changes.
- **Re-run scope:** casecontrol_C1/C2/C3/C3N.tex headers regenerated; numbers.json unchanged by this amendment
- **Hash:** `5838bf2619ae` → `398052e99e0d` (FREEZE.json amendment 90)

## 2026-09-30 — `test_scoring.py`

- **Change:** Pre-R2 audit: test_alert_ratios adds a warning-only case rejected for its documented condition (cause-correct share counts it); new test_consumer_blind_ablation_widens_reads_only_on_upgrades for the exploratory ablation. 64 tests pass.
- **Re-run scope:** tests only
- **Hash:** `8ddf79eb764d` → `6fc26fb6abab` (FREEZE.json amendment 91)

## 2026-09-30 — `mutation_probe.py`

- **Change:** Pre-R2 audit: exploratory_consumer_blind.py added to CODE_FILES; three mutants added (report.cause_share_drops_warning_cause, ablation.added_reads_unverified, ablation.mutates_input). 87/87 killed.
- **Re-run scope:** mutation inventory only
- **Hash:** `581fe8a22611` → `a4460ebfd963` (FREEZE.json amendment 92)

## 2026-09-30 17:59 (local) — Pre-R2 adversarial audit: corrections and one exploratory analysis

- **Found by** three independent pre-dispatch lenses on the R1-to-R2 diff (V19-EMSE/audit/2026-09-30-preR2-{hostile,consistency,numbers}.md; dispositions in 2026-09-30-preR2-triage.md).
- **Exploratory analysis, decided after unsealing (not pre-registered).** `exploratory_consumer_blind.py` scores the version rule without its consumer condition, with the frozen checker and scorer unchanged: each assembled upgrade unit's consumer references are widened to its changed elements, and the added references' provenance is marked as not required, so credit rests on the changed element alone. Result (report/exploratory_consumer_blind.json): the consumer-blind rule detects the checker's 14 and three more (B-Sig-01, robust_35682ec, robust_c4e1187, each missed because the consumer description did not record the reference), rejects two more warning-only controls (robust_778c1ac, C3-028), and no further fixed control (in 39 of 42 assembled fixed upgrade compositions no element changed; in the other three the consumer references a changed element). Reported in RQ3 and wherever the manuscript attributed the detections to the consumer condition. Script and output are ledgered; test and two mutants added.
- **Correction of a reported number.** The cause-correct share of rejections (RQ3, letter R3) counted only right-reason failure detections in its numerator and omitted warning-only compositions rejected for their documented condition (robust_5ee65b0 on C1, C3-135 on C3). `report_extra.alert_ratios` fixed (ledgered); 6 of 15 and 3 of 6 become 7 of 15 and 4 of 6, and the sentence that the two readings "bracket" the precision ratio is withdrawn. Test and mutant added.
- **Correction of the power statement (RQ1).** The statement decided on 2026-09-29 counted 8 assembled in-scope cases as assessable; in 2 of them (C3-044, C3-100) the unit carrying the implicated element did not assemble, which the assembly already showed. Corrected to 6 after unsealing; the test could have rejected only with b = 6, c = 0.
- **Authors' reading after unsealing, no count change.** Stage A2 judged the two tf2 `_allFramesAsDot` deltas on C1 fixed compositions transcription differences; the fixed revision's header declares the function twice (an added overload), so they are real changes. The manuscript states this as the authors' reading; the protocol counts a rejected control as a false alarm whatever the verdict. A source audit of the credited element of all 13 version detections was run (V19-EMSE/audit/2026-09-30-detection-substance-audit.md).
- **Manuscript and letters (no data involved).** Introduction and Fig. 1 re-anchored and redrawn (nav_server 4.1→4.2, two consumers, declared-version and definition checks on the left, no WRONG/CORRECT); the "2,144 message ports" statistic replaced by port records with a kind breakdown and endpoint-only shares; build/loader named as the platform's consumer-aware check and not instantiated as a baseline; contract schema and Listing 1 gain `provides`/`references`; coverage table and implementation scope describe unit, frame, and permission rules as `canonical.py` and `_perm` implement them; author contributions restated in CRediT roles (V: as in the authors' other papers); letters AE/R1/R2/R3 updated.
- **Held for V:** disclosure of the withdrawn Appendix A of the submitted version (the authoring walkthrough) in the letters.
- **Re-run scope:** tables regenerated (only the case-control headers changed); numbers.json changed only in alert_ratios; results files unchanged.
- **Correction to this entry (2026-09-30 18:05 local, after the source audit V19-EMSE/audit/2026-09-30-detection-substance-audit.md).** The authors' reading of the two tf2 `_allFramesAsDot` deltas was wrong under the A2 definition (prompts/A_adjudicate.md item 4: what a consumer depends on; "another line of the same declaration" is transcription). The no-argument declaration the consumer calls is unchanged in both fixed revisions, and the running record cites the added overload's line; A2's transcription_only verdict stands, and the manuscript (RQ3) now says so. The same sentence in the R1 manuscript ("which they are not") was already wrong. No count changes: a rejected control is a false alarm whatever the verdict. The audit found the credited element of all 13 version detections substantively changed (removal 4, field or type 2, default 1, signature or parameter list 3, path or name 2, result field 1), with two caveats recorded in the report: B-Ver-05's ActionResult definition is not in either snapshot (inferred from the .action file), and C3-106's rename is a namespace change derived from the message generator's code, not from generated headers.

## 2026-09-30 19:00 (local) — Withdrawal of the submitted Appendix A disclosed in the letters (letters only)

- **Decision (V, 2026-09-30):** the authoring walkthrough stays removed and is not replaced in this revision; a study in which people write contracts for real modules is left to future work.
- **Change.** AE item 3, the response to Comment 1.10 (authoring effort), and the response to Comment 3.6 (appendix placement) now say that the former Appendix A of the submitted manuscript, a timed authoring walkthrough, is withdrawn because no record shows the session took place as described, and that the revision makes no claim about authoring time. The response to Comment 1.10 answers the effort question with what the revision measures (the version rule reads two element lists that the evaluation derived from code; derivability of the other fields). Its stale "ports" figures were replaced by the port-record figures of RQ4. Origin of the withdrawn record: V11-JSS/audit/F7_walkthrough_results.md and reflection.md, written by the agent working on V11 and attributed to a co-author who did not perform it (V, 2026-09-30).
- **Re-run scope:** none.

## 2026-09-30 — `scoring.py`

- **Change:** Comment only: the Bounds rule is the bounds bullet of PROTOCOL.md Section 12 (Analyses), not Section 15 (R2: GLM review F1, Kimi review F1, Grok F8). No code change.
- **Re-run scope:** none; tests and mutation probe rerun
- **Hash:** `5768ef7cd573` → `464d6115e01e` (FREEZE.json amendment 93)

## 2026-09-30 20:21 (local) — R2 corrections (manuscript, letters, one comment)

- **Found by** round R2 (reports V19-EMSE/audit/2026-09-30-*-review-R2.md; dispositions in 2026-09-30-R2-triage.md). No count, table, or result file changes.
- **Exploratory ablation, restated.** The three matches the consumer-blind variant adds were not adjudicated (Stage A2 ran before the analysis; their provenance is "not refuted", not verified), so they are reported as provisional matches, not detections. The stated cause of the three was wrong: in each, the consumer's code does not name the changed element (a generic introspection tool; a dependence through another package's return type; the old name of a renamed topic that the case inventory did not list), which is a limit of the consumer condition and of the inventory, not a description error. Both variants compare only the elements the case specification listed (at most ten per upgrade case, median 6.5). The rule's declared-major-version condition is unchanged by the ablation. The added references carry a synthetic provenance marker; this is now stated.
- **Fixed controls.** For upgrades, 36 of 42 assembled fixed compositions describe the provider with one task on both sides and 3 more have an empty delta, so they cannot fire the version rule; the three non-trivial ones are all rejected; 4 of 9 assessable warning-only upgrades are rejected by findings (6 consumer-blind); across all compositions only field_break, semver_major, missing_permission, and type_mismatch ever fired. RQ3, the conclusion, and the abstract now say that the fixed-control false-alarm rates say little about the version rule. The earlier phrase "because the fix aligned the consumer with the release" is withdrawn.
- **Introduction and Fig. 1.** The example is now a renamed code symbol that the build reports once the consumer is rebuilt, the kind behind 9 of the 13 version detections; the introduction states that the rule also covers endpoints but that no detection is of that kind and the one documented renamed topic was missed. The 25 version-class failures are described by class (22 upgrades, 3 pairs), not by a removal-in-time gloss.
- **Schema.** `provides` is a map from element to declaration with an explicit absent state (what assemble.py compares), and the text says the evaluation derived these records from code or quoted artifacts for the listed elements only.
- **Other corrections.** Condition (iv) describes the implemented rate and deadline comparisons; the ROS 1 wildcard is stated; the undeclared-field rule states the permission exception; the evaluation wrapper scores only critical findings, so the recovery warning is never scored; complete-case drops controls by the checker's state for all methods; DQ's quality-of-service rules never fired (DQ behaved as definition identity); the tf2 A2 explanation is stated per case; runtime-demonstration dates (June 2026 runs, the QoS probe of 2026-09-24, the frame output re-run of 2026-09-29) and what they show; the checker's last code change (2026-06-26) is disclosed; the letters no longer say that nesting made the null false regardless of data; Discussion sentences on unmeasured benefits are marked as design positions; six references added after two-source verification (V19-EMSE/audit/2026-09-30-R2-litsearch-verify.json).
- **Comment amendment.** scoring.py cites the Bounds rule as PROTOCOL.md Section 12 (logged above); tests 64 passed, mutation probe 87/87, MUTATIONS.md regenerated and ledgered.
- **Re-run scope:** none.

## 2026-09-30 — `test_scoring.py`

- **Change:** Pre-R3 audit (hostile lens M1): the consumer-blind ablation counted element additions as changes, which no API-diff tool reports as breaking. A breaking-only variant (changed elements the built-against provider declares: removals and modifications) is added next to the existing one; the existing variant is kept and labelled as also flagging additions. Exploratory, decided after unsealing. New test test_consumer_blind_breaking_only_leaves_out_additions (additions and empty declarations excluded; a missing description raises).
- **Re-run scope:** tests only; 65 pass
- **Hash:** `6fc26fb6abab` → `ae8b21fe78bf` (FREEZE.json amendment 94)

## 2026-09-30 — `mutation_probe.py`

- **Change:** Pre-R3 audit (hostile lens M1): the consumer-blind ablation counted element additions as changes, which no API-diff tool reports as breaking. A breaking-only variant (changed elements the built-against provider declares: removals and modifications) is added next to the existing one; the existing variant is kept and labelled as also flagging additions. Exploratory, decided after unsealing. Three mutants added (ablation.breaking_only_keeps_additions, ablation.breaking_only_counts_empty_declaration, ablation.breaking_only_missing_description_is_empty). 90/90 killed on an assertion.
- **Re-run scope:** mutation inventory only
- **Hash:** `a4460ebfd963` → `925befb381a4` (FREEZE.json amendment 95)

## 2026-09-30 — pre-R3 audit: breaking-only ablation variant, "pre-specified", and text corrections (written 2026-09-30 21:04 local)

- **Ablation.** The pre-R3 hostile lens found that the consumer-blind variant counts element additions as changes (Δ includes an element one release declares and the other marks absent), which no API-diff tool reports as breaking. A second variant, computed after unsealing like the first, adds to the consumer's references only the changed elements that the built-against provider's recon record declares (removals and modifications). Result (report/exploratory_consumer_blind.json): it matches the 14 primary detections and two more (B-Sig-01, robust_c4e1187), rejects no further control, and changes no fixed or warning-only state. The all-changes variant's third extra match (robust_35682ec) and its two extra warning-only rejections (robust_778c1ac, C3-028) all come from added elements; C3-028's rejection is right_reason (names the documented deprecation). The manuscript's "avoided two false alarms" is withdrawn: against the breaking-only variant the consumer condition cost two provisional matches and avoided none. Verified before the change: all 13 credited version tokens are declared at the built-against revision (none is an addition).
- **Terminology.** The freeze manifest was never deposited with an external registry (it lives in this package, the audit copy and local run logs), so "pre-registered" is replaced by "pre-specified" in the manuscript, appendix and letters, with one sentence in Section 2 and one in Section 4.2 saying why. Code comments and the H1 label in results files keep the old word; the protocol file is frozen.
- **Other corrections from the lens reports** (V19-EMSE/audit/2026-09-30-preR3-{hostile-consistency,numbers}.md): inventory median is 6 over the 47 scored upgrade cases (6.5 was C1 only); the scratch-directory audit counts references to the scratch root by runs that created a subdirectory there (DEVIATIONS 2026-09-29 said so; the manuscript had "every one to a subdirectory"); the frame/unit, co-activation and rate conditions produced nothing because none of their failures could be evaluated with declared values (the text said two of three); C3N-008 has the provider older than the consumer's built-against revision, the direction S1 coded as PAIR in C3-035, now disclosed with its effect (12 version detections, 1 on C3-neutral); the checker's last change (2026-06-26) followed the submitted evaluation's results on C1/C2 and can only have lowered false alarms there, now stated as such.

## 2026-09-30 — `adjudicate.py`

- **Change:** R3 (peer review M1, OpenAI review F1): score_control leaves a control's findings without unit_kind, and evidence() matched a fixed composition's version-rule finding to the pair view of the element, which carries no version provenance, so 5 A2 items went out with null provenance. New module-level unit_for_finding() takes the upgrade unit for field_break/semver_major; evidence() refuses a version finding without an upgrade unit; item ids via item_digest() (same formula); new subcommand a2fix rebuilds only existing all-null items (packet A2_R3.json, map ledger/a2_r3_supersedes.json), because items() would derive A2 items from the scores after the A2 fold.
- **Re-run scope:** A2 evidence for 8 items (5 version, 3 permission); no score, table or H1 change
- **Hash:** `e8307bf5d27c` → `54a028ab5070` (FREEZE.json amendment 96)

## 2026-09-30 — `assemble.py`

- **Change:** R3 (peer review M1, D2): side_block looked up perm_requires[TOKEN] / perm_grants[TOKEN], while S2 keys a value by its exact path perm_requires.values[TOKEN] (recon census: .values[ 14, other form 0), so no permission provenance reached any composition. Reads the .values[ key and keeps the old form.
- **Re-run scope:** re-assembly changes B-Beh-02 and robust_bb3c7ec by added provenance entries only; encodings identical; re-scoring leaves every results file identical (robust_bb3c7ec broken permission findings: provenance unverified -> verified, state wrong_reason unchanged)
- **Hash:** `f2951d354070` → `40907dd6b6f4` (FREEZE.json amendment 97)

## 2026-09-30 — `scoring.py`

- **Change:** R3 (external review F-N1): H1 label says pre-specified, as the manuscript now does.
- **Re-run scope:** label string in results files only
- **Hash:** `464d6115e01e` → `c671d88baf58` (FREEZE.json amendment 98)

## 2026-09-30 — `make_report.py`

- **Change:** R3: comment wording pre-registered -> pre-specified.
- **Re-run scope:** comment only
- **Hash:** `398052e99e0d` → `c63fad9a3592` (FREEZE.json amendment 99)

## 2026-09-30 — `test_scoring.py`

- **Change:** R3: tests for unit_for_finding, the evidence refusal, permission provenance in side_block, and the breaking-only ablation restricting the changed set (OpenAI review F2).
- **Re-run scope:** tests only; 68 pass
- **Hash:** `ae8b21fe78bf` → `c01db657b3d4` (FREEZE.json amendment 100)

## 2026-09-30 — `mutation_probe.py`

- **Change:** R3: mutants adj.control_version_finding_to_pair_view, adj.version_evidence_unchecked, asm.permission_provenance_old_key_only, ablation.breaking_only_keeps_added_elements_in_delta; a2.positional_ids re-anchored to item_digest; without --report nothing is written (peer review m9).
- **Re-run scope:** tooling only; 94/94 killed in the scratch copy
- **Hash:** `925befb381a4` → `f3b4e6e1ac85` (FREEZE.json amendment 101)

## 2026-09-30 — R3: A2 evidence on fixed compositions, permission provenance in assembly, breaking-only ablation (written 2026-09-30 22:54 local)

- **Found by** R3 seats peer review (M1) and OpenAI review (F1), verified by the steward before any fix. 9 of the 48 A2 items, all on resolved compositions, went to the adjudicators with null provenance. (D1) `score_control` leaves a control's findings without `unit_kind`, and `adjudicate.evidence()` then matched a fixed composition's version-rule finding to the first unit carrying the element, the pair view, which has no version provenance: 5 items (C3-099, robust_0481047, robust_7284788 ×3). (D2) `assemble.side_block` looked up `perm_requires[TOKEN]`, while S2 writes the exact path `perm_requires.values[TOKEN]` as its prompt requires (recon census: `.values[` 14 keys, the other form 0), so no permission provenance reached any composition: 3 items (robust_bb3c7ec) lost the provenance that exists, and the fourth (robust_292b5cc) has none in its recon, so its null is real. The adjudicators' records on these items say the packet gave no location; they account for 20 of the 24 values one initial adjudicator left unverified, all 4 substance splits, 9 of the 11 items sent to the third adjudicator, and 6 of the 8 standing demotions.
- **Fix.** adjudicate.py: `unit_for_finding()` takes the upgrade unit for `field_break`/`semver_major`, `evidence()` refuses a version finding without one; assemble.py reads the `.values[` key and keeps the old form. Tests and mutants added (68 tests; 94/94 mutants killed on an assertion). Re-assembly changes two compositions (B-Beh-02, robust_bb3c7ec) by added provenance entries only; re-scoring under all four readings leaves every results file identical (robust_bb3c7ec's broken permission findings change from provenance unverified to verified; their state stays wrong_reason). No detection, false alarm, control verdict or H1 count moves: the protocol counts every rejected control as a false alarm whatever the A2 verdict.
- **Re-adjudication.** Rebuilding all packets with `items()` would derive A2 items from the scores after the A2 fold (three demoted right-reason items would disappear), so `adjudicate.py a2fix` rebuilds the evidence of the existing all-null items only: 8 items in `adjudication/packets/A2_R3.json` under new ids (the digest covers the evidence), map `ledger/a2_r3_supersedes.json`. ADJ1 and ADJ2 run on A2_R3 under the declared roles; ADJ3 on any split. The 8 superseded records of each adjudicator (and ADJ3's on them) move to `adjudication/withdrawn/a2_null_evidence_2026-09-30/`; the fold, scores and tables are then regenerated. The dispatch started from a scratch copy while the R3 freeze held; records are collected into the project afterwards.
- **Ablation (OpenAI review F2).** The breaking-only consumer-blind variant widened the references only with changed elements the built-against provider declares, but left the changed set itself unfiltered, so an addition the consumer already references (C3-046, C3-135) was still flagged. The variant now restricts the changed set too. No composition state or control verdict changes (both variants' outputs as before).
- **Wording.** The H1 label in scoring.py and two comments say pre-specified.

## 2026-10-02 — V20 replacement A2 completion in isolated workspace

- Scope: eight fixed-composition items (five version packet-view errors, three permission provenance-lookup errors). `ledger/a2_r3_supersedes.json` maps new IDs to withdrawn IDs. Old 24 role records are retained in `adjudication/withdrawn_A2_R3/`; no old/new pair is counted together. Production experiment and V19 are untouched.
- ADJ1: recovered GPT-6-astra records. ADJ2: actual zai/glm-5.2, eight complete records. Its first gateway run timed out after five; only after terminal timeout was confirmed, one continuation in the same session completed the three missing permission items. No duplicate independent run was launched.
- ADJ3: actual deepseek/deepseek-v4-pro; seven replacement provenance splits in two neutral packets. Initial answers were withheld. Four version records lacked required provenance entries; original records are preserved under `adjudication/work/A3_R3_versions.adj3/adjudication/schema_incomplete_original/`, with hashes in `adjudication/logs/A3_R3_versions.schema-repair-manifest.json`. A same-session request completed only the required schema; no verdict was prescribed.
- The initial two records agree on all 28 substance judgments, including four tf2 transcription-only changes. ADJ3 is used only for split domains, so an unsolicited differing substance label does not override their agreement.
- Final active A2: 48 items, 100 provenance values, 85 initial agreements; 15 disagreements on ten items (seven replacement items). All 15 are verified by ADJ3. One of these ten also splits on operation; ADJ3 agrees with the specified edge. Final primary demotions: six paths, all transcription-only (four tf2 fixed-control paths and two xacro warning-only paths). The genuine missing-provenance item robust_292b5cc was not replaced; ADJ2/3 located source evidence independently, which does not repair the source description or establish actual remote-mode I/O state.
- Re-ran primary, ADJ1-only, and no-substance folds and scorers. Each fold has 189 complete records and zero pending splits. Demotions 6/13/0; spec overrides 0/46/0. All numerical result fields equal the preserved before-state; only the hypothesis wording changes from pre-registered to pre-specified. H1 remains b=2, c=0, exact p=0.5.
- Regenerated V20 tables with explicit output path (the report script default still points to V19). Conventional binary metrics also regenerated unchanged. This closes the replacement adjudication, not the full revision or submission readiness.

## 2026-10-02 — V22 finding-specific adjudication gate (Codex V21-R1 N2)

- **Change:** The score previously ignored the aggregate `_operation_edge` demotion and inferred verification from absence of a negative path verdict. In adjudicated mode, every credited finding now requires an active, non-superseded A2 packet, both required initial records (ADJ1 alone in the strict fold), a resolved affirmative operation/edge judgment, explicit verified verdicts for all triggering paths, and the same cited evidence as the scored unit. Pre-adjudication remains a separate mode. No original adjudication record or checker rule is changed.
- **Granularity:** The aggregate flag loses the identity of the rejected finding. The original ADJ1 records for robust_55e84a6 reject the redraw-member edge but affirm the module/class dependency. A rejected trial that applied the flag to the entire composition spuriously reduced strict C1 5/31 to 4/31. The adopted per-finding gate preserves the independent confirmed findings; the strict count remains 5/31. The rejected trial and explanation are retained in V22 audit evidence, not used as results.
- **Preliminary comparison:** All 126 rows were rescored under each of the pre-adjudication, primary, strict, and no-substance readings. No final state, aggregate, or H1 change was observed. Some uncredited raw findings now correctly carry unverified evidence annotations. Full snapshot/assembly/sensitivity/table regeneration remains the next verification step.
- **History:** Pre-correction scripts and FREEZE/DEVIATIONS copies are retained under historical_boundary/v21_r1/. V21-R1 itself remains unchanged. Amendments are post-outcome corrections, not retrospectively pre-specified.

### V22 N2 follow-up: values and derived row identity

Independent pre-dispatch refutation found that unchanged citation strings alone could let changed trigger values borrow old A2 verification. The gate now binds each triggering encoded value (token membership for list-valued paths), including explicit grant-absence state, to the active packet. A mutation of C3-099 definition hashes now loses cause-correct credit; all archived covered values matched the packet before this repair. Current readings contain 126 pre-adjudication, 126 primary, 129 ADJ1-only, and 126 no-substance rows. Comparing old/new scorers leaves all final states, aggregates and H1 unchanged, but raw evidence annotations and some matched-instance lists differ.

The seven archived score directories were reconciled with the successful offline regeneration. All old files are preserved under historical_boundary/v21_r1/derived_scores/. Five stale pre-adjudication cases and nineteen duplicate filenames in frozen-assembly ADJ1-only output are retained there rather than counted as current output. One stale pre-adjudication row (robust_bb3c7ec) also differs in raw annotations from both the old and corrected scorer reruns, which agree. Neither issue changed the checked aggregate outputs. The wrapper now archives copied input score directories outside its execution tree, rebuilds all seven from empty directories, and requires exact current filename sets, unique case identities and whole-JSON equality. Bare historical scoring.py --write expects a clean directory and is not the validated reproduction entry point.

## 2026-10-02 — Pairwise inference scope correction after outcomes

The protocol explicitly excluded ECM–NT and ECM–SV tests, but the manuscript described the implementation as excluding all structurally nested pairs. DQ reuses DI raw findings, and SV has no cause-correct matching class. The revised report additionally suppresses DI–DQ and all remaining SV exact tests, preserving all b/c/both/neither counts. H1 is unchanged. Metadata now separates raw_rule_inclusion_scope from inference_excluded and exclusion_basis. ECM–NT raw inclusion applies only to PAIR/CONCURRENT; inclusion on evaluated upgrades is observed, not guaranteed. Method-specific A2 decisions need not preserve raw-rule inclusion. No claim of superiority is drawn from the excluded comparisons. This is a post-outcome reporting correction, not an amendment to the historical protocol.

The prior implementation, tests, generator, manifest, deviations, seven result references and all table fragments are retained under historical_boundary/v22_before_pairwise_correction/. Every difference from that boundary was checked: only pairwise inference metadata/p-values changed (alongside the five already disclosed historical pre-adjudication wording differences); all 888 current per-case JSON records, H1 and paired counts are identical. Exactly four of the 44 generated table fragments change. The separate N2 unchanged-results claim refers to its old/new scorer comparison before this reporting correction.

## 2026-10-02 — post-outcome documentation and generated-report consistency correction

The next revision explicitly interprets the current analysis as exploratory after the previously recorded assembly canonicalizations and substance question. This interpretive decision does not change the pre-specified H1, any labels, case states, counts, or numerical readings. Historical protocol and earlier interpretations remain archived.

NT comments now distinguish the shared nominal rule on ordinary edges from UPGRADE dispatch. The QoS literal helper documents that its deadline branch recognizes only the token, not the numeric value or units; no deadline value occurs in the 2,144 observed nonpilot ports. The canonicalizer docstring now describes the actual four scale-pair comparisons. No executable checker or scorer logic changes. The strict-adjudicator fold is labelled one-sided because newly admitted exclusions lack scored outcomes. Two generated fragment labels change without numeric changes.

Two embedded report copies were stale even though the preceding wrapper verified results, per-case records and table fragments. report/numbers.json retained older pairwise metadata and32 now-excluded p-values, plus one historical hypothesis string. report/binary_metrics.json retained20 outdated source hashes; its metric values are unchanged. Both reports are refreshed from full source-tree materialization, retaining all7 submodule-task records. The wrapper now compares complete regenerated report objects and validates every binary source hash, closing the missing report-level check. Original report copies and pre-change code/freeze history are preserved under historical_boundary/v22_r1/. No old research record is rewritten.

The standalone current-paper plotting source has portable input/output arguments and matches the existing figure pixels; historical plotting source remains preserved. No model generation or runtime experiment was rerun for these corrections.

### V23 report-gate independent refutation

The first draft wrapper compared report objects with Python equality, which conflates Boolean and numeric values, and inherited existing reports could conceal a no-op generator. The corrected wrapper compares types and key presence recursively, preserves inherited reports outside the execution tree, and requires both reports to be regenerated. Eight bounded regression tests exercise scalar/key mutations, hash/source loss, and partial/no report writes. This changes verification only, not any checker, scorer, generator, research record, or numerical result. The first V23 reproduction receipt applies to the preceding wrapper; a new complete run is required for this version.
