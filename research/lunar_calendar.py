# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Chinese calendar via pinned zhdate, with the protocol's year and leap rules.

zhdate is GPL-3.0-or-later. This wrapper does not reimplement its tables.
Tests compare the boundary dates with Hong Kong Observatory conversion tables.
"""

from __future__ import annotations

from datetime import date, datetime
from importlib.metadata import version

from zhdate import ZhDate

from research.calendar_time import BRANCH_NAMES

REQUIRED_ZHDATE_VERSION = "0.1"


class CalendarError(ValueError):
    """The pinned calendar cannot answer this civil date."""


def assert_calendar_library() -> str:
    installed = version("zhdate")
    if installed != REQUIRED_ZHDATE_VERSION:
        raise CalendarError(
            f"需要 zhdate=={REQUIRED_ZHDATE_VERSION}，当前是 {installed}。"
            "未核验的其他版本不能充当本协议的农历。"
        )
    return installed


def branch_from_lunar_year(lunar_year: int) -> tuple[int, str]:
    """Earthly branch of the lunar year whose Spring Festival falls in ``lunar_year``.

    Index 0 is 子 for Gregorian year 4, 16, ..., 1984. The caller must pass
    the lunar year, which changes at Spring Festival rather than at 立春.
    """

    index = (lunar_year - 4) % 12
    return index + 1, BRANCH_NAMES[index]


def lunar_from_civil_date(civil: date) -> dict[str, object]:
    """Return the protocol's lunar fields for a civil date.

    zhdate 0.1 rejects aware datetimes, so it receives a naive civil date
    only after this package has already resolved Asia/Shanghai.
    """

    library_version = assert_calendar_library()
    try:
        lunar = ZhDate.from_datetime(datetime(civil.year, civil.month, civil.day))
    except Exception as exc:  # zhdate raises TypeError outside its table.
        raise CalendarError(f"农历库无法转换 {civil.isoformat()}：{exc}") from exc
    month_number = int(lunar.lunar_month)
    if not 1 <= month_number <= 12:
        raise CalendarError(f"农历月数异常：{month_number}")
    branch_number, branch_name = branch_from_lunar_year(int(lunar.lunar_year))
    return {
        "lunar_year": int(lunar.lunar_year),
        "lunar_month_number": month_number,
        "leap_month": bool(lunar.leap_month),
        "lunar_day": int(lunar.lunar_day),
        "year_branch_number": branch_number,
        "year_branch_name": branch_name,
        "year_boundary": "spring_festival",
        "leap_month_policy": "same_month_number_not_added_into_S",
        "library": {
            "name": "zhdate",
            "version": library_version,
            "license": "GPL-3.0-or-later",
        },
    }
