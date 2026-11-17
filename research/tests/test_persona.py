# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only

import json
from datetime import datetime
from pathlib import Path

import pytest

from research.bazi import four_pillars, term_instant
from research.human_behavior import ConsentBlocked, real_validation_status, validate_real_record
from research.persona import (
    assert_not_validation_label,
    build_fictional_persona,
    simulated_cooperation_output,
)
from research.sandbox_demo import demo_bundle

ROOT = Path(__file__).resolve().parents[2]


def test_year_pillar_follows_lichun_instant_not_lunar_new_year():
    lichun = term_instant(2024, "立春")
    assert lichun.isoformat().startswith("2024-02-04T16:26:")
    before = four_pillars(datetime.fromisoformat("2024-02-04T10:00:00+08:00"), hour_known=True)
    after = four_pillars(datetime.fromisoformat("2024-02-04T18:00:00+08:00"), hour_known=True)
    lunar_new_year = four_pillars(datetime.fromisoformat("2024-02-10T00:00:00+08:00"), hour_known=True)
    assert before["year_pillar"] == "癸卯"
    assert before["month_pillar"] == "乙丑"
    assert after["year_pillar"] == "甲辰"
    assert after["month_pillar"] == "丙寅"
    assert before["day_pillar"] == after["day_pillar"]
    assert lunar_new_year["year_pillar"] == "甲辰"
    assert lunar_new_year["lunar_month_used_as_bazi_month"] is False


def test_missing_hour_does_not_invent_a_chart():
    result = four_pillars(datetime.fromisoformat("1881-09-25T00:00:00+08:00"), hour_known=False)
    assert result["status"] == "not_applicable"
    assert result["pillars"] is None


def test_sandbox_hypothesis_cannot_validate_itself():
    persona = build_fictional_persona(
        "sandbox-focal-01",
        datetime.fromisoformat("2001-06-15T10:30:00+08:00"),
        display_name="沙盒甲",
        living_place_label="虚构街区",
    )
    assert persona["fictional"] is True
    assert persona["occupation_label"] is None
    with pytest.raises(Exception, match="不能当作"):
        assert_not_validation_label(persona["occupation_hypothesis"])
    simulated = simulated_cooperation_output("sandbox-focal-01", "cooperate")
    with pytest.raises(Exception, match="不能当作"):
        assert_not_validation_label(simulated)


def test_historical_cases_have_no_hour_and_no_ranking():
    payload = json.loads((ROOT / "research/cases/public_figures.json").read_text(encoding="utf-8"))
    assert payload["best_worst_ranking"] == "not_applied"
    assert payload["ordinary_controls"] == "not_found"
    assert payload["not_a_blind_test"]
    for case in payload["cases"]:
        assert case["hour"] is None
        assert case["chart_status"] == "not_applicable_missing_hour"
        assert case["deceased"] is True
        assert case["birth_date_source"]["url"].startswith("http")
        assert case["career_source"]["url"].startswith("http")


def test_real_validation_is_blocked_without_consent():
    status = real_validation_status()
    assert status["status"] == "blocked"
    assert status["four_arm_model_run"] is False
    with pytest.raises(ConsentBlocked):
        validate_real_record({"authorization": "public_web", "domain": "choice"})
    bundle = demo_bundle()
    assert bundle["weather_answers_this_question"] is False
    assert bundle["real_validation"]["records_in_repo"] == 0
    assert bundle["historical_cases"]["accuracy_scored"] is False
    assert bundle["graph"]["fictional"] is True


def test_weather_audit_is_marked_out_of_scope():
    text = (ROOT / "research/experiments/offline_v1/OUT_OF_SCOPE.md").read_text(encoding="utf-8")
    assert "out_of_scope" in text or "超出当前问题范围" in text
    assert (ROOT / "research/experiments/offline_v1/future_ledger.jsonl").exists()
