# ECM Contracts

A contract-based interface model for **embodied capability modules**, together with
the empirical harness used to evaluate it.

An embodied robot is increasingly assembled from independently developed
capability modules (perception, planning, control, skills) that are installed,
upgraded, and composed at runtime. Whether two such modules can be safely wired
together, or whether an upgrade silently breaks a downstream consumer, is decided
by properties that a plain message-type (schema) check cannot see. **ECM Contracts**
describes each module interface along six dimensions and checks composition and
upgrade safety against them:

| Dim | Name       | What it captures |
|-----|------------|------------------|
| Sig | Signature  | message type, coordinate frame, physical units |
| Beh | Behavioral | QoS (reliability / durability / deadline), publish rate, pre/postconditions |
| Res | Resource   | exclusive resource ownership (e.g. a single writer to `/cmd_vel`) |
| Perm| Permission | required vs granted permission boundaries and limits |
| Rec | Recovery   | recovery-strategy compatibility |
| Ver | Version    | documented named-entity changes (a renamed/removed/relocated topic, service, parameter, message field, class, or API symbol that a consumer still reads) |

The checker is *frozen* (its hash is pinned in `checker/FROZEN.md`) before any
contract is reconstructed and before any per-case scoring, so it cannot be fitted
to the evaluation cases.

## Layout

```
ecm-contracts/
├── reproduce.py          One-command reproduction harness
├── checker/              The frozen 6-dimension contract checker
│   ├── contract_checker.py   checks + four methods (ECM-full + 3 honest baselines)
│   ├── canonical.py          canonicalizes free-text frames/units into comparable tokens
│   ├── selftest.py           per-dimension self-test (asserts each baseline contrast)
│   └── FROZEN.md             the pinned hash + freeze discipline
├── scoring/              Evaluation drivers
│   ├── canonical_scores.py   single scoring pass -> recall / per-dim / stats tables
│   ├── stats.py              Wilson 95% CIs + exact McNemar tests
│   ├── score_corpus.py       score the ROS2 corpus (incl. negative controls)
│   ├── build_cases.py / build_library.py / extract_robust.py   provenance tooling
│   └── gen_ledger.py         per-case provenance ledger
├── data/                 Corpus + results (JSON)
│   ├── robust_cases.json     integration-relevant cases mined from ROBUST
│   ├── scoreable_cases.json  the interface-property-scoreable subset (32 scored)
│   ├── cases.json            the screened ROS2 corpus (16 scored after exclusions)
│   ├── contract_library.json reconstructed module contracts
│   ├── kappa_sample.json / kappa_blind.json / rater2.json / kappa_result.json
│   └── canonical_numbers.json  regenerated headline numbers
├── reconstruction/       Independent re-derivation of the scored wins (see below)
│   ├── interface_provenance.json            per-field public-source provenance
│   ├── independent_reconstruction_core.json validated-core re-derivation
│   ├── win_reconstruction_agreement.json    all-wins agreement summary
│   ├── win_reconstruction_detailed.json     per-win re-derived fields + sources
│   └── targeted_replication.json            targeted replication (admitted + excluded)
├── runtime/              Live ROS2 runtime confirmations
│   ├── demo_qos.py           QoS reliability mismatch (BEST_EFFORT pub -> RELIABLE sub)
│   ├── demo_res.py           resource conflict (two writers to /cmd_vel)
│   ├── run_res_conflict.sh   resource conflict via the ros2_control resource manager
│   ├── res_robot.urdf / res_controllers.yaml   minimal ros2_control system for it
│   ├── frame_mismatch.py     signature/frame mismatch through the real tf2 stack
│   ├── cm.log                a recorded controller-manager rejection
│   └── box_setup/README.md   how the runtime host was built (Ubuntu 22.04 + ROS2 Humble)
└── tables/               LaTeX tables emitted by the scoring pass
```

## Requirements

- **Checker + scoring + `reproduce.py`:** Python 3.8+, standard library only.
  No third-party packages, no network. The derived `data/*.json` are included, so the
  headline numbers reproduce without the upstream datasets.
- **`runtime/` confirmations:** ROS2 Humble. The QoS and `/cmd_vel` demos use `rclpy`
  (plus Gazebo + `turtlebot3_gazebo` for `/cmd_vel`); the `ros2_control` resource
  conflict uses the `ros2_control` resource manager over a mock hardware interface
  (no Gazebo); the frame mismatch uses `tf2`. See `runtime/box_setup/README.md`.

## How to reproduce

```bash
python3 reproduce.py
```

This runs the frozen-checker self-test, regenerates every reported number with a
single scoring pass, runs the statistical inference, and prints the headline
results. It is offline and uses only the standard library. LaTeX tables are written
to `./tables/`.

## What the numbers mean

On real, documented integration bugs the six-dimension contract checker predicts
**10/32 (31%)** on the ROBUST substrate and **10/16 (62%)** on the screened ROS2
corpus, versus at most **19%** for the strongest schema+QoS and semver baselines
(plain message-type matching plus full DDS QoS compatibility, i.e. everything ROS2
gives for free). The advantage is statistically significant by an exact McNemar test
(**p = 0.0078** on ROBUST, **p = 0.016** on ROS2; both discordant counts are
one-sided, b=8/c=0 and b=7/c=0). On matched good-composition negative controls (each
bug neutralized to a compatible twin) the checker raises **0/16 false positives**, so
the recall gain is not bought with over-rejection. As a stronger control that blanks no
field, for six bugs with a documented fixing commit we reconstruct the **real post-fix**
interface (`reconstruction/real_postfix_controls.json`): the checker accepts five and
flags one (`on_init`), a name-granularity false positive of the version rule that we
report rather than tune away.

The predictive value is concentrated where the conflict is interface-self-evident:
the **resource** dimension (the cleanest win that every baseline misses) and the
**version** dimension restricted to documented named-entity changes. The behavioral
QoS sub-check is co-detected by the schema+QoS baseline and is reported as such; the
permission and recovery dimensions are forward-looking and are not counted toward the
measured margin. Gold dimensions are assigned by mapping each bug's third-party
fault-code taxonomy through a fixed crosswalk, independently of whether the checker
flags the case; a blind second rater labelled the 32 ROBUST cases for **Cohen's
kappa = 0.57** (moderate).

## Independent reconstruction of the scored wins

Because the contract fields were reconstructed by the authors, the central threat is
that a scored win could encode the documented answer rather than predict it. To test
this, every case the checker scores as a win was **independently re-derived from the
public artifacts** (message/service/action definitions, controller configs, version
diffs, API headers, QoS profiles) by an agent blind to both the failure record and
the authors' encoding; the frozen checker was then re-run on the re-derived fields.
All **20 retained wins** were corroborated, each citing a concrete public source
(`reconstruction/win_reconstruction_detailed.json`). The process also produced
**three adverse corrections** that *lowered* the reported numbers:

- a dual-arm `ros2_control` case re-derived as two arms claiming *disjoint* per-joint
  interfaces (an unscoped implementation bug, not an interface resource conflict) and
  is now counted as a miss;
- a Nav2 frame case re-derived with matching default frames and was demoted from the
  replication set;
- the one ROS2 signature win re-derived as a constructed archetype of a frame-mismatch
  class rather than a specific documented instance and was excluded.

The independent reconstruction here is agent-based; a full second-team human
reconstruction of the entire corpus remains the strongest open validation.

## Runtime confirmations

Three predicted failures are confirmed live in ROS2:

- **QoS incompatibility** (Beh): a `BEST_EFFORT` publisher feeding a `RELIABLE`
  subscriber delivers **0/80** messages over five runs, while the matched
  `RELIABLE -> RELIABLE` pair delivers **79/80**.
- **Resource conflict** (Res): two `ForwardCommandController`s both claiming the
  `joint1/position` command interface make the `ros2_control` resource manager reject
  the second with `Command interface 'joint1/position' is already claimed`
  (`runtime/cm.log`); the `/cmd_vel` multi-writer demo shows the same conflict on a
  TurtleBot3 (forward progress collapses from 0.37-0.77 m to 0.02-0.08 m).
- **Signature/frame mismatch** (Sig): a point declared in `base_link` but consumed as
  `camera`, transformed through the real `tf2` stack, lands **1.30 m** from where a
  frame-ignoring consumer would act.

## Citation

```bibtex
@misc{ecmcontracts,
  title  = {ECM Contracts: Contract-Aware, Versioned, and Governable Capability Interfaces for Embodied Agents},
  year   = {2026},
  note   = {Reproducibility artifact},
  url    = {https://github.com/s20sc/ecm-contracts}
}
```
