# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Chinese experiment note generated from the summary, not from a hand-edited claim."""

from __future__ import annotations

from typing import Any

FLAG_TEXT = {
    "ci_includes_zero_not_equivalence": (
        "95%区间包含 0。这次没有检出差异。协议没有做等效性检验，"
        "所以不能把“没有显著差异”写成两种方法等效。"
    ),
    "lower_brier_entire_ci_beyond_margin": (
        "规则侧的 Brier 更低，而且整段 95%区间都越过了预设最小实际增益。"
        "这只描述这一窗口和这一条映射，不是玄学效应的证实，也不是四臂主终点。"
    ),
    "lower_brier_detectable_but_not_entirely_beyond_margin": (
        "区间在 0 的一侧，但没有整段越过预设最小实际增益。"
        "可以用“检出方向”描述，不能写成已经达到预设的实际增益。"
    ),
    "higher_brier_entire_ci_beyond_margin": (
        "规则侧的 Brier 更高，而且整段 95%区间都越过了预设幅度。"
        "在这一映射和窗口上，规则概率比该参照更差。这同样不是对传统文献的终审。"
    ),
    "higher_brier_detectable_but_not_entirely_beyond_margin": (
        "区间在变差的一侧，但没有整段越过预设幅度。"
    ),
    "unclassified": "区间落在未单独命名的边界上，只报告数字，不另加结论。",
}


def _num(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def _p(value: object, replicates: int | None) -> str:
    if isinstance(value, float) and value == 0.0 and replicates:
        return f"0（{replicates} 次重抽样里没有更极端的结果，应理解为小于 {1 / replicates:.4g}，不是精确的零）"
    return _num(value)


def _contrast_paragraph(title: str, block: dict[str, Any], replicates: int | None) -> str:
    flag = str(block.get("flag"))
    extra = ""
    if block.get("covers_zero") and block.get("wider_than_margin"):
        extra = "区间宽度大于预设的最小实际增益，这次样本分辨不了该幅度的差别，属于证据不足。"
    holm = ""
    if "p_holm" in block:
        holm = f" Holm 校正后的 p 为 {_p(block['p_holm'], replicates)}。"
    p_text = ""
    if "p_unadjusted" in block:
        p_text = f" 未校正 p 为 {_p(block['p_unadjusted'], replicates)}。"
    return (
        f"### {title}\n\n"
        f"配对 Brier 差（前者减后者，越低越好）点估计 {_num(block['estimate'])}，"
        f"聚类 bootstrap 95%区间 [{_num(block['ci95_low'])}, {_num(block['ci95_high'])}]，"
        f"宽度 {_num(block['ci_width'])}。{p_text}{holm}\n\n"
        f"{FLAG_TEXT.get(flag, flag)}\n\n{extra}\n"
    )


def render_explanation(summary: dict[str, Any]) -> str:
    task = summary["task"]
    holdout = summary["holdout"]
    primary = summary["study_primary"]
    inventory = summary["inventory"]
    lines = [
        "# 实验说明",
        "",
        "本文由 `research/explain.py` 根据 `score_summary.json` 生成。数字以该摘要为准。",
        "",
        "这是探索性研究，不是预测保证。不用于医疗、博彩或投资决策。",
        "本结果不是“玄学已被科学验证”的证据。工程链路正确不等于预测正确。",
        "没有显著差异不等于两种方法等效。区间宽表示证据不足。",
        "历史回放不能排除公开结果已被语言模型记住；本次模型四臂未运行。",
        "该起卦法在本任务里是日历函数。它若优于常数基率，仍可能只是季节或日期信息。",
        "",
        "## 主终点",
        "",
        f"状态：{primary['status']}。对照是 {primary['contrast']}。",
        primary["reason_zh"],
        "主终点（规则增强臂 B 相对原版臂 A 的配对 Brier 差）本次未估计。",
        "",
        "## 任务",
        "",
        f"问题：{task['question_template']}",
        f"先导期 {task['pilot_start']} 至 {task['pilot_end']}，只用来拟合常数基率和农历月比率。",
        f"留出集 {task['holdout_start']} 至 {task['holdout_end']}，只分析这一次。",
        f"结算来源：{task['settlement']}。缺测不填补。阈值 {task['threshold_mm']} 毫米。",
        f"样本类别：{summary['sample_class']}。",
        "",
        "## 留出集计数",
        "",
        (
            f"日期 {holdout['n_dates']} 天，已结算 {holdout['n_resolved']}，"
            f"未结算 {holdout['n_unresolved']}，失败率 {_num(holdout['failure_rate'])}。"
        ),
        (
            f"结局发生率 {_num(holdout['outcome_rate'])}。ISO 周聚类 {holdout['cluster_count']} 个。"
            f"主体数 {holdout['subject_count']}。相同卦象的事件数（含重复）"
            f" {holdout['identical_cast_collision_events']}。"
        ),
        "智能体数和重复起卦都不是样本量。同一时点的卦相同，只保留每事件一行。",
        "",
        "## 概率与校准",
        "",
    ]
    for name, block in summary["probabilities"].items():
        lines.append(
            f"- {name}：平均 Brier {_num(block['mean_brier'])}，平均概率 {_num(block['mean_p'])}，"
            f"ECE {_num(block['ece'])}，整体校准差（平均概率减发生率）{_num(block['calibration_in_the_large'])}。"
        )
    lines.extend(
        [
            "",
            "分箱可靠性见摘要里的 reliability。bootstrap 区间的频率学覆盖率不能由这一次样本估计。",
            "",
            "## 离线对照",
            "",
            "这些对照执行的是规则引擎和评分器。它们不代替未运行的模型四臂。",
            "",
            _contrast_paragraph(
                "规则映射减常数基率（离线参照，不是研究主终点）",
                summary["contrasts"]["rule_minus_base_rate"],
                summary.get("bootstrap_replicates"),
            ),
            _contrast_paragraph(
                "规则映射减农历月基线（Holm 家族）",
                summary["contrasts"]["rule_minus_calendar"],
                summary.get("bootstrap_replicates"),
            ),
            _contrast_paragraph(
                "规则映射减同月符号对照（Holm 家族）",
                summary["contrasts"]["rule_minus_symbol_control"],
                summary.get("bootstrap_replicates"),
            ),
            _contrast_paragraph(
                "农历月基线减常数基率（只作描述，不进 Holm 家族）",
                summary["contrasts"]["calendar_minus_base_rate"],
                summary.get("bootstrap_replicates"),
            ),
            "## 花费",
            "",
            (
                f"模型调用 {summary['cost']['model_calls']} 次，"
                f"prompt tokens {summary['cost']['prompt_tokens']}，"
                f"completion tokens {summary['cost']['completion_tokens']}。"
                "没有模型账单。不编造金额。"
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
            "## 规则与来源",
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
