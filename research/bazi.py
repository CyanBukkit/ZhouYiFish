# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Four pillars (八字). This is not the Meihua date-count cast.

Year and month change at solar-term instants from sxtwl (寿星天文历), not at
lunar new year and not at the civil date of 立春. The checked 2024 terms match
Hong Kong Observatory clock times within one minute. Day gan-zhi is taken from
sxtwl and was not found in that observatory solar-term bulletin. True solar
time is not applied. The 子初 day boundary is not implemented.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache

import sxtwl

from research.calendar_time import hour_branch_number

STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
SOLAR_TERMS = [
    "冬至", "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨",
    "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋", "处暑", "白露",
    "秋分", "寒露", "霜降", "立冬", "小雪", "大雪",
]
# 节, not 中气. 寅月 starts at 立春.
JIE_BRANCH = [
    ("小寒", "丑"),
    ("立春", "寅"),
    ("惊蛰", "卯"),
    ("清明", "辰"),
    ("立夏", "巳"),
    ("芒种", "午"),
    ("小暑", "未"),
    ("立秋", "申"),
    ("白露", "酉"),
    ("寒露", "戌"),
    ("立冬", "亥"),
    ("大雪", "子"),
]
UTC8 = timezone(timedelta(hours=8))
POLICY = {
    "year_boundary": "lichun_instant_not_spring_festival_and_not_civil_date",
    "month_boundary": "jie_instant_not_zhongqi_and_not_lunar_month",
    "day_boundary": "zi_zheng_00:00_in_the_input_timezone_converted_to_UTC+8",
    "not_implemented_day_school": "zi_chu_23:00_changes_the_day_pillar",
    "hour_time": "standard_clock_not_true_solar_time",
    "library": "sxtwl==2.0.7",
    "solar_term_check": "2024 HKO terms within one minute; not every historical year",
    "day_cycle_check": "sxtwl sexagenary day, no second published day-ganzhi table in this repo",
}


class FourPillarsError(ValueError):
    """The instant cannot support the stated four-pillar policy."""


def _pillar(stem_index: int, branch_index: int) -> str:
    return STEMS[stem_index % 10] + BRANCHES[branch_index % 12]


def _year_index(gregorian_year_of_lichun: int) -> int:
    return (gregorian_year_of_lichun - 4) % 60


@lru_cache(maxsize=64)
def _term_instants(year: int) -> tuple[tuple[str, datetime], ...]:
    found: dict[str, datetime] = {}
    cursor = sxtwl.fromSolar(year - 1, 11, 1)
    for offset in range(500):
        day = cursor.after(offset)
        if not day.hasJieQi():
            continue
        name = SOLAR_TERMS[day.getJieQi()]
        if name in found:
            continue
        parts = sxtwl.JD2DD(day.getJieQiJD())
        second = int(round(parts.s))
        minute = int(parts.m)
        hour = int(parts.h)
        if second == 60:
            second = 0
            minute += 1
        if minute == 60:
            minute = 0
            hour += 1
        instant = datetime(int(parts.Y), int(parts.M), int(parts.D), hour, minute, second, tzinfo=UTC8)
        found[name] = instant
    missing = [name for name, _branch in JIE_BRANCH if name not in found]
    missing += [name for name in ("立春",) if name not in found]
    if missing:
        raise FourPillarsError(f"节气时刻不完整：{missing}")
    return tuple(sorted(found.items(), key=lambda item: item[1]))


def _as_utc8(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise FourPillarsError("四柱拒绝无时区时间，也不接受把事件编号当成出生时刻。")
    return moment.astimezone(UTC8)


def four_pillars(moment: datetime | None, *, hour_known: bool) -> dict[str, object]:
    """Return pillars for one aware instant.

    ``hour_known`` false means the clock time was not in the source. No hour
    is invented, and the chart is incomplete.
    """

    if moment is None or not hour_known:
        return {
            "status": "not_applicable",
            "reason": "没有来源里的钟点，不能排时柱，也不把日期中午或事件编号补成时辰。",
            "policy": POLICY,
            "pillars": None,
        }
    local = _as_utc8(moment)
    terms = dict(_term_instants(local.year))
    lichun = terms["立春"]
    year_number = local.year if local >= lichun else local.year - 1
    if local < lichun:
        lichun = dict(_term_instants(local.year - 1))["立春"]
        if local < lichun:
            year_number = local.year - 2
    year_gz_index = _year_index(year_number)
    year_pillar = _pillar(year_gz_index, year_gz_index)
    jie_times = []
    for name, branch in JIE_BRANCH:
        for shift in (-1, 0, 1):
            instant = dict(_term_instants(local.year + shift))[name]
            jie_times.append((instant, branch))
    jie_times.sort(key=lambda item: item[0])
    month_branch = None
    for instant, branch in jie_times:
        if instant <= local:
            month_branch = branch
    if month_branch is None:
        raise FourPillarsError("找不到不晚于出生时刻的节。")
    yin_stem = (2 * (year_gz_index % 5) + 2) % 10
    month_offset = "寅卯辰巳午未申酉戌亥子丑".index(month_branch)
    month_pillar = _pillar(yin_stem + month_offset, BRANCHES.index(month_branch))
    day = sxtwl.fromSolar(local.year, local.month, local.day)
    day_gz = day.getDayGZ()
    day_pillar = STEMS[day_gz.tg] + BRANCHES[day_gz.dz]
    branch_number = hour_branch_number(local.hour)
    zi_stem = (2 * (day_gz.tg % 5)) % 10
    hour_pillar = _pillar(zi_stem + branch_number - 1, branch_number - 1)
    return {
        "status": "complete_under_stated_policy",
        "policy": POLICY,
        "input_utc8": local.isoformat(),
        "year_pillar": year_pillar,
        "month_pillar": month_pillar,
        "day_pillar": day_pillar,
        "hour_pillar": hour_pillar,
        "pillars": year_pillar + month_pillar + day_pillar + hour_pillar,
        "true_solar_time_applied": False,
        "lunar_month_used_as_bazi_month": False,
        "does_not_determine_occupation": True,
    }


def term_instant(year: int, name: str) -> datetime:
    return dict(_term_instants(year))[name]
