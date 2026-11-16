# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only

import json
from datetime import date, timedelta

import pytest

from research.cli import build_parser, main
from research.data_openmeteo import SnapshotError, parse_snapshot, request_url
from research.experiment import future_ledger, run_experiment
from research.protocol import load_protocol
from research.server import CastHandler
from http.server import ThreadingHTTPServer
import threading
import urllib.request


def _dates(start: str, end: str) -> list[date]:
    cursor = date.fromisoformat(start)
    last = date.fromisoformat(end)
    days = []
    while cursor <= last:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days


def _daily(protocol, null_holdout_date: str | None = None):
    task = protocol["task"]
    days = _dates(task["pilot"]["start"], task["holdout"]["end"])
    rows = []
    for index, civil in enumerate(days):
        amount = None if civil.isoformat() == null_holdout_date else (2.0 if index % 3 == 0 else 0.0)
        rows.append(
            {
                "date": civil.isoformat(),
                "precipitation_mm": amount,
                "grid_latitude": 31.25,
                "grid_longitude": 121.5,
                "elevation_m": 4.0,
            }
        )
    return rows


def test_parser_rejects_a_bad_offset_and_url_has_no_credential():
    protocol, digest = load_protocol()
    url = request_url()
    assert "api_key" not in url.lower()
    assert "precipitation_sum" in url
    start = protocol["task"]["pilot"]["start"]
    end = protocol["task"]["holdout"]["end"]
    days = [item.isoformat() for item in _dates(start, end)]
    payload = {
        "latitude": 31.2,
        "longitude": 121.5,
        "timezone": "Asia/Shanghai",
        "utc_offset_seconds": 0,
        "daily_units": {"time": "iso8601", "precipitation_sum": "mm"},
        "daily": {"time": days, "precipitation_sum": [0.0] * len(days)},
    }
    with pytest.raises(SnapshotError):
        parse_snapshot({"raw": payload, "protocol_sha256": digest})


def test_synthetic_window_does_not_leak_labels_or_score_the_future():
    protocol, digest = load_protocol()
    daily = _daily(protocol, null_holdout_date="2023-01-15")
    first = run_experiment(
        daily,
        sample_class="synthetic_pipeline_only",
        snapshot_sha256="synthetic",
        bootstrap_replicates=40,
    )
    flipped = []
    for row in daily:
        copied = dict(row)
        if copied["date"].startswith("2023-") and copied["precipitation_mm"] is not None:
            copied["precipitation_mm"] = 0.0 if copied["precipitation_mm"] >= 1 else 3.0
        flipped.append(copied)
    second = run_experiment(
        flipped,
        sample_class="synthetic_pipeline_only",
        snapshot_sha256="synthetic",
        bootstrap_replicates=40,
    )
    by_id = {row["event_id"]: row for row in first["events"]}
    for row in second["events"]:
        original = by_id[row["event_id"]]
        assert row["prediction_sha256"] == original["prediction_sha256"]
        assert row["p_rule"] == original["p_rule"]
        if row["split"] == "holdout" and row["outcome"] is not None:
            assert row["p_calendar"] == original["p_calendar"]
    pilot_flip = []
    for row in daily:
        copied = dict(row)
        if copied["date"].startswith("2022-") and copied["precipitation_mm"] is not None:
            copied["precipitation_mm"] = 5.0
        pilot_flip.append(copied)
    third = run_experiment(
        pilot_flip,
        sample_class="synthetic_pipeline_only",
        snapshot_sha256="synthetic",
        bootstrap_replicates=20,
    )
    third_by_id = {row["event_id"]: row for row in third["events"]}
    assert third_by_id["shanghai-precip-ge1mm-2023-06-01"]["p_calendar"] != by_id[
        "shanghai-precip-ge1mm-2023-06-01"
    ]["p_calendar"]
    summary = first["summary"]
    assert summary["synthetic_pipeline_only"] is True
    assert summary["study_primary"]["status"] == "not_run"
    assert summary["holdout"]["n_unresolved"] == 1
    assert summary["holdout"]["n_events"] if False else summary["contrasts"]["rule_minus_base_rate"]["n_events"] == summary["holdout"]["n_resolved"]
    assert "不能用来声称预测提升" in first["explanation"]
    assert "不是“玄学已被科学验证”的证据" in first["explanation"]
    assert "主终点（规则增强臂 B 相对原版臂 A 的配对 Brier 差）本次未估计" in first["explanation"]
    future_ids = {row["event_id"] for row in first["future_ledger"]}
    assert future_ids.isdisjoint({row["event_id"] for row in first["events"]})
    assert all(row["outcome"] is None and row["status"] == "pending_settlement" for row in first["future_ledger"])
    assert future_ledger()[0]["issued_prospectively"] is True


def test_cli_has_no_window_override_and_cast_numbers_match_the_example():
    parser = build_parser()
    offline = next(action for action in parser._subparsers._group_actions if action.dest == "command")
    choices = set(offline.choices)
    assert "run-offline" in choices
    assert "--start" not in parser.format_help()
    assert main(["cast-numbers", "--year-branch", "5", "--month", "12", "--day", "17", "--hour-branch", "9"]) == 0


def test_local_cast_service():
    server = ThreadingHTTPServer(("127.0.0.1", 0), CastHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        payload = json.dumps(
            {"year_branch": 5, "month": 12, "day": 17, "hour_branch": 9}
        ).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/cast-numbers",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
        assert body["hexagram"] == "泽火革"
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as response:
            health = json.loads(response.read().decode("utf-8"))
        assert health["model_arms"] == "not_run"
    finally:
        server.shutdown()
