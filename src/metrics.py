"""任务3：补全指标统计。"""
def summarize(raw, cfg):
    """返回字典，键名必须保留：
    payload_utilization=delivered_payload_bits/(cfg.ticks*cfg.slot_bits)
    wire_utilization=wire_sent_bits/(cfg.ticks*cfg.slot_bits)
    mean_delay_ms、max_delay_ms：完成记录的delay_ticks乘cfg.tick_ms；
      无完成记录时两者返回None，不能写0掩盖无送达。
    loss_ratio=dropped_payload_bits/generated_payload_bits；无生成数据时为0。
    backlog_payload_bits：所有未完成记录的原始payload总和，直接取raw对应值。
    只用观察窗口[0,ticks)，不追加排空时间；有效载荷按完整交付记录计数。
    raw['completed']元素含payload_bits、delay_ticks、user。
    要检查generated=delivered+dropped+backlog，不相等抛ValueError。
    """
    generated_payload_bits = raw["generated_payload_bits"]
    delivered_payload_bits = raw["delivered_payload_bits"]
    dropped_payload_bits = raw["dropped_payload_bits"]
    backlog_payload_bits = raw["backlog_payload_bits"]
    wire_sent_bits = raw["wire_sent_bits"]
    completed_list = raw["completed"]

    # 守恒校验
    if generated_payload_bits != delivered_payload_bits + dropped_payload_bits + backlog_payload_bits:
        raise ValueError("payload 比特不守恒")

    total_wire_cap = cfg.ticks * cfg.slot_bits
    payload_utilization = delivered_payload_bits / total_wire_cap
    wire_utilization = wire_sent_bits / total_wire_cap

    # 丢包率
    if generated_payload_bits == 0:
        loss_ratio = 0.0
    else:
        loss_ratio = dropped_payload_bits / generated_payload_bits

    # 时延：completed里面是字典，用[]取值
    delay_list = [p["delay_ticks"] * cfg.tick_ms for p in completed_list]
    if not delay_list:
        mean_delay_ms = None
        max_delay_ms = None
    else:
        mean_delay_ms = sum(delay_list) / len(delay_list)
        max_delay_ms = max(delay_list)

    res = {
        "payload_utilization": payload_utilization,
        "wire_utilization": wire_utilization,
        "mean_delay_ms": mean_delay_ms,
        "max_delay_ms": max_delay_ms,
        "loss_ratio": loss_ratio,
        "backlog_payload_bits": backlog_payload_bits
    }
    return res