# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""梅花易数卷一 年月日时起卦. Deterministic, and it refuses outcome labels."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from research.calendar_time import describe_instant
from research.hexagrams import (
    compose_lines,
    hexagram_label,
    split_lines,
)
from research.lunar_calendar import lunar_from_civil_date
from research.protocol import sha256_obj

EXACT_EIGHT = 8
EXACT_SIX = 6


class CastError(ValueError):
    """The inputs are outside the frozen arithmetic."""


def positive_remainder(value: int, modulus: int, exact_maps_to: int) -> tuple[int, int]:
    if not isinstance(value, int) or value <= 0:
        raise CastError(f"起卦总数必须是正整数，收到 {value!r}。")
    raw = value % modulus
    mapped = exact_maps_to if raw == 0 else raw
    return raw, mapped


def cast_from_numbers(
    year_branch: int,
    month: int,
    day: int,
    hour_branch: int,
    *,
    outcome: Any = None,
) -> dict[str, Any]:
    """Cast from the four classical counts.

    ``outcome`` exists so a mistaken call fails loudly. The arithmetic
    never reads it.
    """

    if outcome is not None:
        raise CastError("起卦函数拒绝接收结局。规则不能读标签。")
    _check_range("年支", year_branch, 1, 12)
    _check_range("月数", month, 1, 12)
    _check_range("日数", day, 1, 30)
    _check_range("时支", hour_branch, 1, 12)
    total = year_branch + month + day
    timed = total + hour_branch
    upper_raw, upper = positive_remainder(total, 8, EXACT_EIGHT)
    lower_raw, lower = positive_remainder(timed, 8, EXACT_EIGHT)
    moving_raw, moving = positive_remainder(timed, 6, EXACT_SIX)
    lines = compose_lines(upper, lower)
    changed = list(lines)
    changed[moving - 1] = 1 - changed[moving - 1]
    changed_upper, changed_lower = split_lines(changed)
    cast = {
        "rule_version": "meihua-juan1-ymd-hour-v1",
        "inputs": {
            "year_branch_number": year_branch,
            "lunar_month_number": month,
            "lunar_day": day,
            "hour_branch_number": hour_branch,
        },
        "S": total,
        "S_plus_hour": timed,
        "upper_remainder_raw": upper_raw,
        "upper_number": upper,
        "lower_remainder_raw": lower_raw,
        "lower_number": lower,
        "moving_remainder_raw": moving_raw,
        "moving_line": moving,
        "mod8_zero_policy": "map_to_8_follows_如得八数整即坤卦",
        "mod6_zero_policy": "map_to_6_protocol_boundary_not_a_quotation",
        "lines_bottom_up": lines,
        "hexagram": hexagram_label(upper, lower),
        "changed_lines_bottom_up": changed,
        "changed_upper_number": changed_upper,
        "changed_lower_number": changed_lower,
        "changed_hexagram": hexagram_label(changed_upper, changed_lower),
        "flip": "exactly one line, yin and yang exchange; bottom-up index is moving_line",
        "not_used": ["outcome", "body_use_wuxing", "image_statements", "later_heaven_numbers", "yarrow"],
    }
    cast["cast_sha256"] = sha256_obj(
        {key: value for key, value in cast.items() if key != "cast_sha256"}
    )
    return cast


def cast_from_datetime(moment: datetime, *, outcome: Any = None) -> dict[str, Any]:
    """Cast from a timezone-aware instant. No seed, and no outcome."""

    if outcome is not None:
        raise CastError("起卦函数拒绝接收结局。规则不能读标签。")
    civil = describe_instant(moment)
    lunar = lunar_from_civil_date(datetime.fromisoformat(civil.civil_date).date())
    cast = cast_from_numbers(
        int(lunar["year_branch_number"]),
        int(lunar["lunar_month_number"]),
        int(lunar["lunar_day"]),
        civil.hour_branch_number,
    )
    cast["time"] = civil.as_dict()
    cast["lunar"] = lunar
    cast["seed"] = None
    cast["cast_sha256"] = sha256_obj(
        {key: value for key, value in cast.items() if key != "cast_sha256"}
    )
    return cast


def _check_range(name: str, value: int, low: int, high: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise CastError(f"{name}必须是 {low}–{high} 的整数，收到 {value!r}。")
