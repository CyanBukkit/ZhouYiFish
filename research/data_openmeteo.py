# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Open-Meteo archive snapshot. Missing values stay missing; nothing is invented."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any

from research.protocol import load_protocol

USER_AGENT = "ZhouYiFish-research/0.1 (exploratory historical snapshot; no credentials)"


class SnapshotError(ValueError):
    """The settlement file does not match the frozen task."""


def protocol_windows() -> tuple[date, date, date, date]:
    protocol, _digest = load_protocol()
    task = protocol["task"]
    pilot_start = date.fromisoformat(task["pilot"]["start"])
    pilot_end = date.fromisoformat(task["pilot"]["end"])
    holdout_start = date.fromisoformat(task["holdout"]["start"])
    holdout_end = date.fromisoformat(task["holdout"]["end"])
    if pilot_end + timedelta(days=1) != holdout_start:
        raise SnapshotError("先导期和留出集必须首尾相接，否则不能用一份连续快照。")
    if pilot_start > pilot_end or holdout_start > holdout_end:
        raise SnapshotError("任务日期窗口颠倒。")
    return pilot_start, pilot_end, holdout_start, holdout_end


def request_url() -> str:
    protocol, _digest = load_protocol()
    task = protocol["task"]
    start, _pilot_end, _holdout_start, end = protocol_windows()
    query = {
        "latitude": task["requested_latitude"],
        "longitude": task["requested_longitude"],
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "precipitation_sum",
        "timezone": "Asia/Shanghai",
    }
    return task["settlement"]["endpoint"] + "?" + urllib.parse.urlencode(query)


def fetch_snapshot() -> dict[str, Any]:
    url = request_url()
    if any(token in url.lower() for token in ("api_key", "apikey", "token=", "secret")):
        raise SnapshotError("结算请求不应携带凭据。")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read()
    payload = json.loads(raw.decode("utf-8"))
    protocol, digest = load_protocol()
    settlement = protocol["task"]["settlement"]
    return {
        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": digest,
        "request_url": url,
        "license": settlement["license"],
        "license_url": settlement["license_url"],
        "attribution": settlement["attribution"],
        "source": settlement["source"],
        "raw": payload,
    }


def parse_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    protocol, _digest = load_protocol()
    task = protocol["task"]
    settlement = task["settlement"]
    payload = snapshot["raw"]
    if not isinstance(payload, dict) or "daily" not in payload:
        reason = payload.get("reason") if isinstance(payload, dict) else "not json"
        raise SnapshotError(f"Open-Meteo 响应没有 daily 序列：{reason}")
    if payload.get("timezone") != "Asia/Shanghai":
        raise SnapshotError(f"结算时区不是 Asia/Shanghai：{payload.get('timezone')}")
    if int(payload.get("utc_offset_seconds")) != int(settlement["required_utc_offset_seconds"]):
        raise SnapshotError("结算日界偏移不是 28800 秒，拒绝把另一套日界混进任务。")
    units = payload.get("daily_units") or {}
    if units.get("precipitation_sum") != "mm":
        raise SnapshotError(f"降水量单位不是 mm：{units.get('precipitation_sum')}")
    daily = payload["daily"]
    times = daily.get("time")
    amounts = daily.get("precipitation_sum")
    if not isinstance(times, list) or not isinstance(amounts, list) or len(times) != len(amounts):
        raise SnapshotError("日期和降水量长度不一致。")
    start, _pilot_end, _holdout_start, end = protocol_windows()
    expected = _dates(start, end)
    if times != [item.isoformat() for item in expected]:
        raise SnapshotError("快照日期与协议窗口不是逐日连续对齐。")
    rows = []
    for civil, amount in zip(expected, amounts):
        if amount is None:
            millimeters = None
        else:
            millimeters = float(amount)
        rows.append(
            {
                "date": civil.isoformat(),
                "precipitation_mm": millimeters,
                "grid_latitude": payload.get("latitude"),
                "grid_longitude": payload.get("longitude"),
                "elevation_m": payload.get("elevation"),
            }
        )
    return rows


def split_name(civil: str) -> str:
    protocol, _digest = load_protocol()
    if protocol["task"]["pilot"]["start"] <= civil <= protocol["task"]["pilot"]["end"]:
        return "pilot"
    if protocol["task"]["holdout"]["start"] <= civil <= protocol["task"]["holdout"]["end"]:
        return "holdout"
    raise SnapshotError(f"{civil} 不在先导期或留出集。")


def _dates(start: date, end: date) -> list[date]:
    days = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return days
