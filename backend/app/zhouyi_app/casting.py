# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Four pillars for an archive, using the checked research calendar."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.bazi import JIE_BRANCH, POLICY, FourPillarsError, four_pillars, term_instant
from research.bazi_rules import evaluate
from research.persona import hypothetical_occupations

SCENARIOS = [
    "是否把一份共享备忘录交给同事继续改",
    "是否报名参加社区读书会",
    "是否在小组会上说明自己的不同意见",
    "是否接受一项相邻岗位的短期协作",
]


def parse_moment(birth_date: str, birth_time: str, timezone_name: str) -> datetime:
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise FourPillarsError(f"无法识别时区 {timezone_name}。") from exc
    try:
        year, month, day = (int(part) for part in birth_date.split("-"))
        hour, minute = (int(part) for part in birth_time.split(":"))
        return datetime(year, month, day, hour, minute, tzinfo=zone)
    except ValueError as exc:
        raise FourPillarsError("出生日期或时刻无法解析。时刻用 HH:MM。") from exc


def active_jie(moment: datetime) -> dict[str, str]:
    local = moment.astimezone(ZoneInfo("Asia/Shanghai"))
    best: tuple[datetime, str, str] | None = None
    for shift in (-1, 0, 1):
        for name, branch in JIE_BRANCH:
            instant = term_instant(local.year + shift, name)
            if instant <= local and (best is None or instant > best[0]):
                best = (instant, name, branch)
    if best is None:
        raise FourPillarsError("找不到不晚于该时刻的节。")
    lichun = term_instant(local.year, "立春")
    return {
        "active_jie": best[1],
        "month_branch_from_jie": best[2],
        "active_jie_at": best[0].isoformat(),
        "lichun_same_year": lichun.isoformat(),
        "year_uses_previous_lichun": local < lichun,
        "clock_used": "标准时区钟点。出生地没有参与真太阳时换算。",
    }


def luck_params(fields: dict[str, object]) -> dict[str, object]:
    year = fields.get("liunian_year")
    return {
        "luck_mode": fields.get("luck_mode") or "",
        "luck_sex": fields.get("luck_sex") or "",
        "luck_direction": fields.get("luck_direction") or "",
        "liunian_year": int(year) if year else None,
    }


def cast_fields(fields: dict[str, object]) -> dict[str, object]:
    """Return a chart payload. Missing hour stays incomplete on purpose."""

    base = {
        "policy": POLICY,
        "true_solar_time_applied": False,
        "birth_place_used_for_true_solar": False,
        "birth_place_stored": fields.get("birth_place") or "",
        "place_notice": "出生地只作档案记录。排盘使用所选时区的标准钟，不是真太阳时。",
        "zi_chu_notice": "子初换日（23:00 切日柱）没有实现。日界是换到 UTC+8 后的 00:00。",
        "does_not_determine_occupation": True,
    }
    if not fields.get("birth_date"):
        chart = {**base, "status": "not_applicable", "reason": "没有出生日期，不能排盘。", "pillars": None}
        chart["reading"] = evaluate(chart, luck_params(fields))
        return chart
    if not fields.get("birth_time"):
        chart = {**base, **four_pillars(None, hour_known=False)}
        chart["reading"] = evaluate(chart, luck_params(fields))
        return chart
    moment = parse_moment(str(fields["birth_date"]), str(fields["birth_time"]), str(fields["timezone"]))
    chart = four_pillars(moment, hour_known=True)
    chart.update(base)
    chart["solar_term"] = active_jie(moment)
    day = str(chart["day_pillar"])
    occupations = hypothetical_occupations(day)
    chart["rule_candidates"] = occupations
    chart["reading"] = evaluate(chart, luck_params(fields))
    return chart
