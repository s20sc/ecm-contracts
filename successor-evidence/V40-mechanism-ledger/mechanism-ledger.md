# V39 primary mechanism ledger

UTC 2026-10-07T21:10:49.096798+00:00

只读独立逐案账本，未运行scorer aggregate/main、整套复现或pytest；未改spec、labels、assembled或scores。活动实现为V32 replication_package。所有标签与A2 source裁决仍是模型产物，不是独立人类真值。

- Primary failures=93；各语料={'C2': 12, 'C3': 40, 'C3N': 7, 'C1': 34}。93条各有spec/score/assembly pointer及SHA。
- ECM causecredits=14；各语料={'C2': 3, 'C3': 3, 'C3N': 2, 'C1': 6}。操作={'PAIR': 1, 'UPGRADE': 13}；维度={'Sig': 1, 'Beh': 0, 'Res': 0, 'Perm': 0, 'Rec': 0, 'Ver': 13}。
- 每个credit连接failed condition/class/element、实际MATCH tuple、score finding/matched pointer、assembled单位encoding、逐触发值provenance、active A2 packet与三角色model record/operation/value verdict。
- Platform-failure-record credits=['B-Sig-02', 'B-Ver-05']；同93失败分母下withheld=12。保留artifact trigger与task原文本/字节SHA。
- H1 E=['C3-093', 'C3-099', 'C3-106']；D=['C3-099']；E-only=['C3-093', 'C3-106']；D-only=[]；both=['C3-099']；neither=37；b=2；c=0；独立exact binomial p=0.5。DQ shared credit仅保留stored finding/matched；scope=PARTIAL_STORED_SCORE_ONLY，未完成definition trigger/A2/source全链追溯。
- Independent C3 frozen order/repo-cap walk matches stored selected flags=True；N从当前scoring AST读取。
- Current precise A2 coverage failures=0；满足record/packet/trigger门不等于label accuracy。
- 13个version matched tokens均在changed_fields与consumer_reads中；移除intersection结构上保留既有field_break。本任务未重跑完整ablation，不能据此宣称benefit、specificity不变或prospective accuracy。type credit不属于consumer-restricted version rule。

## 原始源指针边界

触发值source-pointer实例=68；本轮不能定位读取=9；相关cases=['C3-106', 'C3N-008', 'robust_0481047', 'robust_55e84a6']。A2 source-excerpt中的其他引用也逐项保留。缺失/ambiguity/out-of-range显式UNVERIFIED，不能因模型record写verified而变成原文件已读。
能读取的source/artifact文件保留实际SHA与完整start–end行范围及逐行excerpt；读取字节/范围不等于literal trigger value验证，trigger_value_literal_verified均为false。repo/revision来自task ledger。未重新hash完整snapshot树；declared tree pin与单文件byte hash分开，不声称完整revision认证。

## Credit mechanisms

| Case | Corpus | Class / rule / element | Dim | Platform | Retained after withholding platform-record credits | Active A2 |
|---|---|---|---|---|---|---|
| B-Sig-02 | C2 | nominal_type_mismatch / type_mismatch / topic:/box | Sig | True | False | A2-B-Sig-02-broken-M1-8b8060c4f2 |
| B-Ver-02 | C2 | definition_mismatch / field_break / msg:franka_msgs/FrankaState | Ver | False | True | A2-B-Ver-02-broken-M1-49aadae494 |
| B-Ver-05 | C2 | definition_mismatch / field_break / msg:control_msgs/FollowJointTrajectoryActionResult | Ver | True | False | A2-B-Ver-05-broken-M1-18d32d5b87 |
| C3-093 | C3 | element_retyped / field_break / api:yaml.load | Ver | False | True | A2-C3-093-broken-M1-ab57a4ddb1 |
| C3-099 | C3 | definition_mismatch / field_break / field:rmw_dds_common/Gid.data; element_retyped / field_break / field:rmw_dds_common/Gid.data | Ver | False | True | A2-C3-099-broken-M1-e0bc209998 |
| C3-106 | C3 | element_removed_or_renamed / field_break / api:mavlink::common::msg::GLOBAL_POSITION_INT | Ver | False | True | A2-C3-106-broken-M1-fc5c78bf41 |
| C3N-008 | C3N | element_retyped / field_break / api:rclcpp::Executor::add_node | Ver | False | True | A2-C3N-008-broken-M1-69f63d998f |
| C3N-024 | C3N | element_removed_or_renamed / field_break / api:rclcpp::Duration::Duration(rcl_duration_value_t) | Ver | False | True | A2-C3N-024-broken-M1-77b103d422 |
| robust_0481047 | C1 | element_retyped / field_break / api:tf2::BufferCore::_allFramesAsDot; element_removed_or_renamed / field_break / api:tf2::BufferCore::_allFramesAsDot | Ver | False | True | A2-robust_0481047-broken-M1-66cf574393 |
| robust_55e84a6 | C1 | element_removed_or_renamed / field_break / api:rqt_plot.mat_data_plot.MatDataPlot | Ver | False | True | A2-robust_55e84a6-broken-M1-87b0cd254c |
| robust_9c8abeb | C1 | element_removed_or_renamed / field_break / api:boost::shared_dynamic_cast | Ver | False | True | A2-robust_9c8abeb-broken-M1-6ba8355e6e |
| robust_b826eae | C1 | element_retyped / field_break / api:xacro:schunk_pg70 | Ver | False | True | A2-robust_b826eae-broken-M1-2746ff72e2 |
| robust_bdda1fa | C1 | element_removed_or_renamed / field_break / api:mavros.command.guided_enable; element_removed_or_renamed / field_break / api:mavros.command.guided_enable | Ver | False | True | A2-robust_bdda1fa-broken-M1-df122618ea |
| robust_c0067f9 | C1 | element_removed_or_renamed / field_break / msg:mavros_msgs/WaypointGOTO; element_removed_or_renamed / field_break / msg:mavros_msgs/WaypointGOTO | Ver | False | True | A2-robust_c0067f9-broken-M1-27387c57e6 |

这是source/mechanism追溯材料，不是新增detector实验。独立human reference、真实compatible multi-consumer controls、prospective consumer收益及expanded-boundary完整验证等major gaps均保留；不给Accept。

AG.load_coverage实际读取的所有JSON已按同一字节snapshot记录SHA，包括106个active role records。只声明all listed hashes match；未封存transitive Python import或完整snapshot树。

交付mechanism-ledger.json（93逐案）、credit-case-index.json（14credits）、source-sha256.json（读取source/input SHA）、verification.json。
