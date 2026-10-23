# AI协作记录

工具与模型：# AI协作日志 现代交换仿真实验
> 记录范围：11.3 ~ 11.11，包含提示、报错、方案、采纳/修正理由

## 记录1：serve_circuit 固定时隙电路交换函数
- 用户提示：实现 serve_circuit，按tick%users选择对应用户队列，只服务该用户；payload不能修改；报文发完才加入completed
- AI输出：按tick取对应队列、循环扣减remaining_wire_bits、发完popleft
- 运行结果：单元测试通过
- 采纳理由：符合AC01固定时隙预留规则，其他用户即使有数据也不能抢占当前时隙，和手工推演一致

## 记录2：serve_packet FIFO分组交换函数（重点约定）
- 用户提示：实现 serve_packet；**remaining_wire_bits入队时已经包含包头，函数内部禁止再加包头**；全局一条共享队列，队首发完才处理下一个
- AI输出：单FIFO循环、预算递减、只扣减remaining_wire_bits
- 运行结果：test_packet 4项测试全部PASS
- 采纳理由：遵守AC03包头口径约定，避免重复叠加包头造成比特统计错误；和6.2两用户案例手算匹配

## 记录3：summarize 指标统计（第一轮报错）
- 用户提示：实现summarize，做payload守恒校验；无完成记录时mean/max时延返回None；loss_ratio、利用率按公式计算
- AI初稿：直接使用 raw["generated"]，用列表遍历求和
- 报错：`KeyError: 'generated'`
- 修正决策：查看测试输入结构，raw里面是预计算好的数值键 `generated_payload_bits`，不是列表；改为直接读取数值
- 结果：解决KeyError，守恒校验可以正常触发

## 记录4：summarize 指标统计（第二轮报错）
- 用户提示：修复后继续测试时延部分
- AI初稿：`p.delay_ticks`，把completed内元素当成对象
- 报错：`AttributeError: 'dict' object has no attribute 'delay_ticks'`
- 修正决策：completed里面每一条记录是字典，改成 `p["delay_ticks"]`；保持无数据返回None逻辑不变
- 结果：test_metrics 3项全部PASS
- 采纳理由：匹配测试框架数据结构，时延口径、None标记、守恒校验全部对齐教师测试约束

## 记录5：11.10 自编反例 test_my_case.py
- 用户提示：编写边界反例，每个测试包含输入、手算预期、断言、说明它能捕获什么错误
- AI输出：5组测试：空时隙不可借用、时隙刚好填满、包头只算一次、无时延返回None、守恒破坏抛异常
- 运行结果：5 passed
- 采纳理由：覆盖AC约束的边界场景，能够检验核心逻辑有没有偏离规则，满足实验11.11自拟测试要求

## 记录6：仿真结果分析、报告正文
- 用户提示：按模板写REPORT.md，区分有效载荷利用率和线路忙碌率；解释利用率与时延矛盾的场景、模型局限
- AI输出：完整报告章节，包含手工推演、结果解释、思考题回答
- 调整：按照实验要求增加“满载连续场景分组不一定更优”、“积压不等于丢包”等限定描述
- 采纳理由：贴合实验评分要求，不单纯说分组交换更好，做到基于指标、结合业务场景分析

## 记录7：参数附加分析（results/extra）
- 用户提示：修改包头参数做敏感性实验，保留基线8组数据不动，附加结果放到extra文件夹
- AI建议：修改header_bits，观察payload利用率变化；区分基线与附加实验
- 执行：自行复制脚本、修改参数、单独保存结果
- 采纳理由：满足11.11附加参数分析要求，不污染原始对比数据

## 记录8：通用调试辅助
- 反复出现：IndentationError缩进报错
- AI建议：全部统一使用4空格缩进，不要混用Tab
- 修正：统一代码缩进风格
- 采纳理由：Python语法强制要求，解决收集阶段报错

## 总结一条核心循环 + 一条验证决策（给REPORT.md引用）
1. 核心循环：`serve_packet` 发送循环，以时隙比特为预算，持续发送队首报文、扣减remaining_wire_bits，报文全部发送完毕才移出队列并标记完成；全程不再追加包头。
2. 关键验证决策：summarize时延读取方式，发现completed元素是字典而非对象，从 `.delay_ticks` 修改为 `["delay_ticks"]`；决策目标：保证指标口径和测试框架完全一致，防止时延计算出错。



## 一项真实协作过程

需求与输入：实现 serve_packet，约定 remaining_wire_bits 在报文入队时已经包含包头；函数内不能额外再加包头；共用一条FIFO队列，必须把队首报文发完才处理下一个，返回发送比特和已完成报文列表。

AI建议：用剩余比特预算循环，每次优先发送队首报文，扣减 remaining_wire_bits；报文剩余比特减到0才弹出队列、加入completed；全程不再叠加包头。

我的手算与测试：
输入：cfg.slot_bits=128，一条报文 payload=96bit、header=32bit，入队时 remaining_wire_bits=128；tick预算128bit。
预期：本tick发送128bit，报文发送完成，进入completed。
实际：sent=128，completed包含该报文，报文剩余比特归零。
对应测试名：test_packet_header_counted_once

修正或采纳理由：采纳该实现；即使首次运行就通过基础用例，额外增加边界验证：报文长度大于时隙预算、多条报文排队的场景，确认不会重复增加包头、不会提前弹出未发完的报文，保证和AC03口径一致。

我能解释的核心逻辑：
1. 避免重加包头：包头只在报文入队阶段一次性合并进 remaining_wire_bits，serve_packet只做比特扣除，不做包头追加；
2. 禁止跨报文抢占：FIFO严格队首发完再处理下一条；
3. 积压统计不遗漏：窗口结束还没发完的报文留在队列，归为backlog，不会被当成已交付或者丢包，统计上和delivered、dropped严格区分。
