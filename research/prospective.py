# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Prospective locks compared with a public commit time.

Local content hashes are not issuance times. issued_prospectively is the
boolean result of public_commit < event_start, or null when the public
commit time is absent. It is never stored as a constant true.
Settlement rows live in a separate append-only table.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from research.calendar_time import SHANGHAI
from research.experiment import dumps_jsonl
from research.mapping import probability_from_lines, structural_features
from research.meihua import cast_from_datetime
from research.protocol import load_protocol, sha256_bytes, sha256_obj

EARLIEST_CIVIL_DATE = date(2026, 11, 18)
WINDOW_DAYS = 30
OLD_LEDGER = Path(__file__).resolve().parent / "experiments" / "offline_v1" / "future_ledger.jsonl"
OLD_RUN_LOG = Path(__file__).resolve().parent / "experiments" / "offline_v1" / "run_log.json"
PROSPECTIVE_DIR = Path(__file__).resolve().parent / "experiments" / "prospective_v2"


class ProspectiveError(ValueError):
    """The row cannot be treated as an issued forecast or as a scored event."""


def event_bounds(civil: date) -> tuple[datetime, datetime]:
    start = datetime(civil.year, civil.month, civil.day, 0, 0, 0, tzinfo=SHANGHAI)
    return start, start + timedelta(days=1)


def as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ProspectiveError("公开锚点必须带时区。")
    return moment.astimezone(timezone.utc)


def issued_before_event(public_commit: datetime | None, event_start: datetime) -> bool | None:
    """Return a comparison, or null when no public commit time exists."""

    if public_commit is None:
        return None
    return as_utc(public_commit) < as_utc(event_start)


def first_unstarted_civil_date(public_commit: datetime) -> date:
    """First local midnight strictly after the commit, and not before 18 Nov 2026."""

    local = as_utc(public_commit).astimezone(SHANGHAI)
    candidate = local.date() + timedelta(days=1)
    if candidate < EARLIEST_CIVIL_DATE:
        candidate = EARLIEST_CIVIL_DATE
    return candidate


def planned_dates(public_commit: datetime | None = None) -> list[date]:
    if public_commit is None:
        start = EARLIEST_CIVIL_DATE
    else:
        start = first_unstarted_civil_date(public_commit)
    return [start + timedelta(days=offset) for offset in range(WINDOW_DAYS)]


def content_lock(civil: date) -> dict[str, Any]:
    """Hash the cast. This hash is not a public issuance time."""

    protocol, digest = load_protocol()
    start, end = event_bounds(civil)
    cast = cast_from_datetime(start)
    features = structural_features(cast)
    p_rule = probability_from_lines(list(cast["lines_bottom_up"]))
    task = protocol["task"]
    question = task["question_template"].format(date=civil.isoformat())
    event_id = f"shanghai-precip-ge1mm-{civil.isoformat()}"
    input_body = {
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": digest,
        "event_id": event_id,
        "question": question,
        "event_start": start.isoformat(),
        "event_end": end.isoformat(),
        "requested_latitude": task["requested_latitude"],
        "requested_longitude": task["requested_longitude"],
        "rule_inputs": cast["inputs"],
        "lunar_year": cast["lunar"]["lunar_year"],
        "leap_month": cast["lunar"]["leap_month"],
    }
    input_hash = sha256_obj(input_body)
    prediction_body = {
        "input_sha256": input_hash,
        "mapping_id": "P-MAP-1",
        "mapping_status": "engineering_hypothesis_not_a_classical_probability",
        "p_rule": p_rule,
        "cast_sha256": cast["cast_sha256"],
        "features": features,
        "hexagram": cast["hexagram"],
        "changed_hexagram": cast["changed_hexagram"],
    }
    return {
        "event_id": event_id,
        "record_class": "prospective_content_lock",
        "event_start": start.isoformat(),
        "event_end": end.isoformat(),
        "question": question,
        "cast": cast,
        "features": features,
        "p_rule": p_rule,
        "mapping_id": "P-MAP-1",
        "mapping_status": "engineering_hypothesis_not_a_classical_probability",
        "local_content_hash": {
            "input_sha256": input_hash,
            "prediction_sha256": sha256_obj(prediction_body),
            "is_public_commit_time": False,
        },
        "public_commit_time": None,
        "issued_prospectively": None,
        "eligibility": "pending_public_commit_comparison",
        "outcome": None,
        "scored": False,
    }


def apply_public_commit(row: dict[str, Any], public_commit: datetime, source: str) -> dict[str, Any]:
    start = datetime.fromisoformat(row["event_start"])
    flag = issued_before_event(public_commit, start)
    copied = dict(row)
    copied["public_commit_time"] = as_utc(public_commit).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    copied["public_anchor_source"] = source
    copied["issued_prospectively"] = flag
    copied["eligibility"] = "eligible_unscored" if flag else "invalid_excluded"
    if flag:
        copied["exclusion_reason"] = None
    else:
        copied["exclusion_reason"] = "公开提交时间不早于当地日的 event_start，不能当作完整日的事前预测。"
    copied["outcome"] = None
    copied["scored"] = False
    return copied


def assert_scorable(rows: list[dict[str, Any]]) -> None:
    """Missing outcomes are never scored. Prospective rows stay unscored."""

    if not rows:
        raise ProspectiveError("没有可评分的行。")
    for row in rows:
        if row.get("outcome") not in (0, 1):
            raise ProspectiveError(f"{row.get('event_id')} 缺失结局，不评分。")
        if row.get("record_class") == "prospective_content_lock" or row.get("scored") is False:
            raise ProspectiveError(f"{row.get('event_id')} 属于未结算前瞻，不评分。")


def old_queue_disposition() -> dict[str, Any]:
    raw = OLD_LEDGER.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ProspectiveError("旧台账含有 BOM。")
    log = json.loads(OLD_RUN_LOG.read_text(encoding="utf-8"))
    computed = datetime.fromisoformat(log["computed_at"]).astimezone(SHANGHAI)
    rows = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        original = json.loads(line)
        start = datetime.fromisoformat(original["information_time_local"])
        end = start + timedelta(days=1)
        reasons = [
            "issued_prospectively 由当时的生成器写成常数 true，没有比较公开提交时间与 event_start。",
            "input_sha256 和 prediction_sha256 是本地内容哈希，不是服务器可验证的提交时间。",
            "结算写在同一行里，而不是另表追加。",
        ]
        if computed >= end:
            reasons.insert(0, "该当地日在 offline_v1 的 computed_at 之前已经结束。")
        elif computed >= start:
            reasons.insert(0, "该当地日在 offline_v1 的 computed_at 时已经开始，不是完整的事前日。")
        else:
            reasons.insert(0, "当地日的 0 点晚于当时的 computed_at，但这份旧队列的发行标记无效，所以整行退出前瞻。")
        rows.append(
            {
                "event_id": original["event_id"],
                "event_start": original["information_time_local"],
                "status": "invalid",
                "excluded": True,
                "outcome_in_old_file": original["outcome"],
                "reasons": reasons,
            }
        )
    return {
        "source_file": "research/experiments/offline_v1/future_ledger.jsonl",
        "source_sha256": sha256_bytes(raw),
        "source_bytes_unchanged": True,
        "computed_at_read_from_run_log": log["computed_at"],
        "computed_at_shanghai": computed.isoformat(),
        "queue_status": "invalid_excluded",
        "rows": rows,
    }


def build_unanchored_ledger() -> list[dict[str, Any]]:
    return [content_lock(civil) for civil in planned_dates(None)]


def write_prospective_files() -> None:
    PROSPECTIVE_DIR.mkdir(parents=True, exist_ok=True)
    ledger = build_unanchored_ledger()
    (PROSPECTIVE_DIR / "ledger.jsonl").write_bytes(dumps_jsonl(ledger).encode("utf-8"))
    settlement = PROSPECTIVE_DIR / "settlement.jsonl"
    if not settlement.exists():
        settlement.write_bytes(b"")
    disposition_path = OLD_LEDGER.parent / "future_ledger_disposition.json"
    disposition_path.write_text(
        json.dumps(old_queue_disposition(), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
