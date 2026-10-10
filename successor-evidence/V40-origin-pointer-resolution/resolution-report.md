# V40 原始源指针独立定位

2026-10-07T21:35:59.842707+00:00

原账本9个UNVERIFIED指针/4 cases未改变。本receipt确认9个精确basename别名/原行范围，涉及7个源码文件。完整trigger语义仍未验证9项；新增human reference为0。

| Instance | Case | Task | Original pointer | Exact relative path |
|---|---|---|---|---|
| 1 | C3-106 | u0363 | mavgen_cpp11.py:122-124 | pymavlink/generator/mavgen_cpp11.py |
| 2 | C3-106 | u0363 | mavgen_cpp11.py:356-357 | pymavlink/generator/mavgen_cpp11.py |
| 3 | C3-106 | u0363 | mavparse.py:190-192 | pymavlink/generator/mavparse.py |
| 4 | C3-106 | u0362 | standard.xml:115 | message_definitions/v1.0/standard.xml |
| 5 | C3-106 | u0362 | mavgen.py:170-177 | pymavlink/generator/mavgen.py |
| 6 | C3N-008 | u0421 | executor.hpp:210 | rclcpp/include/rclcpp/executor.hpp |
| 7 | robust_0481047 | u0033 | buffer_core.h:54 | tf2/include/tf2/buffer_core.h |
| 8 | robust_0481047 | u0033 | buffer_core.h:54 | tf2/include/tf2/buffer_core.h |
| 9 | robust_55e84a6 | u0080 | setup.py:7 | rqt_plot/setup.py |

多候选已实核：standard.xml两份L115同literal，原S2explicit fullpath与notes排除测试副本；mavgen.py两份只有generator副本具有原L170–177；setup.py22份只有rqt_plot/setup.py在L7逐字匹配原package list，S2packet.package也明确rqt_plot。其余对应task basename唯一。

每个selected/candidate文件实际SHA均匹配当前snapshots.json精确条目，taskdeclared tree pin一致。JSON保留原ledger/S2/manifest JSONPointer、原ref、原值、实际source SHA及完整原范围文本。未重hash整树。

这些是namespace/template、XML basename、消息定义、include-table merge、重载、namespace和package list的源码片段；读出原片段不等于changed_fields成员、完整符号消失、编译失败或消费者收益被验证。原9历史边界保留；既有stage结果不用于此结论。没有pipeline、网络、安装、ROS/GPU、浏览器、ablation或Accept。
