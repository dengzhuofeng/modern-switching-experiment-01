"""11.10 自编反例/边界测试：基于6.2节两用户案例的手算预期"""
from collections import deque

import pytest

from src.metrics import summarize
from src.models import Config, Pending
from src.part1_circuit import serve_circuit
from src.part2_packet import serve_packet


def make_cfg():
    # 6.2节参数：2用户，tick=1ms，时隙128bit，包头32bit
    return Config(users=2, ticks=2, slot_bits=128, tick_ms=1,
                  header_bits=32, buffer_payload_bits=4096)


# ---------- 反例1：固定时隙，空时隙不能借给别的用户 ----------
def test_circuit_empty_slot_not_borrowable():
    cfg = make_cfg()
    # 输入：tick=0，0%2=0轮到用户0；用户0队列空，用户1有96bit记录(含包头128bit)
    pkt = Pending(user=1, arrival_tick=0, payload_bits=96, remaining_wire_bits=128)
    queues = [deque(), deque([pkt])]

    sent, completed = serve_circuit(queues, 0, cfg)

    # 手算预期：时隙空着，用户1不能抢用 → 发送0bit，无完成
    assert sent == 0, "固定时隙下空时隙不能被其他用户借用"
    assert completed == [], "本tick无记录可发，不应有完成记录"
    assert pkt.remaining_wire_bits == 128, "未发送的记录remaining不应变化"
    # 断言为何成立：serve_circuit只允许服务tick%users对应队列（AC01），
    # 其他队列即使有数据也不能占用本时隙，否则第一个断言会失败。


# ---------- 反例2：电路交换包头+payload填满一个时隙 ----------
def test_circuit_full_slot_one_tick():
    cfg = make_cfg()
    # 输入：tick=1，1%2=1轮到用户1，一条96bit记录(remaining=96+32=128)
    pkt = Pending(user=1, arrival_tick=0, payload_bits=96, remaining_wire_bits=128)
    queues = [deque(), deque([pkt])]

    sent, completed = serve_circuit(queues, 1, cfg)

    # 手算预期：128bit正好占满时隙，tick内发完，时延=1ms
    assert sent == 128, "包头+payload应恰好填满128bit时隙"
    assert len(completed) == 1, "整条记录发完才计入完成"
    assert pkt.payload_bits == 96, "payload_bits是有效载荷，全程不允许修改"


# ---------- 反例3：分组交换包头只初始化一次，函数内不得再加 ----------
def test_packet_header_counted_once():
    cfg = make_cfg()
    # 输入：入队时remaining_wire_bits=payload+header=96+32=128（包头已包含）
    pkt = Pending(user=0, arrival_tick=0, payload_bits=96, remaining_wire_bits=128)
    queue = deque([pkt])

    sent, completed = serve_packet(queue, 0, cfg)

    # 手算预期：128bit刚好一个时隙发完，1个tick交付
    assert sent == 128
    assert len(completed) == 1
    # 断言为何成立：AC03包头只初始化一次；
    # 若函数错误地再+32bit包头，remaining=160>128预算，本tick发不完，
    # completed为空，第二个断言会失败——这就是反例的作用。


# ---------- 反例4：无完成记录时，时延必须是None不是0 ----------
def test_summarize_no_delivery_delay_none():
    raw = {
        "generated_payload_bits": 0,
        "delivered_payload_bits": 0,
        "dropped_payload_bits": 0,
        "backlog_payload_bits": 0,
        "wire_sent_bits": 0,
        "completed": [],
    }
    r = summarize(raw, make_cfg())
    # 手算预期：没有任何完成记录 → 平均/最大时延=None，丢包率=0
    assert r["mean_delay_ms"] is None
    assert r["max_delay_ms"] is None
    assert r["loss_ratio"] == 0
    # 断言为何成立：None表示"无送达"，不能写0掩盖无数据，AC09口径


# ---------- 反例5：payload守恒，不相等必须抛ValueError ----------
def test_summarize_conservation_violation():
    raw = {
        "generated_payload_bits": 400,
        "delivered_payload_bits": 200,
        "dropped_payload_bits": 100,
        "backlog_payload_bits": 99,   # 400 != 200+100+99，故意破坏守恒
        "wire_sent_bits": 320,
        "completed": [],
    }
    with pytest.raises(ValueError):
        summarize(raw, make_cfg())
    # 断言为何成立：守恒等式是硬校验，不满足必须抛异常，
    # 否则指标统计会被"凭空消失/多出的比特"污染。
