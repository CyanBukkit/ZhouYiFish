# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only

from datetime import date, datetime, timezone

import pytest
from zhdate import CHINESENEWYEAR

from research.calendar_time import SHANGHAI, TimePolicyError, describe_instant, hour_branch_number
from research.lunar_calendar import lunar_from_civil_date
from research.meihua import cast_from_datetime

# Civil date, lunar year, month number, day, leap.
# Read from Hong Kong Observatory conversion tables, including the second
# occurrence of a month name as that year's leap month.
HKO_VECTORS = [
    ("2024-02-09", 2023, 12, 30, False),
    ("2024-02-10", 2024, 1, 1, False),
    ("2024-02-04", 2023, 12, 25, False),
    ("2024-01-01", 2023, 11, 20, False),
    ("2024-01-11", 2023, 12, 1, False),
    ("2023-01-21", 2022, 12, 30, False),
    ("2023-01-22", 2023, 1, 1, False),
    ("2023-02-20", 2023, 2, 1, False),
    ("2023-03-21", 2023, 2, 30, False),
    ("2023-03-22", 2023, 2, 1, True),
    ("2023-04-20", 2023, 3, 1, False),
    ("2020-04-23", 2020, 4, 1, False),
    ("2020-05-23", 2020, 4, 1, True),
    ("2020-06-21", 2020, 5, 1, False),
    ("2022-01-01", 2021, 11, 29, False),
    ("2022-01-03", 2021, 12, 1, False),
    ("2022-02-01", 2022, 1, 1, False),
    ("2026-02-17", 2026, 1, 1, False),
]


def test_zhdate_new_year_table_matches_checked_hko_dates():
    assert CHINESENEWYEAR[2020 - 1900] == "20200125"
    assert CHINESENEWYEAR[2022 - 1900] == "20220201"
    assert CHINESENEWYEAR[2023 - 1900] == "20230122"
    assert CHINESENEWYEAR[2024 - 1900] == "20240210"
    assert CHINESENEWYEAR[2026 - 1900] == "20260217"


@pytest.mark.parametrize("civil, year, month, day, leap", HKO_VECTORS)
def test_lunar_fields_match_hko_vectors(civil, year, month, day, leap):
    lunar = lunar_from_civil_date(date.fromisoformat(civil))
    assert lunar["lunar_year"] == year
    assert lunar["lunar_month_number"] == month
    assert lunar["lunar_day"] == day
    assert lunar["leap_month"] is leap


def test_year_branch_changes_at_spring_festival_not_lichun_or_january():
    new_year_eve = _at(2024, 2, 9, 23)
    new_year = _at(2024, 2, 10, 0)
    lichun = _at(2024, 2, 4, 0)
    january = _at(2024, 1, 1, 0)
    assert new_year_eve["inputs"]["year_branch_number"] == 4
    assert new_year_eve["lunar"]["year_branch_name"] == "卯"
    assert new_year["inputs"]["year_branch_number"] == 5
    assert new_year["lunar"]["year_branch_name"] == "辰"
    assert lichun["inputs"]["year_branch_number"] == 4
    assert january["inputs"]["year_branch_number"] == 4
    assert january["lunar"]["lunar_month_number"] == 11


def test_zi_hour_keeps_the_civil_date_and_midnight_starts_the_next_one():
    late = _at(2024, 6, 15, 23)
    noon = _at(2024, 6, 15, 12)
    nxt = _at(2024, 6, 16, 0)
    assert late["time"]["civil_date"] == "2024-06-15"
    assert late["inputs"]["hour_branch_number"] == 1
    assert late["lunar"]["lunar_day"] == noon["lunar"]["lunar_day"]
    assert late["lunar"]["lunar_month_number"] == noon["lunar"]["lunar_month_number"]
    assert noon["inputs"]["hour_branch_number"] == 7
    assert nxt["time"]["civil_date"] == "2024-06-16"
    assert nxt["inputs"]["hour_branch_number"] == 1
    assert nxt["lunar"]["lunar_day"] != late["lunar"]["lunar_day"] or nxt["lunar"]["lunar_month_number"] != late["lunar"]["lunar_month_number"]


def test_utc_instant_is_converted_before_the_lunar_date():
    cast = cast_from_datetime(datetime(2024, 2, 9, 16, 0, tzinfo=timezone.utc))
    assert cast["time"]["local"].startswith("2024-02-10T00:00:00+08:00")
    assert cast["time"]["utc"] == "2024-02-09T16:00:00+00:00"
    assert cast["lunar"]["lunar_year"] == 2024
    assert cast["seed"] is None


def test_leap_month_uses_the_same_number_and_can_repeat_a_cast():
    regular = _at(2023, 2, 20, 0)
    leap = _at(2023, 3, 22, 0)
    assert regular["lunar"]["leap_month"] is False
    assert leap["lunar"]["leap_month"] is True
    assert regular["inputs"] == leap["inputs"]
    assert regular["lines_bottom_up"] == leap["lines_bottom_up"]
    assert regular["lunar"]["leap_month"] != leap["lunar"]["leap_month"]


def test_hour_branch_table_and_dst_offset_are_recorded():
    expected = {
        0: 1,
        1: 2,
        2: 2,
        3: 3,
        10: 6,
        11: 7,
        12: 7,
        15: 9,
        22: 12,
        23: 1,
    }
    for hour, branch in expected.items():
        assert hour_branch_number(hour) == branch
    summer = describe_instant(datetime(1988, 7, 15, 12, tzinfo=SHANGHAI))
    winter = describe_instant(datetime(2024, 7, 15, 12, tzinfo=SHANGHAI))
    assert summer.utc_offset == "+09:00"
    assert winter.utc_offset == "+08:00"
    with pytest.raises(TimePolicyError):
        describe_instant(datetime(2024, 6, 15, 0, 0))


def _at(year: int, month: int, day: int, hour: int) -> dict:
    return cast_from_datetime(datetime(year, month, day, hour, tzinfo=SHANGHAI))
