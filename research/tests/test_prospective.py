# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from research.calendar_time import SHANGHAI
from research.data_openmeteo import SnapshotError, clean_precipitation
from research.prospective import (
    EARLIEST_CIVIL_DATE,
    OLD_LEDGER,
    WINDOW_DAYS,
    apply_public_commit,
    assert_scorable,
    build_unanchored_ledger,
    content_lock,
    first_unstarted_civil_date,
    issued_before_event,
    old_queue_disposition,
    planned_dates,
)

ROOT = Path(__file__).resolve().parents[2]


def test_source_never_assigns_issued_prospectively_true():
    for relative in ("research/experiment.py", "research/prospective.py", "research/cli.py"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "issued_prospectively=True" not in text
        assert "issued_prospectively = True" not in text


def test_old_freeze_excludes_16_and_17_and_the_whole_old_queue():
    freeze = datetime(2026, 11, 17, 0, 7, 55, tzinfo=SHANGHAI)
    nov16 = datetime(2026, 11, 16, 0, 0, tzinfo=SHANGHAI)
    nov17 = datetime(2026, 11, 17, 0, 0, tzinfo=SHANGHAI)
    nov18 = datetime(2026, 11, 18, 0, 0, tzinfo=SHANGHAI)
    assert issued_before_event(freeze, nov16) is False
    assert issued_before_event(freeze, nov17) is False
    assert issued_before_event(freeze, nov18) is True
    assert issued_before_event(None, nov18) is None
    disposition = old_queue_disposition()
    assert disposition["queue_status"] == "invalid_excluded"
    assert len(disposition["rows"]) == 30
    by_id = {row["event_id"]: row for row in disposition["rows"]}
    assert by_id["shanghai-precip-ge1mm-2026-11-16"]["status"] == "invalid"
    assert by_id["shanghai-precip-ge1mm-2026-11-17"]["excluded"] is True
    assert "已经结束" in "".join(by_id["shanghai-precip-ge1mm-2026-11-16"]["reasons"])
    assert "已经开始" in "".join(by_id["shanghai-precip-ge1mm-2026-11-17"]["reasons"])
    assert all(row["outcome_in_old_file"] is None for row in disposition["rows"])
    assert disposition["source_sha256"] == __import__("hashlib").sha256(OLD_LEDGER.read_bytes()).hexdigest()


def test_new_window_starts_on_or_after_18_november_and_is_not_scored():
    anchor = datetime(2026, 11, 16, 16, 10, tzinfo=timezone.utc)
    assert first_unstarted_civil_date(anchor) == date(2026, 11, 18)
    days = planned_dates(anchor)
    assert days[0] == EARLIEST_CIVIL_DATE
    assert len(days) == WINDOW_DAYS == 30
    assert days[-1] == date(2026, 12, 17)
    locked = content_lock(days[0])
    assert locked["issued_prospectively"] is None
    assert locked["local_content_hash"]["is_public_commit_time"] is False
    eligible = apply_public_commit(locked, anchor, "unit-test-clock")
    assert eligible["issued_prospectively"] is True
    assert datetime.fromisoformat(eligible["public_commit_time"]) < datetime.fromisoformat(eligible["event_start"])
    assert eligible["outcome"] is None and eligible["scored"] is False
    late = apply_public_commit(locked, datetime(2026, 11, 18, 0, 0, tzinfo=SHANGHAI), "too-late")
    assert late["eligibility"] == "invalid_excluded"
    assert late["issued_prospectively"] is False
    with pytest.raises(Exception, match="不评分"):
        assert_scorable([eligible])
    historical_ids = {
        json.loads(line)["event_id"]
        for line in (ROOT / "research/experiments/offline_v1/predictions.jsonl").read_text().splitlines()
    }
    prospective_ids = {row["event_id"] for row in build_unanchored_ledger()}
    assert historical_ids.isdisjoint(prospective_ids)
    assert all(item >= date(2026, 11, 18) for item in days)


def test_missing_precipitation_stays_missing_and_zero_is_a_real_zero():
    assert clean_precipitation(None) is None
    assert clean_precipitation(0) == 0.0
    assert clean_precipitation(1.5) == 1.5
    with pytest.raises(SnapshotError):
        clean_precipitation(-0.1)
    with pytest.raises(SnapshotError):
        clean_precipitation(float("nan"))
    from research.experiment import _outcome

    assert _outcome(None, 1.0) is None
    assert _outcome(0.0, 1.0) == 0
    with pytest.raises(ValueError):
        _outcome(-1, 1.0)


def test_github_anchor_is_before_every_eligible_event_start():
    anchor_path = ROOT / "research/experiments/prospective_v2/public_anchor.json"
    eligibility_path = ROOT / "research/experiments/prospective_v2/eligibility.jsonl"
    ledger_path = ROOT / "research/experiments/prospective_v2/ledger.jsonl"
    settlement_path = ROOT / "research/experiments/prospective_v2/settlement.jsonl"
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    moment = datetime.fromisoformat(anchor["github_committer_date"].replace("Z", "+00:00"))
    derived = [
        apply_public_commit(json.loads(line), moment, anchor["source"])
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    stored = [json.loads(line) for line in eligibility_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert stored == derived
    assert len(stored) == 30
    assert settlement_path.read_bytes() == b""
    for row in stored:
        public_time = datetime.fromisoformat(row["public_commit_time"])
        start = datetime.fromisoformat(row["event_start"])
        assert public_time < start
        assert row["issued_prospectively"] is True
        assert row["outcome"] is None and row["scored"] is False
        assert row["local_content_hash"]["is_public_commit_time"] is False
        assert row["public_commit_time"] != row["local_content_hash"]["input_sha256"]
    with pytest.raises(Exception, match="不评分"):
        assert_scorable(stored)


def test_public_commit_equal_to_midnight_is_not_early_enough():
    start = datetime(2026, 11, 18, 0, 0, tzinfo=SHANGHAI)
    assert issued_before_event(start, start) is False
    later = start - timedelta(seconds=1)
    assert issued_before_event(later, start) is True
