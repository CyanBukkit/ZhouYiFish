# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Civil time in Asia/Shanghai. The hour branch does not move the date."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")
BRANCH_NAMES = list("子丑寅卯辰巳午未申酉戌亥")


class TimePolicyError(ValueError):
    """The timestamp is not usable under the frozen civil-time policy."""


@dataclass(frozen=True)
class CivilInstant:
    local: datetime
    utc: datetime
    utc_offset: str
    civil_date: str
    hour: int
    minute: int
    hour_branch_number: int
    hour_branch_name: str

    def as_dict(self) -> dict[str, object]:
        return {
            "local": _format_local(self.local),
            "utc": _format_utc(self.utc),
            "utc_offset": self.utc_offset,
            "civil_date": self.civil_date,
            "hour": self.hour,
            "minute": self.minute,
            "hour_branch_number": self.hour_branch_number,
            "hour_branch_name": self.hour_branch_name,
            "day_boundary": "local civil date changes at 00:00; 23:00 keeps this civil date",
            "timezone": "Asia/Shanghai",
        }


def hour_branch_number(hour: int) -> int:
    if hour == 23 or hour == 0:
        return 1
    if not 0 <= hour <= 22:
        raise TimePolicyError(f"小时超出 0–23：{hour}")
    return (hour + 1) // 2 + 1


def require_aware(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise TimePolicyError("拒绝无时区的时间。请传入带偏移的时间，再换算到 Asia/Shanghai。")
    return moment.astimezone(SHANGHAI)


def describe_instant(moment: datetime) -> CivilInstant:
    local = require_aware(moment)
    offset = local.utcoffset()
    if offset is None:
        raise TimePolicyError("Asia/Shanghai 没有给出偏移。")
    branch = hour_branch_number(local.hour)
    return CivilInstant(
        local=local,
        utc=local.astimezone(timezone.utc),
        utc_offset=format_offset(offset),
        civil_date=local.date().isoformat(),
        hour=local.hour,
        minute=local.minute,
        hour_branch_number=branch,
        hour_branch_name=BRANCH_NAMES[branch - 1],
    )


def format_offset(offset: timedelta) -> str:
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    minutes = abs(total_minutes)
    hour, minute = divmod(minutes, 60)
    return f"{sign}{hour:02d}:{minute:02d}"


def _format_local(moment: datetime) -> str:
    base = moment.strftime("%Y-%m-%dT%H:%M:%S")
    return base + format_offset(moment.utcoffset() or timedelta(0))


def _format_utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
