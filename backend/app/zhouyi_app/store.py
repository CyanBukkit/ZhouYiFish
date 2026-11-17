# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Local SQLite archive. No model key is stored."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_STORES: dict[str, "Store"] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class Store:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._write = threading.Lock()
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS personas (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    fictional INTEGER NOT NULL,
                    birth_date TEXT,
                    birth_time TEXT,
                    timezone TEXT NOT NULL,
                    birth_place TEXT,
                    known_occupation TEXT,
                    living_background TEXT,
                    notes TEXT,
                    luck_mode TEXT,
                    luck_sex TEXT,
                    luck_direction TEXT,
                    liunian_year INTEGER
                );
                CREATE TABLE IF NOT EXISTS charts (
                    persona_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS relations (
                    id TEXT PRIMARY KEY,
                    persona_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS hypotheses (
                    id TEXT PRIMARY KEY,
                    persona_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    text TEXT NOT NULL,
                    source TEXT NOT NULL,
                    is_fact INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    persona_id TEXT,
                    persona_name TEXT,
                    scenario TEXT NOT NULL,
                    status TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    model TEXT,
                    compare_model TEXT,
                    budget INTEGER NOT NULL,
                    requests_used INTEGER NOT NULL,
                    error TEXT,
                    result_json TEXT,
                    cancel_requested INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS experiments (
                    id TEXT PRIMARY KEY,
                    persona_id TEXT,
                    persona_name TEXT,
                    scenario TEXT NOT NULL,
                    status TEXT NOT NULL,
                    model TEXT,
                    budget INTEGER NOT NULL,
                    requests_used INTEGER NOT NULL,
                    error TEXT,
                    result_json TEXT,
                    cancel_requested INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            columns = {row[1] for row in db.execute("PRAGMA table_info(personas)")}
            for name, typedef in (
                ("luck_mode", "TEXT"),
                ("luck_sex", "TEXT"),
                ("luck_direction", "TEXT"),
                ("liunian_year", "INTEGER"),
            ):
                if name not in columns:
                    db.execute(f"ALTER TABLE personas ADD COLUMN {name} {typedef}")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, check_same_thread=False)
        db.row_factory = sqlite3.Row
        return db

    def upsert_persona(self, fields: dict[str, Any], persona_id: str | None = None) -> dict[str, Any]:
        stamp = now()
        with self._write:
            with self._connect() as db:
                current = None
                if persona_id is not None:
                    current = db.execute("SELECT id FROM personas WHERE id = ?", (persona_id,)).fetchone()
                if current is None:
                    persona_id = persona_id or new_id("persona")
                    db.execute(
                        """
                        INSERT INTO personas (
                            id, created_at, updated_at, display_name, fictional, birth_date,
                            birth_time, timezone, birth_place, known_occupation, living_background, notes,
                            luck_mode, luck_sex, luck_direction, liunian_year
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            persona_id,
                            stamp,
                            stamp,
                            fields["display_name"],
                            1 if fields["fictional"] else 0,
                            fields.get("birth_date") or None,
                            fields.get("birth_time") or None,
                            fields["timezone"],
                            fields.get("birth_place") or "",
                            fields.get("known_occupation") or "",
                            fields.get("living_background") or "",
                            fields.get("notes") or "",
                            fields.get("luck_mode") or "",
                            fields.get("luck_sex") or "",
                            fields.get("luck_direction") or "",
                            fields.get("liunian_year"),
                        ),
                    )
                else:
                    db.execute(
                        """
                        UPDATE personas SET updated_at=?, display_name=?, fictional=?, birth_date=?,
                            birth_time=?, timezone=?, birth_place=?, known_occupation=?,
                            living_background=?, notes=?, luck_mode=?, luck_sex=?, luck_direction=?,
                            liunian_year=? WHERE id=?
                        """,
                        (
                            stamp,
                            fields["display_name"],
                            1 if fields["fictional"] else 0,
                            fields.get("birth_date") or None,
                            fields.get("birth_time") or None,
                            fields["timezone"],
                            fields.get("birth_place") or "",
                            fields.get("known_occupation") or "",
                            fields.get("living_background") or "",
                            fields.get("notes") or "",
                            fields.get("luck_mode") or "",
                            fields.get("luck_sex") or "",
                            fields.get("luck_direction") or "",
                            fields.get("liunian_year"),
                            persona_id,
                        ),
                    )
        return self.get_persona(persona_id)

    def get_persona(self, persona_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM personas WHERE id = ?", (persona_id,)).fetchone()
        if row is None:
            raise KeyError(persona_id)
        return self._persona(row)

    def list_personas(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM personas ORDER BY updated_at DESC").fetchall()
        return [self._persona(row) for row in rows]

    def delete_persona(self, persona_id: str) -> None:
        with self._write:
            with self._connect() as db:
                found = db.execute("SELECT id FROM personas WHERE id = ?", (persona_id,)).fetchone()
                if found is None:
                    raise KeyError(persona_id)
                db.execute("DELETE FROM relations WHERE persona_id = ?", (persona_id,))
                db.execute("DELETE FROM hypotheses WHERE persona_id = ?", (persona_id,))
                db.execute("DELETE FROM charts WHERE persona_id = ?", (persona_id,))
                db.execute("DELETE FROM personas WHERE id = ?", (persona_id,))

    def save_chart(self, persona_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._write:
            with self._connect() as db:
                db.execute(
                    """
                    INSERT INTO charts (persona_id, payload_json, updated_at) VALUES (?, ?, ?)
                    ON CONFLICT(persona_id) DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at
                    """,
                    (persona_id, json.dumps(payload, ensure_ascii=False), now()),
                )
        return payload

    def get_chart(self, persona_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT payload_json FROM charts WHERE persona_id = ?", (persona_id,)).fetchone()
        if row is None:
            return None
        return json.loads(row["payload_json"])

    def replace_rule_hypotheses(self, persona_id: str, texts: list[str]) -> list[dict[str, Any]]:
        with self._write:
            with self._connect() as db:
                db.execute(
                    "DELETE FROM hypotheses WHERE persona_id = ? AND source = ?",
                    (persona_id, "day_stem_table"),
                )
                for text in texts:
                    db.execute(
                        """
                        INSERT INTO hypotheses (id, persona_id, kind, text, source, is_fact, created_at)
                        VALUES (?, ?, ?, ?, ?, 0, ?)
                        """,
                        (new_id("hyp"), persona_id, "rule_candidate", text, "day_stem_table", now()),
                    )
        return self.list_hypotheses(persona_id)

    def add_hypothesis(self, persona_id: str, text: str, kind: str = "user_note") -> dict[str, Any]:
        item_id = new_id("hyp")
        with self._write:
            with self._connect() as db:
                db.execute(
                    """
                    INSERT INTO hypotheses (id, persona_id, kind, text, source, is_fact, created_at)
                    VALUES (?, ?, ?, ?, ?, 0, ?)
                    """,
                    (item_id, persona_id, kind, text, "user_note", now()),
                )
        return next(item for item in self.list_hypotheses(persona_id) if item["id"] == item_id)

    def list_hypotheses(self, persona_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM hypotheses WHERE persona_id = ? ORDER BY created_at",
                (persona_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "kind": row["kind"],
                "text": row["text"],
                "source": row["source"],
                "is_fact": False,
                "label": "规则候选或假设，不是用户已知事实",
            }
            for row in rows
        ]

    def add_relation(self, persona_id: str, name: str, relation: str, kind: str) -> dict[str, Any]:
        item_id = new_id("rel")
        with self._write:
            with self._connect() as db:
                db.execute(
                    """
                    INSERT INTO relations (id, persona_id, name, relation, kind, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (item_id, persona_id, name, relation, kind, now()),
                )
        return next(item for item in self.list_relations(persona_id) if item["id"] == item_id)

    def delete_relation(self, relation_id: str) -> None:
        with self._write:
            with self._connect() as db:
                deleted = db.execute("DELETE FROM relations WHERE id = ?", (relation_id,))
                if deleted.rowcount == 0:
                    raise KeyError(relation_id)

    def list_relations(self, persona_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM relations WHERE persona_id = ? ORDER BY created_at",
                (persona_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "relation": row["relation"],
                "kind": row["kind"],
                "is_fact": row["kind"] == "user_fact",
            }
            for row in rows
        ]

    def other_charts(self, exclude_id: str) -> list[dict[str, str]]:
        found = []
        for persona in self.list_personas():
            if persona["id"] == exclude_id:
                continue
            chart = self.get_chart(persona["id"])
            pillars = (chart or {}).get("pillars")
            if pillars:
                found.append({"id": persona["id"], "pillars": pillars, "name": persona["display_name"]})
        return found

    def create_task(self, table: str, fields: dict[str, Any]) -> dict[str, Any]:
        item_id = new_id("run" if table == "analyses" else "exp")
        stamp = now()
        columns = [
            "id",
            "persona_id",
            "persona_name",
            "scenario",
            "status",
            "budget",
            "requests_used",
            "error",
            "result_json",
            "cancel_requested",
            "created_at",
            "updated_at",
        ]
        values: list[Any] = [
            item_id,
            fields.get("persona_id"),
            fields.get("persona_name"),
            fields["scenario"],
            "queued",
            fields["budget"],
            0,
            None,
            None,
            0,
            stamp,
            stamp,
        ]
        if table == "analyses":
            columns[5:5] = ["engine", "model", "compare_model"]
            values[5:5] = [fields["engine"], fields.get("model"), fields.get("compare_model")]
        else:
            columns[5:5] = ["model"]
            values[5:5] = [fields.get("model")]
        with self._write:
            with self._connect() as db:
                db.execute(
                    f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                    values,
                )
        return self.get_task(table, item_id)

    def update_task(self, table: str, item_id: str, **changes: Any) -> dict[str, Any]:
        changes["updated_at"] = now()
        if "result" in changes:
            changes["result_json"] = json.dumps(changes.pop("result"), ensure_ascii=False)
        assignments = ", ".join(f"{key} = ?" for key in changes)
        with self._write:
            with self._connect() as db:
                db.execute(
                    f"UPDATE {table} SET {assignments} WHERE id = ?",
                    (*changes.values(), item_id),
                )
        return self.get_task(table, item_id)

    def request_cancel(self, table: str, item_id: str) -> dict[str, Any]:
        current = self.get_task(table, item_id)
        if current["status"] in {"succeeded", "failed", "cancelled"}:
            return current
        if current["status"] == "queued":
            return self.update_task(table, item_id, status="cancelled", cancel_requested=1, error="已在开始前取消")
        return self.update_task(table, item_id, cancel_requested=1)

    def cancel_requested(self, table: str, item_id: str) -> bool:
        return bool(self.get_task(table, item_id)["cancel_requested"])

    def get_task(self, table: str, item_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(item_id)
        return self._task(row)

    def list_tasks(self, table: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(f"SELECT * FROM {table} ORDER BY created_at DESC").fetchall()
        return [self._task(row) for row in rows]

    def _persona(self, row: sqlite3.Row) -> dict[str, Any]:
        chart = None
        with self._connect() as db:
            saved = db.execute("SELECT payload_json FROM charts WHERE persona_id = ?", (row["id"],)).fetchone()
        if saved:
            chart = json.loads(saved["payload_json"])
        return {
            "id": row["id"],
            "display_name": row["display_name"],
            "fictional": bool(row["fictional"]),
            "birth_date": row["birth_date"] or "",
            "birth_time": row["birth_time"] or "",
            "timezone": row["timezone"],
            "birth_place": row["birth_place"] or "",
            "true_solar_time_applied": False,
            "birth_place_used_for_true_solar": False,
            "known_occupation": row["known_occupation"] or "",
            "living_background": row["living_background"] or "",
            "notes": row["notes"] or "",
            "luck_mode": row["luck_mode"] or "",
            "luck_sex": row["luck_sex"] or "",
            "luck_direction": row["luck_direction"] or "",
            "liunian_year": row["liunian_year"],
            "known_facts": {
                "occupation": row["known_occupation"] or "",
                "living_background": row["living_background"] or "",
                "note": "这里只保存用户写下的内容，不从八字回填。",
            },
            "chart_status": (chart or {}).get("status"),
            "pillars": (chart or {}).get("pillars"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _task(self, row: sqlite3.Row) -> dict[str, Any]:
        keys = row.keys()
        result = json.loads(row["result_json"]) if row["result_json"] else None
        item = {
            "id": row["id"],
            "persona_id": row["persona_id"],
            "persona_name": row["persona_name"],
            "scenario": row["scenario"],
            "status": row["status"],
            "model": row["model"],
            "budget": row["budget"],
            "requests_used": row["requests_used"],
            "error": row["error"],
            "result": result,
            "cancel_requested": bool(row["cancel_requested"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "accuracy": None,
            "accuracy_reason": "没有真实结局，不计算准确率。模拟输出不是 ground truth。",
        }
        if "engine" in keys:
            item["engine"] = row["engine"]
            item["compare_model"] = row["compare_model"]
        return item


def get_store() -> Store:
    path = os.environ.get("ZHOUYI_DB_PATH")
    if not path:
        path = str(Path(__file__).resolve().parents[2] / "data" / "zhouyi.sqlite")
    with _LOCK:
        store = _STORES.get(path)
        if store is None:
            store = Store(path)
            _STORES[path] = store
        return store
