# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Build one event row per date, score the holdout once, and lock a future ledger."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from research.baselines import (
    calendar_probability,
    fit_reference_rates,
    symbol_control_probabilities,
)
from research.calendar_time import SHANGHAI
from research.data_openmeteo import split_name
from research.explain import render_explanation
from research.mapping import probability_from_lines, structural_features
from research.meihua import cast_from_datetime
from research.protocol import load_protocol, sha256_bytes, sha256_obj
from research.scoring import (
    brier,
    bootstrap_contrast,
    cluster_id,
    holm,
    interpret,
    mean,
    reliability_table,
)

OUTPUT_NAMES = (
    "predictions.jsonl",
    "score_summary.json",
    "future_ledger.jsonl",
    "实验说明.md",
)


def run_experiment(
    daily_rows: list[dict[str, Any]],
    *,
    sample_class: str,
    snapshot_sha256: str,
    bootstrap_replicates: int | None = None,
) -> dict[str, Any]:
    protocol, digest = load_protocol()
    if sample_class not in {"historical_open_meteo_retrospective", "synthetic_pipeline_only"}:
        raise ValueError("未知样本类别。")
    events = [_event_from_daily(row, protocol, digest) for row in daily_rows]
    _assert_splits(events, protocol)
    pilot = [row for row in events if row["split"] == "pilot"]
    holdout = [row for row in events if row["split"] == "holdout"]
    rates = fit_reference_rates(pilot)
    for row in events:
        row["p_base"] = float(rates["base_rate"])
        row["p_calendar"] = calendar_probability(rates, int(row["lunar_month_number"]))
        row["baseline_fit"] = {
            "base_rate_smoothed": rates["base_rate_smoothed"],
            "month_fallback_to_base": rates["month_fallback_to_base"],
            "month_smoothed": rates["month_smoothed"],
        }
    for row in pilot:
        row["p_symbol_control"] = None
        row["used_for_scoring"] = False
        row["used_for_fitting"] = True
    scoring = [row for row in holdout if row["outcome"] in (0, 1)]
    if not scoring:
        raise RuntimeError("留出集没有可结算事件。拒绝编造 Brier。")
    permuted = symbol_control_probabilities(scoring)
    for row, probability in zip(scoring, permuted):
        row["p_symbol_control"] = probability
        row["used_for_scoring"] = True
        row["used_for_fitting"] = False
    for row in holdout:
        if row["outcome"] not in (0, 1):
            row["p_symbol_control"] = None
            row["used_for_scoring"] = False
            row["used_for_fitting"] = False
    summary = _summarize(
        protocol,
        digest,
        snapshot_sha256,
        sample_class,
        pilot,
        holdout,
        scoring,
        rates,
        bootstrap_replicates,
    )
    explanation = render_explanation(summary)
    return {
        "events": events,
        "summary": summary,
        "explanation": explanation,
    }


def dumps_json(obj: Any) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def dumps_jsonl(rows: list[dict[str, Any]]) -> str:
    import json

    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )


def _event_from_daily(row: dict[str, Any], protocol: dict[str, Any], digest: str) -> dict[str, Any]:
    event = _cast_row(
        date.fromisoformat(row["date"]),
        precipitation_mm=row["precipitation_mm"],
        grid=row,
        protocol=protocol,
        digest=digest,
        record_class="retrospective_engineering",
    )
    event["split"] = split_name(row["date"])
    event["grid_settled"] = True
    if event["time"]["utc_offset"] != "+08:00":
        raise RuntimeError(
            f"{row['date']} 的 Asia/Shanghai 偏移不是 +08:00，与本窗口的结算日界假设不一致。"
        )
    return event


def _cast_row(
    civil: date,
    *,
    precipitation_mm: float | None,
    grid: dict[str, Any] | None,
    protocol: dict[str, Any],
    digest: str,
    record_class: str,
) -> dict[str, Any]:
    moment = datetime(civil.year, civil.month, civil.day, 0, 0, 0, tzinfo=SHANGHAI)
    cast = cast_from_datetime(moment)
    features = structural_features(cast)
    p_rule = probability_from_lines(list(cast["lines_bottom_up"]))
    task = protocol["task"]
    question = task["question_template"].format(date=civil.isoformat())
    if record_class != "retrospective_engineering":
        raise RuntimeError("历史事件构建器不写前瞻发行标记。")
    outcome = _outcome(precipitation_mm, float(task["threshold_mm"]))
    subject = "requested:{:.4f},{:.4f}".format(
        float(task["requested_latitude"]), float(task["requested_longitude"])
    )
    if grid and grid.get("grid_latitude") is not None:
        subject = "openmeteo:{},{}".format(grid["grid_latitude"], grid["grid_longitude"])
    input_body = {
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": digest,
        "event_id": f"shanghai-precip-ge1mm-{civil.isoformat()}",
        "question": question,
        "information_time_local": cast["time"]["local"],
        "information_time_utc": cast["time"]["utc"],
        "utc_offset": cast["time"]["utc_offset"],
        "requested_latitude": task["requested_latitude"],
        "requested_longitude": task["requested_longitude"],
        "rule_inputs": cast["inputs"],
        "lunar_year": cast["lunar"]["lunar_year"],
        "leap_month": cast["lunar"]["leap_month"],
    }
    input_hash = sha256_obj(input_body)
    prediction_body = {
        "input_sha256": input_hash,
        "mapping_id": protocol["probability_mapping"]["id"],
        "p_rule": p_rule,
        "cast_sha256": cast["cast_sha256"],
        "features": features,
        "hexagram": cast["hexagram"],
        "changed_hexagram": cast["changed_hexagram"],
    }
    return {
        "event_id": input_body["event_id"],
        "record_class": record_class,
        "issued_prospectively": False,
        "status": "settled" if outcome is not None else "unresolved",
        "subject_id": subject,
        "question": question,
        "information_time_local": cast["time"]["local"],
        "information_time_utc": cast["time"]["utc"],
        "utc_offset": cast["time"]["utc_offset"],
        "time": cast["time"],
        "lunar_year": cast["lunar"]["lunar_year"],
        "lunar_month_number": cast["lunar"]["lunar_month_number"],
        "leap_month": cast["lunar"]["leap_month"],
        "lunar_day": cast["lunar"]["lunar_day"],
        "year_branch_number": cast["inputs"]["year_branch_number"],
        "year_branch_name": cast["lunar"]["year_branch_name"],
        "hour_branch_number": cast["inputs"]["hour_branch_number"],
        "hour_branch_name": cast["time"]["hour_branch_name"],
        "cast": cast,
        "features": features,
        "mapping_id": protocol["probability_mapping"]["id"],
        "p_rule": p_rule,
        "precipitation_mm": precipitation_mm,
        "outcome": outcome,
        "threshold_mm": float(task["threshold_mm"]),
        "grid_latitude": None if grid is None else grid.get("grid_latitude"),
        "grid_longitude": None if grid is None else grid.get("grid_longitude"),
        "input_sha256": input_hash,
        "prediction_sha256": sha256_obj(prediction_body),
        "cluster_id": cluster_id(civil.isoformat()),
    }


def _summarize(
    protocol: dict[str, Any],
    digest: str,
    snapshot_sha256: str,
    sample_class: str,
    pilot: list[dict[str, Any]],
    holdout: list[dict[str, Any]],
    scoring: list[dict[str, Any]],
    rates: dict[str, Any],
    bootstrap_replicates: int | None,
) -> dict[str, Any]:
    margin = float(protocol["task"]["minimum_practical_brier_gain"])
    outcomes = [int(row["outcome"]) for row in scoring]
    series = {
        "rule": [float(row["p_rule"]) for row in scoring],
        "base_rate": [float(row["p_base"]) for row in scoring],
        "calendar": [float(row["p_calendar"]) for row in scoring],
        "symbol_control": [float(row["p_symbol_control"]) for row in scoring],
    }
    contrasts = {
        "rule_minus_base_rate": _contrast(series["rule"], series["base_rate"], outcomes, scoring, bootstrap_replicates),
        "rule_minus_calendar": _contrast(series["rule"], series["calendar"], outcomes, scoring, bootstrap_replicates),
        "rule_minus_symbol_control": _contrast(
            series["rule"], series["symbol_control"], outcomes, scoring, bootstrap_replicates
        ),
        "calendar_minus_base_rate": _contrast(
            series["calendar"], series["base_rate"], outcomes, scoring, bootstrap_replicates
        ),
    }
    family_names = list(protocol["statistics"]["holm_family"])
    family = holm({name: float(contrasts[name]["mc_proportion"]) for name in family_names})
    for name, block in contrasts.items():
        block["interval_location"] = interpret(block, margin)
        block["margin_is_a_reading_aid_not_a_holm_test"] = True
        block["wider_than_margin"] = float(block["ci_width"]) > margin
        if name in family:
            block["holm_mc_proportion"] = family[name]
            block["holm_applies_to"] = "zero_difference_mc_proportion_only"
            block["holm_does_not_adjust_intervals"] = True
            block["holm_does_not_test_margin"] = True
            block["role"] = "exploratory_zero_difference_family"
        elif name == "calendar_minus_base_rate":
            block["role"] = "exploratory_description_not_in_holm_family"
        else:
            block["role"] = "exploratory_reference_not_study_primary"
    cast_counts: dict[tuple, int] = {}
    for row in scoring:
        # The full cast hash includes the civil timestamp, so it never collides.
        # Count the structural cast: counts, lines, and moving line.
        signature = (
            row["cast"]["inputs"]["year_branch_number"],
            row["cast"]["inputs"]["lunar_month_number"],
            row["cast"]["inputs"]["lunar_day"],
            row["cast"]["inputs"]["hour_branch_number"],
            tuple(row["cast"]["lines_bottom_up"]),
            row["cast"]["moving_line"],
        )
        cast_counts[signature] = cast_counts.get(signature, 0) + 1
    collisions = sum(count for count in cast_counts.values() if count > 1)
    unresolved = sum(1 for row in holdout if row["outcome"] not in (0, 1))
    n_dates = len(holdout)
    quote = protocol["quotes_from_simplified_transcription"]["worked_example_quote"]
    return {
        "sample_class": sample_class,
        "synthetic_pipeline_only": sample_class == "synthetic_pipeline_only",
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": digest,
        "snapshot_sha256": snapshot_sha256,
        "study_primary": {
            "contrast": "mean paired Brier of arm B minus arm A",
            "status": "not_run",
            "reason_zh": (
                "四臂没有运行。阻塞是没有明确交给本次任务的模型凭据。"
                "未购买、未搜索凭据，也没有用随机数或 mock 回答填充四臂。"
                "臂 A 只是聊天补全基线，不是原版 MiroFish。OASIS 群体仿真没有接通。"
            ),
        },
        "task": {
            "question_template": protocol["task"]["question_template"],
            "pilot_start": protocol["task"]["pilot"]["start"],
            "pilot_end": protocol["task"]["pilot"]["end"],
            "holdout_start": protocol["task"]["holdout"]["start"],
            "holdout_end": protocol["task"]["holdout"]["end"],
            "threshold_mm": protocol["task"]["threshold_mm"],
            "settlement": protocol["task"]["settlement"]["attribution"],
            "settlement_kind": "open_meteo_archive_grid_not_a_station_observation",
            "model_parameter_pinned": False,
            "requested_latitude": protocol["task"]["requested_latitude"],
            "requested_longitude": protocol["task"]["requested_longitude"],
            "returned_grid_latitude": holdout[0]["grid_latitude"] if holdout else None,
            "returned_grid_longitude": holdout[0]["grid_longitude"] if holdout else None,
            "missing_rows_imputed_as_zero": 0,
        },
        "pilot": _split_counts(pilot),
        "holdout": {
            **_split_counts(holdout),
            "n_resolved": len(scoring),
            "n_unresolved": unresolved,
            "failure_rate": unresolved / n_dates,
            "outcome_rate": mean(outcomes),
            "cluster_count": len({row["cluster_id"] for row in scoring}),
            "subject_count": len({row["subject_id"] for row in scoring}),
            "identical_cast_collision_events": collisions,
        },
        "baseline_fit": {
            "base_rate": rates["base_rate"],
            "base_rate_smoothed": rates["base_rate_smoothed"],
            "month_rates": rates["month_rates"],
            "month_fallback_to_base": rates["month_fallback_to_base"],
            "month_smoothed": rates["month_smoothed"],
            "pilot_resolved": rates["pilot_resolved"],
        },
        "probabilities": {
            name: _probability_block(values, outcomes) for name, values in series.items()
        },
        "contrasts": contrasts,
        "margin": margin,
        "alpha": protocol["statistics"]["alpha"],
        "bootstrap_replicates": int(
            bootstrap_replicates or protocol["statistics"]["bootstrap_replicates"]
        ),
        "cost": {
            "model_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "currency_usd": None,
        },
        "inventory": {
            "ran": [
                "梅花易数卷一年月日时起卦",
                "香港天文台边界日期所核验的 zhdate 0.1 农历换算",
                "Open-Meteo 日降水快照的解析与评分" if sample_class.startswith("historical") else "合成降水上的链路演练",
                "先导期常数基率与农历月基线",
                "同农历月的单次固定置换",
                "按 ISO 周的探索性百分位区间",
            ],
            "not_run": [
                "聊天四臂 A/B/C/D",
                "OASIS 群体仿真、Zep 与报告代理",
                "奇门遁甲",
                "风水",
                "揲蓍",
                "体用五行与卦辞断语",
            ],
            "pending_settlement": [
                "prospective_v2 的结算表仍为空。旧 future_ledger.jsonl 已标为 invalid/excluded，不在待结算队列。"
            ],
        },
        "symbol_control": {
            "draws": 1,
            "kind": "single_fixed_hmac_permutation",
            "interval_includes_permutation_randomness": False,
        },
        "evaluation_label_zh": "预设代码分割的回顾性评估，研究者选择泄漏未排除",
        "rule_note_zh": (
            "规则计数来自维基文库《梅花易数》卷一公开转录，不是校勘定本，也不把邵雍写成已证实的作者。"
            f"观梅占算例核对为：{quote}"
            "八整为坤有该转录的句子。六整除记为上爻没有对应的原文句子，只是协议边界。"
            "P-MAP-1 是工程假设 (阳爻数+1)/8，不是古法给出的概率，也不是有传统依据的预测模型。"
        ),
        "limitations_zh": [
            "四臂没有运行，OASIS 没有接通，不能说规则增强了 MiroFish，也不能说预测更准。",
            "这是预设代码分割的回顾性评估，研究者选择泄漏未排除。没有外部时间证据证明研究者从未看过 2023 年的降水，或没有试过别的映射。",
            "P-MAP-1 只是人为的概率映射。",
            "离线 Brier 只描述这一窗口上的这条映射，不是对周易或梅花的终审。",
            "年月日时起卦在固定时点上是日历函数。",
            "预测时点固定在当地 0 点，时支恒为子，本任务识别不了时辰效应。",
            "闰月与本月使用同一个月数，所以有些日期会得到同一卦。",
            "只有一个地理网格。按 ISO 周重抽样仍留下季节性和相邻周相关，百分位区间只是探索性描述。",
            "同月对照只有一条固定置换，区间没有包含置换分布的随机性。",
            "Open-Meteo 返回的是归档网格，不是气象站实测，而且请求没有固定模型。",
            "空降水量保持为空，缺测条数不会被填成 0。",
            "旧前瞻队列已排除。新的 prospective_v2 在公开提交时间写入并完成比较之前，不能称为已公开预注册。",
            "农历依赖 zhdate 0.1，边界日期对照过香港天文台换算表，不是独立的全历史校勘。",
            "不用于医疗、博彩或投资决策。",
        ],
    }


def _contrast(left, right, outcomes, rows, replicates: int | None) -> dict[str, Any]:
    differences = [
        brier(left_p, outcome) - brier(right_p, outcome)
        for left_p, right_p, outcome in zip(left, right, outcomes)
    ]
    return bootstrap_contrast(
        differences,
        [row["cluster_id"] for row in rows],
        replicates=replicates,
    )


def _probability_block(probabilities: list[float], outcomes: list[int]) -> dict[str, Any]:
    table = reliability_table(probabilities, outcomes)
    return {
        "mean_brier": mean(brier(probability, outcome) for probability, outcome in zip(probabilities, outcomes)),
        "mean_p": mean(probabilities),
        "ece": table["ece"],
        "calibration_in_the_large": table["calibration_in_the_large"],
        "reliability": table["bins"],
        "frequentist_coverage_of_bootstrap_ci": table["frequentist_coverage_of_bootstrap_ci"],
    }


def _split_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = [row for row in rows if row["outcome"] in (0, 1)]
    return {
        "n_dates": len(rows),
        "n_resolved": len(resolved),
        "n_unresolved": len(rows) - len(resolved),
        "failure_rate": (len(rows) - len(resolved)) / len(rows) if rows else None,
    }


def _outcome(precipitation_mm: float | None, threshold: float) -> int | None:
    if precipitation_mm is None:
        return None
    if isinstance(precipitation_mm, bool) or not isinstance(precipitation_mm, (int, float)):
        raise ValueError("降水量必须是有限非负数或空值。空值不能填 0。")
    value = float(precipitation_mm)
    if not math.isfinite(value) or value < 0:
        raise ValueError("降水量必须是有限非负数。空值不能填 0。")
    return 1 if value >= threshold else 0


def _assert_splits(events: list[dict[str, Any]], protocol: dict[str, Any]) -> None:
    pilot_ids = {row["event_id"] for row in events if row["split"] == "pilot"}
    holdout_ids = {row["event_id"] for row in events if row["split"] == "holdout"}
    if pilot_ids & holdout_ids:
        raise RuntimeError("先导期和留出集有相同事件。")
    if len(pilot_ids) != len([row for row in events if row["split"] == "pilot"]):
        raise RuntimeError("先导期事件号重复。")
    expected_pilot = _dates(protocol["task"]["pilot"]["start"], protocol["task"]["pilot"]["end"])
    expected_holdout = _dates(protocol["task"]["holdout"]["start"], protocol["task"]["holdout"]["end"])
    got = {row["time"]["civil_date"] for row in events}
    expected = {item.isoformat() for item in expected_pilot + expected_holdout}
    if got != expected:
        raise RuntimeError("日序列与协议窗口不一致。")


def _dates(start: str | date, end: str | date) -> list[date]:
    cursor = start if isinstance(start, date) else date.fromisoformat(start)
    last = end if isinstance(end, date) else date.fromisoformat(end)
    days = []
    while cursor <= last:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def snapshot_digest(snapshot_bytes: bytes) -> str:
    if snapshot_bytes.startswith(b"\xef\xbb\xbf"):
        raise ValueError("快照含有 BOM。")
    return sha256_bytes(snapshot_bytes)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def zone_name() -> str:
    return getattr(ZoneInfo("Asia/Shanghai"), "key", "Asia/Shanghai")
