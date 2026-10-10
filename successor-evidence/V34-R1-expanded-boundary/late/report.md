# Seven semantic admissions: late source reconstruction and frozen-rule replay

**Coordinator-built / unblinded / late / post-outcome.** These records are a successor evidence supplement, not original S1/S2, independent human labels, new runtime observations, or observed fixed-success controls. The seven records retain the existing semantic boundary; they do not modify primary H1 or the seven-unknown sensitivity audit.

All seven IDs are tracked. Three C1 outcomes remain `undocumented`; four outcomes are failures reported by external issue authors, supported by quotes below. Every specific cause remains unresolved. Full expanded-boundary results are **not complete**: two C1 providers and the C3-053 receiver lack adequate source-bound declarations; revisions/configuration/binary mapping remain missing where stated.

| Case | Outcome basis | Static assembly | ECM / NT / DI / DQ / SV |
|---|---|---|---|
| robust_84264f0 | undocumented (original runtime effect undocumented) | unassessable | unassessable / unassessable / unassessable / unassessable / unassessable |
| robust_b166c93 | undocumented (original runtime effect undocumented) | unassessable | unassessable / unassessable / unassessable / unassessable / unassessable |
| robust_ff581a0 | undocumented (original runtime effect undocumented) | done | accept / accept / accept / accept / accept |
| C3-053 | failure (source-reported issue outcome) | unassessable | unassessable / unassessable / unassessable / unassessable / unassessable |
| C3-127 | failure (source-reported issue outcome) | done | not_supported / not_supported / not_supported / not_supported / not_supported |
| C3-136 | failure (source-reported issue outcome) | done | not_supported / not_supported / not_supported / not_supported / not_supported |
| C3N-006 | failure (source-reported issue outcome) | done | not_supported / not_supported / not_supported / not_supported / not_supported |

`robust_ff581a0` has one matched parameter edge and two missing consumer ports in the selected slice. Its raw `accept` is produced with an empty failure-condition list and unknown contract attributes; it establishes neither coverage nor runtime success. Missing `y/z` references in that slice do not assert package-wide absence.

The other assembled failures use coordinator-selected generic `other` conditions grounded in quoted wrong-value, timeout or delivery behavior. The frozen matching rules have no right-reason rule for this class; `not_supported` is not a runtime-success verdict. `C3-053` keeps the echo receiver static type unknown rather than copying the publisher type.

The pure aggregate is retained in results.json for transparency: four source-reported failures, one unassessable failure, zero observed controls, and zero right-reason detections for every method. Three undocumented C1 records remain explicit in the outcome census and are excluded by the frozen aggregate. These descriptive counts do not establish expanded-boundary detection performance; the aggregate's mechanical statistical fields are not new inferential claims.

The current experiments/pathb_v2/FREEZE.json binds assemble.py, scoring.py, baselines, checker and literal-policy dependencies before importing pure APIs. Only edge_units, score_composition and aggregate are called. No original main entry point, materialization, source fetch, adjudication, primary score write, archive or runtime experiment is invoked.

Validation: eight unittest checks cover explicit outcome census, source quotes/hashes, inadequate-descriptor propagation, empty ports, partial edges, tampered type/rate/absence rejection and original file hashes. `python3 -B -m unittest discover -s successor-evidence/V34-R1-expanded-boundary/late -p test_replay.py -v` passes. Independent code review identified two validator guard gaps: mutable outcome census and incomplete descriptor null/revision/binding policy. Both were corrected with mutation rejection tests; independent code-reviewer re-review closed both warnings, found no new actionable issues, reran all eight tests successfully and confirmed pure recomputation equals saved results. This is automated code/evidence review, not independent human scientific validation.

## Per-case evidence and limitations

### robust_84264f0

- Plugin uses ~visualization namespace and reads visualization/fixed_frame_id; issue requests namespace change. Evidence: `viz_namespace`, `viz_old_read`, `viz_issue`.

- Limitation: No source-bound actual visualization setting/configuration.
- Limitation: No quoted runtime manifestation; outcome remains undocumented.
- Limitation: Retrieved config slice cannot establish package-wide absence.

### robust_b166c93

- Retained old source calls isnan; fixed source calls std::isnan. Issue asks for Indigo backport. Evidence: `kobuki_old`, `kobuki_new`, `kobuki_issue`.

- Limitation: Provider/toolchain interface unknown; no invented standard library version.
- Limitation: No source-quoted original runtime manifestation.

### robust_ff581a0

- Config supplies x/y/z; retained old plugin loads all three variables from x; fixed slice loads y and z from respective keys. Evidence: `ds_config`, `ds_reads`, `ds_fixed`.

- Limitation: Only x has a source-bound matched edge; y/z retained as missing consumer ports in selected slice, not package-wide absence.
- Limitation: No runtime outcome quoted; accept from empty failed conditions cannot establish coverage.

### C3-053

- Retained publisher uses Float32 and -1.0/0.0; negative infinity interpretation follows expression, while issue calls these NaN values. Evidence: `nan_pub`, `nan_expr`.
- Issue reports ros2 topic echo subscriber crash and quoted conversion error. Evidence: `nan_outcome`, `nan_error`, `nan_echo`.

- Limitation: Actual ros2topic receiver static type is null.
- Limitation: Producer revision not proven as exact issue-run revision.
- Limitation: rosidl generated conversion revision/binary mapping not retained.
- Limitation: Specific cause unresolved.

### C3-127

- v3 source uses 25Hz and 100ms transform timestamp offset with lookup timeout 0.5s; tag0.25.8 dependency slices show TFMessage conversion/callback. Evidence: `tf_v3_rate`, `tf_v3_delay`, `tf_v3_send`, `tf_v3_lookup`, `tf_wire_producer`, `tf_wire_consumer`.
- Follow-up reports TF wait timeout; later comment reports forgotten DDS profile setting. Profile XML is not supplied. Evidence: `tf_outcome`, `tf_xml`.

- Limitation: v3 attachment has no repository revision.
- Limitation: tf2 tag0.25.8 dependency slices are late expanded evidence, not original S2.
- Limitation: Original issue30Hz/50ms and v3 25Hz/100ms are distinct source variants.
- Limitation: DDS XML content and exact runtime binding unknown.
- Limitation: Specific cause unresolved.

### C3-136

- Issue excerpt declares Float64 publication and subscription on comm_topic and reports continuing publisher with listener stall; timer follow-up repeats stall. Evidence: `rclcpp_pub`, `rclcpp_sub`, `rclcpp_outcome`, `rclcpp_timer_stall`.

- Limitation: Repository commit revisions and exact reproducer/fix mapping not retained; Dashing distribution label is not a commit.
- Limitation: DDS implementation/default QoS is not an explicit two-sided contract.
- Limitation: Finite-publisher Fast-DDS571 example is distinct and does not explain this continuing-publisher failure.
- Limitation: Specific cause unresolved.

### C3N-006

- Retained header/definition expose interpolate; issue caller invokes it and reports long-way interpolation value. Evidence: `moveit_declaration`, `moveit_definition`, `moveit_call`, `moveit_outcome`.

- Limitation: Caller is issue snippet without repository revision.
- Limitation: API signature is preserved as declaration; it is not encoded as a fabricated ROS msg_type.
- Limitation: Exact issue runtime revision is not proven by fetched parent source.
- Limitation: Specific cause unresolved.

## Verbatim anchors

For JSON issue files, the retained compact file has line1; the quote below is the decoded body excerpt. The exact escaped raw token and JSON pointer are also retained in inputs.json and checked against that file line. This distinguishes verbatim content from JSON serialization.

### viz_namespace

`successor-evidence/V34-R1-expanded-boundary/source/mavros-visualization-broken.cpp:31`.

```text
viz_nh("~visualization")
```

### viz_old_read

`successor-evidence/V34-R1-expanded-boundary/source/mavros-visualization-broken.cpp:41`.

```text
viz_nh.param<std::string>("visualization/fixed_frame_id", fixed_frame_id, "local_origin");
```

### viz_issue

`successor-evidence/V34-R1-expanded-boundary/source/mavros-visualization-issue207.json:1` (JSON pointer `/body`).

```text
Move `~visualization/visualization/xxx` → `~visualization/xxx`.
```

### kobuki_old

`successor-evidence/V34-R1-expanded-boundary/source/kobuki-broken.cpp:276`.

```text
if (isnan(heading_offset) == true)
```

### kobuki_new

`successor-evidence/V34-R1-expanded-boundary/source/kobuki-fixed.cpp:277`.

```text
if (std::isnan(heading_offset) == true)
```

### kobuki_issue

`successor-evidence/V34-R1-expanded-boundary/source/kobuki-issue22.json:1` (JSON pointer `/body`).

```text
Could we have that fix backported to indigo as well?
```

### ds_config

`V34-EMSE/audit/expanded-boundary-source-fetch/mavros-broken-px4_config.yaml:122`.

```text
sensor_position: {x:  0.0, y:  0.0, z:  -0.3}
```

### ds_reads

`V34-EMSE/audit/expanded-boundary-source-fetch/mavros-broken-distance_sensor.cpp:311`.

```text
pnh.param("sensor_position/x", x, 0.0);
			pnh.param("sensor_position/x", y, 0.0);
			pnh.param("sensor_position/x", z, 0.0);
```

### ds_fixed

`V34-EMSE/audit/expanded-boundary-source-fetch/mavros-fixed-distance_sensor.cpp:312`.

```text
pnh.param("sensor_position/y", y, 0.0);
			pnh.param("sensor_position/z", z, 0.0);
```

### nan_pub

`successor-evidence/V34-R1-expanded-boundary/source/nan_publisher.cpp:29`.

```text
publisher_ = this->create_publisher<std_msgs::msg::Float32>("nan", 1);
```

### nan_expr

`successor-evidence/V34-R1-expanded-boundary/source/nan_publisher.cpp:33`.

```text
message.data = -1.0 / 0.0;
```

### nan_outcome

`successor-evidence/V34-R1-expanded-boundary/source/rclpy-issue848.json:1` (JSON pointer `/body`).

```text
The subscriber crashes with the following message:
```

### nan_error

`successor-evidence/V34-R1-expanded-boundary/source/rclpy-issue848.json:1` (JSON pointer `/body`).

```text
make_tuple(): unable to convert argument of type 'object' to Python object
```

### nan_echo

`successor-evidence/V34-R1-expanded-boundary/source/rclpy-issue848.json:1` (JSON pointer `/body`).

```text
ros2 topic echo /nan
```

### tf_v3_rate

`successor-evidence/V34-R1-expanded-boundary/source/geometry2-v3-broadcaster.cpp:18`.

```text
rclcpp::Rate r(25);
```

### tf_v3_delay

`successor-evidence/V34-R1-expanded-boundary/source/geometry2-v3-broadcaster.cpp:25`.

```text
msg.header.stamp = now() - rclcpp::Duration::from_seconds(0.1);
```

### tf_v3_send

`successor-evidence/V34-R1-expanded-boundary/source/geometry2-v3-broadcaster.cpp:27`.

```text
tf_broadcaster_->sendTransform(msg);
```

### tf_v3_lookup

`successor-evidence/V34-R1-expanded-boundary/source/geometry2-v3-listener.cpp:49`.

```text
tmp = tf_buffer_->lookupTransform("odom", "base_link", stamp, rclcpp::Duration::from_seconds(0.5));
```

### tf_wire_producer

`successor-evidence/V34-R1-expanded-boundary/source/tf2-transform_broadcaster.cpp:54`.

```text
tf2_msgs::msg::TFMessage message;
```

### tf_wire_consumer

`successor-evidence/V34-R1-expanded-boundary/source/tf2-transform_listener.cpp:71`.

```text
const tf2_msgs::msg::TFMessage::ConstSharedPtr msg,
```

### tf_outcome

`successor-evidence/V34-R1-expanded-boundary/source/geometry2-comments727.json:1` (JSON pointer `/0/body`).

```text
TF waiting will timeout after 500 ms.
```

### tf_xml

`successor-evidence/V34-R1-expanded-boundary/source/geometry2-comments727.json:1` (JSON pointer `/1/body`).

```text
I forgot that I had specific DDS setting in my `~/.bashrc` (`FASTRTPS_DEFAULT_PROFILES_FILE`)
```

### rclcpp_pub

`successor-evidence/V34-R1-expanded-boundary/source/rclcpp-issue755.json:1` (JSON pointer `/body`).

```text
this->pub_ = this->create_publisher<std_msgs::msg::Float64>("comm_topic");
```

### rclcpp_sub

`successor-evidence/V34-R1-expanded-boundary/source/rclcpp-issue755.json:1` (JSON pointer `/body`).

```text
this->sub_ = this->create_subscription<std_msgs::msg::Float64>("comm_topic", 1000, std::bind(&Listener::callback, this, std::placeholders::_1));
```

### rclcpp_outcome

`successor-evidence/V34-R1-expanded-boundary/source/rclcpp-issue755.json:1` (JSON pointer `/body`).

```text
The publisher works as expected - just keeps publishing messages.
The listener **STOPS** after receiving some messages (random amount).
```

### rclcpp_timer_stall

`successor-evidence/V34-R1-expanded-boundary/source/rclcpp-comments755.json:1` (JSON pointer `/1/body`).

```text
In this case, I will again experience the same problem that the listener stops working at some time.
```

### moveit_declaration

`successor-evidence/V34-R1-expanded-boundary/source/moveit-broken-floating_joint_model.h:60`.

```text
void interpolate(const double* from, const double* to, const double t, double* state) const override;
```

### moveit_definition

`V34-EMSE/audit/expanded-boundary-source-fetch/moveit-broken-floating_joint_model.cpp:132`.

```text
void FloatingJointModel::interpolate(const double* from, const double* to, const double t, double* state) const
```

### moveit_call

`V34-EMSE/audit/expanded-boundary-source-fetch/moveit-issue-1478.json:1` (JSON pointer `/body`).

```text
fjm.interpolate(jv1, jv2, 0.5, intp);
```

### moveit_outcome

`V34-EMSE/audit/expanded-boundary-source-fetch/moveit-issue-1478.json:1` (JSON pointer `/body`).

```text
Note how the interpolated angle has value 0.285: it's taking the long way around, with the interpolation going through 0 instead of Pi/-Pi radians.
```

## Source metadata

- `successor-evidence/V34-R1-expanded-boundary/source/mavros-visualization-broken.cpp`
  URL: https://raw.githubusercontent.com/mavlink/mavros/01055466b1a97a71d2374831a43f276f392fc27d/mavros_extras/src/plugins/visualization.cpp
  Revision: `01055466b1a97a71d2374831a43f276f392fc27d`
  SHA256: `1861af673ee50c394fb0cf19b956128ad46578aac72263b1add9b845b6dc0e8c`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/mavros-visualization-issue207.json`
  URL: https://api.github.com/repos/mavlink/mavros/issues/207
  Revision: `null` (issue/excerpt or attachment, repository revision unknown)
  SHA256: `f3c9a4707920b82b2b54c923781bb9b55887b26113309df5db6f1d93d21e6e37`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/mavros-visualization-config-broken.yaml`
  URL: https://raw.githubusercontent.com/mavlink/mavros/01055466b1a97a71d2374831a43f276f392fc27d/mavros/launch/px4_config.yaml
  Revision: `01055466b1a97a71d2374831a43f276f392fc27d`
  SHA256: `a434bab6a643713c7dcb10f45fe14a4ea4839307734c34d733a0f7f2c06b725d`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/additional-declarations-receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/kobuki-broken.cpp`
  URL: https://raw.githubusercontent.com/yujinrobot/kobuki_core/0.6.3/kobuki_driver/src/driver/kobuki.cpp
  Revision: `0.6.3`
  SHA256: `7ca11de863a864f94e79247bc66b45f81a1268b389e9b8b4b0da7d324ceb62e5`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/kobuki-fixed.cpp`
  URL: https://raw.githubusercontent.com/yujinrobot/kobuki_core/b166c93913e293c55a3faa7b298c5f52f6def964/kobuki_driver/src/driver/kobuki.cpp
  Revision: `b166c93913e293c55a3faa7b298c5f52f6def964`
  SHA256: `e46fd8da8298e646cc4c0b61ae05ca58ee2261deb6bd57c607c993228f8e6da1`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/kobuki-issue22.json`
  URL: https://api.github.com/repos/yujinrobot/kobuki_core/issues/22
  Revision: `null` (issue/excerpt or attachment, repository revision unknown)
  SHA256: `12e38c3018fa17aa831e330af36735568bb6f1bdcafa481a4c48d0e27f4fc581`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/receipt.json`

- `V34-EMSE/audit/expanded-boundary-source-fetch/mavros-broken-px4_config.yaml`
  URL: https://raw.githubusercontent.com/mavlink/mavros/5dd2e1e5742cea77e6b133bca753b4d8f3e404c6/mavros/launch/px4_config.yaml
  Revision: `5dd2e1e5742cea77e6b133bca753b4d8f3e404c6`
  SHA256: `ae2d6f42882473411e20bcf354dfc8a1daf6ba3105838c2b17bbccd286ceaf64`
  Receipt: `V34-EMSE/audit/expanded-boundary-source-fetch/receipt.json`

- `V34-EMSE/audit/expanded-boundary-source-fetch/mavros-broken-distance_sensor.cpp`
  URL: https://raw.githubusercontent.com/mavlink/mavros/5dd2e1e5742cea77e6b133bca753b4d8f3e404c6/mavros_extras/src/plugins/distance_sensor.cpp
  Revision: `5dd2e1e5742cea77e6b133bca753b4d8f3e404c6`
  SHA256: `ec1d082165b11685c41f70acba690f0ff5c336a9707f41e7593898445e223b2e`
  Receipt: `V34-EMSE/audit/expanded-boundary-source-fetch/receipt.json`

- `V34-EMSE/audit/expanded-boundary-source-fetch/mavros-fixed-distance_sensor.cpp`
  URL: https://raw.githubusercontent.com/mavlink/mavros/ff581a0752107f7ad875c16f83f7b75ccd92f847/mavros_extras/src/plugins/distance_sensor.cpp
  Revision: `ff581a0752107f7ad875c16f83f7b75ccd92f847`
  SHA256: `4b71010ba1246d07df30481e432f27fce8059d8169bf3e3b26f0ed52b17a7295`
  Receipt: `V34-EMSE/audit/expanded-boundary-source-fetch/receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/nan_publisher.cpp`
  URL: https://raw.githubusercontent.com/jacobperron/nan_publisher/05a7c39e879e8370123fd47cad921d7b2af7f4eb/src/nan_publisher.cpp
  Revision: `05a7c39e879e8370123fd47cad921d7b2af7f4eb`
  SHA256: `e6bdd5515adbf914ee36035c4d400344c04d3c04d34d0a2a84511efe01a3d09d`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/rclpy-issue848.json`
  URL: https://api.github.com/repos/ros2/rclpy/issues/848
  Revision: `null` (issue/excerpt or attachment, repository revision unknown)
  SHA256: `39ecd35c4d925ab13ea5bb407551aa158627a6548230c14aad0329bbc067a2b3`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/geometry2-v3-broadcaster.cpp`
  URL: https://github.com/user-attachments/files/17727580/tf2_buffer_lag_ros2_v3.zip
  Revision: `null` (issue/excerpt or attachment, repository revision unknown)
  SHA256: `9d07417491f9a1aef55ab286362e92fe197f2d13a5a662b833b15832da32c6a4`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/geometry2-v3-listener.cpp`
  URL: https://github.com/user-attachments/files/17727580/tf2_buffer_lag_ros2_v3.zip
  Revision: `null` (issue/excerpt or attachment, repository revision unknown)
  SHA256: `4898da5ec3c61bb0fc1e287c62332dda1ba617fa24fff65a0b7346176e42e2d0`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/tf2-transform_broadcaster.cpp`
  URL: https://raw.githubusercontent.com/ros2/geometry2/0.25.8/tf2_ros/src/transform_broadcaster.cpp
  Revision: `0.25.8`
  SHA256: `59f5afe5bb58e57523267c4fa02fdc09f0349046b1142e4e553e85baede90dfb`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/additional-declarations-receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/tf2-transform_listener.cpp`
  URL: https://raw.githubusercontent.com/ros2/geometry2/0.25.8/tf2_ros/src/transform_listener.cpp
  Revision: `0.25.8`
  SHA256: `155abeeb400ddf93c5d162183af9e75885fc3b301b616ccbf6e3cc261c236127`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/additional-declarations-receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/geometry2-comments727.json`
  URL: https://api.github.com/repos/ros2/geometry2/issues/727/comments?per_page=100
  Revision: `null` (issue/excerpt or attachment, repository revision unknown)
  SHA256: `a1b2d84e5310aa7a9c8d7681aee0816b62d9cbf83c2f5eaff1bfdefe57afd7dc`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/rclcpp-issue755.json`
  URL: https://api.github.com/repos/ros2/rclcpp/issues/755
  Revision: `null` (issue/excerpt or attachment, repository revision unknown)
  SHA256: `fd68938d291d7a3770b5b72bd3fd467b8449d1a97d1fd2c841e2abfaa087992c`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/rclcpp-comments755.json`
  URL: https://api.github.com/repos/ros2/rclcpp/issues/755/comments?per_page=100
  Revision: `null` (issue/excerpt or attachment, repository revision unknown)
  SHA256: `9c1a2b0e96edf10e0ff5432d7c0a1b6cb522fa20174e03963be84d25832270e6`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/receipt.json`

- `successor-evidence/V34-R1-expanded-boundary/source/moveit-broken-floating_joint_model.h`
  URL: https://raw.githubusercontent.com/moveit/moveit2/14489f904c44f2c184660ba2d50bd50119a2235e/moveit_core/robot_model/include/moveit/robot_model/floating_joint_model.h
  Revision: `14489f904c44f2c184660ba2d50bd50119a2235e`
  SHA256: `f9e414da7154ff375966082e53b01b8a55ad171df9f17f97ecae1ddcd82d4479`
  Receipt: `successor-evidence/V34-R1-expanded-boundary/source/additional-declarations-receipt.json`

- `V34-EMSE/audit/expanded-boundary-source-fetch/moveit-broken-floating_joint_model.cpp`
  URL: https://raw.githubusercontent.com/moveit/moveit2/14489f904c44f2c184660ba2d50bd50119a2235e/moveit_core/robot_model/src/floating_joint_model.cpp
  Revision: `14489f904c44f2c184660ba2d50bd50119a2235e`
  SHA256: `a02e1c9f40506bde792de71c0688e92ac1cc35e938ad4f5ab4dd42cd30b6c721`
  Receipt: `V34-EMSE/audit/expanded-boundary-source-fetch/receipt.json`

- `V34-EMSE/audit/expanded-boundary-source-fetch/moveit-issue-1478.json`
  URL: https://api.github.com/repos/moveit/moveit2/issues/1478
  Revision: `null` (issue/excerpt or attachment, repository revision unknown)
  SHA256: `2d876a5040cc11fd55d60b51bb16b248f779277067a60b934a26216ded19a16f`
  Receipt: `V34-EMSE/audit/expanded-boundary-source-fetch/receipt.json`

## Frozen rule binding

```json
{
  "assemble.py": "40907dd6b6f4410c89437d788e732e317ffb6801c05c4e54e6f9ee1d8026d5e1",
  "scoring.py": "c671d88baf58a64874184d9bdbc5547c12832f80b797138056077bbfdcd50894",
  "baselines_v2.py": "0625fca0bc72cc12f29a429fb6851b2335330744fd8a3ae1875b9e10e55a6085",
  "../pathb/checker/contract_checker.py": "e9e0dbbfba9985924717d30265b4200514bb9d442a1429b16a49566e024673bf",
  "../pathb/checker/canonical.py": "52ac4d84e07cb3058c5b93a131e4f28b58c92e5fe83ee63ee334a59d2925e9c3",
  "qos_literal.py": "cca23e2e7986d5f5534354d2225d43be228768389d0b058532c78aa150b7ecfc",
  "frame_literal.py": "3227fe687e973c7cfb49c8cec93914c6b89bab5a4ff4a3f708fd7a374c57553a",
  "FREEZE.json": "7b4a02f3438880d68679e11b7f8a8f795e5d23cf8355a2608523d5cba5df39d9"
}
```
