# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Chinese note generated from the summary.

Intervals are described. Monte Carlo counts are not rewritten as exact
p-values or as p < 0.0001. Holm is mentioned only for the two
zero-difference proportions, and not as a test of the 0.02 margin.
"""

from __future__ import annotations

from typing import Any

LOCATION_TEXT = {
    "interval_includes_zero": (
        "百分位区间包含 0。这只说明区间的位置。没有做等效性检验，"
        "不能写成两种方法等效，也不能写成已经检出差异或没有检出差异。"
    ),
    "interval_entirely_below_minus_margin": (
        "百分位区间整体落在小于或等于 -0.02 的一侧。0.02 只是阅读幅度的参照，"
        "不是被 Holm 检验过的阈值。"
    ),
    "interval_below_zero": (
        "百分位区间整体在 0 下方，但没有整体落在 -0.02 之外。"
        "0.02 只是阅读参照，不是假设检验的对象。"
    ),
    "interval_entirely_above_margin": (
        "百分位区间整体落在大于或等于 0.02 的一侧。0.02 只是阅读幅度的参照，"
        "不是被 Holm 检验过的阈值。"
    ),
    "interval_above_zero": (
        "百分位区间整体在 0 上方，但没有整体落在 0.02 之外。"
        "0.02 只是阅读参照，不是假设检验的对象。"
    ),
    "unclassified": "区间落在未单独命名的边界上，只报告数字。",
}


def _num(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _mc_sentence(block: dict[str, Any]) -> str:
    count = int(block["extreme_count"])
    trials = int(block["mc_n"])
    low, high = block["mc_proportion_wilson95"]
    sentence = (
        f"重中心化聚类 bootstrap 的极端次数是 {count}/{trials}。"
        f"这不是精确的 p，也不能写成 p<0.0001。"
        f"该蒙特卡洛比例的 Wilson 95% 区间是 [{_num(low)}, {_num(high)}]，"
        "它只描述有限次重抽样本身的不确定性，不是 Brier 差的区间。"
    )
    if "holm_mc_proportion" in block:
        if count == 0:
            adjusted = (
                f"Holm 作用在这组零差值对照的蒙特卡洛比例上；"
                f"调整后的点比例对应极端次数仍是 0/{trials}，"
                "这个点不是精确的 0，也不是 p<0.0001。"
            )
        else:
            adjusted = f"Holm 调整后的蒙特卡洛比例是 {_num(block['holm_mc_proportion'])}。"
        sentence += " " + adjusted + "Holm 不调整百分位区间，也不检验差是否超过 0.02。"
    return sentence


def _contrast_paragraph(title: str, block: dict[str, Any]) -> str:
    return (
        f"### {title}\n\n"
        f"配对 Brier 差（前者减后者，越低越好）点估计 {_num(block['estimate'])}。"
        f"探索性百分位区间 [{_num(block['ci95_low'])}, {_num(block['ci95_high'])}]，"
        f"宽度 {_num(block['ci_width'])}。单年的周聚类没有去掉季节性，相邻周仍可能相关，"
        "所以这个区间只是探索性描述。\n\n"
        f"{_mc_sentence(block)}\n\n"
        f"{LOCATION_TEXT.get(str(block.get('interval_location')), str(block.get('interval_location')))}\n"
    )


def render_explanation(summary: dict[str, Any]) -> str:
    task = summary["task"]
    holdout = summary["holdout"]
    primary = summary["study_primary"]
    inventory = summary["inventory"]
    lines = [
        "# 实验说明",
        "",
        "本文由 `research/explain.py` 根据 `score_summary.json` 生成。",
        "这是天气网格上的回顾记录，标为 out_of_scope：它不回答人的行为、选择或互动，也不能换成人物预测的结论。",
        "",
        "四臂模型实验没有运行。OASIS 群体仿真没有接通。",
        "臂 A 若要运行，也只是聊天补全基线，不是原版 MiroFish。",
        "这是探索性研究，不是预测保证。不用于医疗、博彩或投资决策。",
        "本结果不是“玄学已被科学验证”的证据。工程链路正确不等于预测正确。",
        "目前没有四臂结算，也没有已发生并结算的前瞻事件，不能说预测更准。",
        "这是预设代码分割的回顾性评估，研究者选择泄漏未排除。",
        "没有外部时间证据证明研究者从未看过 2023 年的降水，或没有试过别的映射。",
        "不能写成看数据前确定、真正未触碰留出集，或已经完成预注册验证。",
        "P-MAP-1 是工程假设 (阳爻数+1)/8，不是古法给出的概率，也不是有传统依据的预测模型。",
        "同月符号对照只有一条固定置换，不是完整置换分布。下面的区间没有包含这条置换本身的随机性。",
        "历史回放和 prospective_v2 是分开的目录。旧 future_ledger.jsonl 已标为 invalid/excluded。",
        "",
        "## 主终点",
        "",
        f"状态：{primary['status']}。",
        primary["reason_zh"],
        "主终点（聊天基线臂 A 与规则文本臂 B 的配对 Brier 差）本次未估计。臂 A 不是原版 MiroFish。",
        "",
        "## 任务",
        "",
        f"问题：{task['question_template']}",
        f"先导期 {task['pilot_start']} 至 {task['pilot_end']}，留出集 {task['holdout_start']} 至 {task['holdout_end']}。",
        (
            f"结算来源：{task['settlement']}。这是 Open-Meteo 归档网格，不是气象站实测。"
            "请求没有固定 models 参数，模型版本未锁定。"
            f"请求坐标 ({task['requested_latitude']}, {task['requested_longitude']})，"
            f"快照返回网格 ({task['returned_grid_latitude']}, {task['returned_grid_longitude']})。"
            f"缺测条数为 {holdout['n_unresolved']}。空值保持为空，没有把缺测填成 0。"
            f"阈值 {task['threshold_mm']} 毫米。"
        ),
        f"评估标签：{summary['evaluation_label_zh']}。样本类别：{summary['sample_class']}。",
        "",
        "## 留出集计数",
        "",
        (
            f"日期 {holdout['n_dates']} 天，已结算 {holdout['n_resolved']} 条，"
            f"缺测条数为 {holdout['n_unresolved']}，失败率 {_num(holdout['failure_rate'])}。"
        ),
        (
            f"结局发生率 {_num(holdout['outcome_rate'])}。ISO 周 {holdout['cluster_count']} 个。"
            f"主体数 {holdout['subject_count']}。相同结构卦涉及的事件数 {holdout['identical_cast_collision_events']}。"
        ),
        "智能体数不是样本量。",
        "",
        "## 概率与校准",
        "",
    ]
    for name, block in summary["probabilities"].items():
        lines.append(
            f"- {name}：平均 Brier {_num(block['mean_brier'])}，平均概率 {_num(block['mean_p'])}，"
            f"ECE {_num(block['ece'])}，平均概率减发生率 {_num(block['calibration_in_the_large'])}。"
        )
    lines.extend(
        [
            "",
            "分箱见摘要。百分位区间的频率学覆盖率不能由这一次样本估计。",
            "",
            "## 离线对照",
            "",
            "这些数字执行的是规则映射和评分器。它们不代替未运行的四臂，也不能说预测更准。",
            "",
            _contrast_paragraph("规则映射减常数基率（探索性参照，不是研究主终点）", summary["contrasts"]["rule_minus_base_rate"]),
            _contrast_paragraph("规则映射减农历月基线（零差值家族之一）", summary["contrasts"]["rule_minus_calendar"]),
            _contrast_paragraph("规则映射减单次同月置换（零差值家族之一）", summary["contrasts"]["rule_minus_symbol_control"]),
            _contrast_paragraph("农历月基线减常数基率（只作描述，不进 Holm）", summary["contrasts"]["calendar_minus_base_rate"]),
            "## 花费",
            "",
            (
                f"模型调用 {summary['cost']['model_calls']} 次，"
                f"prompt tokens {summary['cost']['prompt_tokens']}，"
                f"completion tokens {summary['cost']['completion_tokens']}。"
                "没有模型账单。等字节不是等 token；四臂未运行，token 预算没有实际测量。"
            ),
            "",
            "## 清单",
            "",
            "已跑：" + "、".join(inventory["ran"]),
            "",
            "未跑：" + "、".join(inventory["not_run"]),
            "",
            "待结算：" + "、".join(inventory["pending_settlement"]),
            "",
            "## 规则与映射",
            "",
            summary["rule_note_zh"],
            "",
            "## 限制",
            "",
        ]
    )
    for item in summary["limitations_zh"]:
        lines.append(f"- {item}")
    lines.extend(["", "协议哈希：" + summary["protocol_sha256"], ""])
    if summary.get("synthetic_pipeline_only"):
        lines.extend(
            [
                "这份输出使用合成降水量，只证明链路能跑通。不能用来声称预测提升，也不能当成真实天气实验。",
                "",
            ]
        )
    return "\n".join(lines)
