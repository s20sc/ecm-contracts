# V40 原9指针完整trigger静态语义复核

UTC 2026-10-07T22:23:44.998411+00:00

9个原alias直接复用，未再定位路径。每实例结果：VERIFIED3（rclcpp1、tf2重复2），UNRESOLVED6（MAVLink5、rqt_plot1），REFUTED0。VERIFIED仅指本报告指定的声明变化/消费者引用成员谓词；不是原bug标签的人类真值或执行结果。原ledger9个UNVERIFIED仍原样。

| Case | Instance status | Static conclusion | Remaining boundary |
|---|---|---|---|
| C3-106 (5 pointers) | UNRESOLVED | common.xml→standard.xml、生成器每XML namespace、consumer common::msg参数形成强静态生成链 | 未闭合实际生成header及transitive alias/include/toolchain，未验证实际编译。 |
| C3N-008 (1 pointer) | VERIFIED | add_node从const-reference变by-value；MockExecutor override和base调用确实引用此API | line210是另一Node重载；真正差异在198–202/198–200。GTE生成macro/历史安装版本未执行验证，且31→30.1.5是反向skew。 |
| robust_0481047 (2 duplicate pointers) | VERIFIED | _allFramesAsDot零参→double默认0，consumer通过继承BufferCore的Buffer无参调用 | 新默认参数保留源码call arity兼容，不能声称重编译必失败；原credit为已有libtf.so的ABI断裂，未实查binary符号/链接。 |
| robust_55e84a6 (1 pointer) | UNRESOLVED | oldqualified module缺失、类搬到data_plot；consumer原import/subclass存在 | stored报AttributeError缺autoscroll，不是import失败。backend无autoscroll、wrapper有、provider会调用；旧import如何达到该runtime路径需installed/mixedmodule证据，classrelocation单token不证明整个exception。 |

检查了原始定义、消费者完整调用/继承/override上下文和旧新差异，并按manifest逐文件核SHA。MAVLink还静态扫描两task全部message_definitions/v1.0/*.xml目标消息定义；没有执行generator。assemble.py155–214表明changed_fields是canonicalized声明/显式absence差，consumer_reads来自references；checker165–176只对两集合交集发field_break。因此，集合成员可以成立而某种实际client行为仍兼容，尤其tf2默认参数的重编译情景。

没有据此改分、改primary/control labels或为某个compatible change补实验。C3N普通call的参数转换兼容不否定override的类型失配；tf2 source-call兼容不否定旧binary ABI场景；MAVLink wire message保留不等于C++qualified symbol保留；rqt同名backendclass保留不等于旧Pythonmodule路径兼容。

semantic-receipt.json给逐实例verified/unresolved、exact source SHA/ranges/excerpts、S1/S2来源及限定。仅写本scratch；没有V40、原source、原receipt或其他audit写入；不读其他在审report，不向native席共享。模型阅读不是humanreference，也不给科学Accept。
