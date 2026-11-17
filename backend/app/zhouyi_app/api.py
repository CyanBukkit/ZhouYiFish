# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""HTTP API for the ZhouYiFish workbench."""

from __future__ import annotations

import os
import threading
from typing import Any

from flask import Blueprint, Response, jsonify, request

from .casting import POLICY, SCENARIOS, cast_fields
from .engine import (
    ENGINE_NAME,
    NOT_CONFIGURED,
    FixtureClient,
    LiveClient,
    build_arms,
    run_experiment,
    run_rounds,
)
from .settings import redact, runtime
from .store import get_store

bp = Blueprint("zhouyi", __name__)
HARD_LIMIT = 60


def _json_error(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


def _ok(data: Any, status: int = 200):
    return jsonify({"success": True, "data": data}), status


def _body() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _persona_fields(payload: dict[str, Any], current: dict[str, Any] | None = None) -> dict[str, Any]:
    source = current or {}
    name = str(payload.get("display_name", source.get("display_name", ""))).strip()
    if not name:
        raise ValueError("需要人物名称。")
    timezone_name = str(payload.get("timezone", source.get("timezone", "Asia/Shanghai"))).strip() or "Asia/Shanghai"
    return {
        "display_name": name[:80],
        "fictional": bool(payload.get("fictional", source.get("fictional", True))),
        "birth_date": str(payload.get("birth_date", source.get("birth_date", ""))).strip()[:10],
        "birth_time": str(payload.get("birth_time", source.get("birth_time", ""))).strip()[:5],
        "timezone": timezone_name[:64],
        "birth_place": str(payload.get("birth_place", source.get("birth_place", ""))).strip()[:200],
        "known_occupation": str(payload.get("known_occupation", source.get("known_occupation", ""))).strip()[:200],
        "living_background": str(payload.get("living_background", source.get("living_background", ""))).strip()[:1000],
        "notes": str(payload.get("notes", source.get("notes", ""))).strip()[:1000],
    }


def _budget(payload: dict[str, Any]) -> int:
    raw = payload.get("budget", 8)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("预算必须是整数。") from exc
    if value < 1 or value > HARD_LIMIT:
        raise ValueError(f"单次预算必须在 1 到 {HARD_LIMIT} 之间。")
    return value


def _client():
    if request.headers.get("X-Zhouyi-Fixture") == "1":
        if os.environ.get("ZHOUYI_ALLOW_FIXTURE") != "1":
            raise PermissionError("测试夹具只在自动测试里启用，不能当作真实模型。")
        return FixtureClient()
    return LiveClient()


def _missing(persona_id: str):
    try:
        return get_store().get_persona(persona_id), None
    except KeyError:
        return None, _json_error("没有这个人物档案。", 404)


@bp.get("/health")
def health():
    view = runtime.public_view()
    return jsonify(
        {
            "status": "ok",
            "service": "ZhouYiFish",
            "llm_configured": view["key_configured"],
            "zep_configured": view["zep_configured"],
            "zep_required_for_core": False,
            "engine": ENGINE_NAME,
            "engine_is_oasis": False,
        }
    )


@bp.get("/meta")
def meta():
    return _ok({"scenarios": SCENARIOS, "policy": POLICY, "engine": ENGINE_NAME, "engine_is_oasis": False})


@bp.get("/settings")
def get_settings():
    return _ok(runtime.public_view())


@bp.post("/settings")
def update_settings():
    payload = _body()
    runtime.update(
        api_key=payload.get("api_key") if "api_key" in payload else None,
        clear_key=bool(payload.get("clear_key")),
        base_url=payload.get("base_url") if "base_url" in payload else None,
        model=payload.get("model") if "model" in payload else None,
    )
    return _ok(runtime.public_view())


@bp.post("/settings/test")
def test_connection():
    if not runtime.effective_key():
        return _json_error(NOT_CONFIGURED + " 连接测试没有发出。", 400)
    outcome = LiveClient().complete(
        model=runtime.effective_model(_body().get("model")),
        messages=[{"role": "user", "content": "Reply with the single word PONG and nothing else."}],
        max_tokens=16,
    )
    public = {
        "ok": outcome["ok"],
        "http_status": outcome.get("http_status"),
        "latency_ms": outcome.get("latency_ms"),
        "usage": outcome.get("usage"),
        "response_model": outcome.get("response_model"),
        "response_model_is_not_identity_verification": True,
        "error": outcome.get("error"),
        "body_excerpt": outcome.get("body_excerpt"),
        "real_model": True,
        "requests_sent": 1,
    }
    status = 200 if outcome["ok"] else 502
    return jsonify({"success": outcome["ok"], "data": public, "error": outcome.get("error")}), status


@bp.get("/personas")
def list_personas():
    return _ok(get_store().list_personas())


@bp.post("/personas")
def create_persona():
    try:
        fields = _persona_fields(_body())
    except ValueError as exc:
        return _json_error(str(exc))
    return _ok(get_store().upsert_persona(fields), 201)


@bp.post("/examples/sandbox-jia")
def load_example():
    store = get_store()
    fields = {
        "display_name": "沙盒甲",
        "fictional": True,
        "birth_date": "2001-06-15",
        "birth_time": "10:30",
        "timezone": "Asia/Shanghai",
        "birth_place": "虚构文化馆登记台",
        "known_occupation": "",
        "living_background": "虚构文化馆的登记台，不是真实地址。",
        "notes": "内置虚构样例。职业候选来自日干表，不是这个人的真实职业。",
    }
    store.upsert_persona(fields, "sandbox-example-jia")
    failed = _cast("sandbox-example-jia")
    if failed:
        return failed
    for relation in store.list_relations("sandbox-example-jia"):
        store.delete_relation(relation["id"])
    store.add_relation("sandbox-example-jia", "沙盒同事", "一起处理登记台的文书", "scene_role")
    store.add_relation("sandbox-example-jia", "同层邻居", "住在虚构登记台的邻户", "scene_role")
    return _ok(_bundle("sandbox-example-jia"))


@bp.get("/personas/<persona_id>")
def get_persona(persona_id: str):
    _persona, error = _missing(persona_id)
    if error:
        return error
    return _ok(_bundle(persona_id))


@bp.patch("/personas/<persona_id>")
def update_persona(persona_id: str):
    current, error = _missing(persona_id)
    if error:
        return error
    try:
        fields = _persona_fields(_body(), current)
    except ValueError as exc:
        return _json_error(str(exc))
    birth_changed = (
        fields["birth_date"] != current["birth_date"]
        or fields["birth_time"] != current["birth_time"]
        or fields["timezone"] != current["timezone"]
    )
    get_store().upsert_persona(fields, persona_id)
    if birth_changed:
        cast_error = _cast(persona_id)
        if cast_error:
            return cast_error
    return _ok(_bundle(persona_id))


@bp.delete("/personas/<persona_id>")
def delete_persona(persona_id: str):
    try:
        get_store().delete_persona(persona_id)
    except KeyError:
        return _json_error("没有这个人物档案。", 404)
    return _ok({"deleted": persona_id})


@bp.post("/personas/<persona_id>/chart")
def create_chart(persona_id: str):
    _persona, error = _missing(persona_id)
    if error:
        return error
    failed = _cast(persona_id)
    if failed:
        return failed
    return _ok(_bundle(persona_id))


@bp.post("/personas/<persona_id>/relations")
def add_relation(persona_id: str):
    _persona, error = _missing(persona_id)
    if error:
        return error
    payload = _body()
    name = str(payload.get("name", "")).strip()
    relation = str(payload.get("relation", "")).strip()
    kind = payload.get("kind", "user_fact")
    if kind not in {"user_fact", "scene_role"}:
        return _json_error("关系类型只能是用户已知事实或场景角色。")
    if not name or not relation:
        return _json_error("需要关系名称和说明。")
    get_store().add_relation(persona_id, name[:80], relation[:200], kind)
    return _ok(_bundle(persona_id), 201)


@bp.delete("/relations/<relation_id>")
def delete_relation(relation_id: str):
    try:
        get_store().delete_relation(relation_id)
    except KeyError:
        return _json_error("没有这条关系。", 404)
    return _ok({"deleted": relation_id})


@bp.post("/personas/<persona_id>/hypotheses")
def add_hypothesis(persona_id: str):
    _persona, error = _missing(persona_id)
    if error:
        return error
    if _body().get("is_fact") is True:
        return _json_error("假设不能标成用户已知事实。")
    text = str(_body().get("text", "")).strip()
    if not text:
        return _json_error("需要假设文本。")
    get_store().add_hypothesis(persona_id, text[:500])
    return _ok(_bundle(persona_id), 201)


@bp.post("/analyses")
def create_analysis():
    payload = _body()
    persona, error = _missing(str(payload.get("persona_id", "")))
    if error:
        return error
    scenario = str(payload.get("scenario", "")).strip()
    if scenario not in SCENARIOS:
        return _json_error("请选择列表中的低风险场景。")
    try:
        budget = _budget(payload)
        client = _client()
    except ValueError as exc:
        return _json_error(str(exc))
    except PermissionError as exc:
        return _json_error(str(exc), 403)
    chart = get_store().get_chart(persona["id"]) or {}
    model = runtime.effective_model(payload.get("model"))
    compare = str(payload.get("compare_model") or "").strip() or None
    task = get_store().create_task(
        "analyses",
        {
            "persona_id": persona["id"],
            "persona_name": persona["display_name"],
            "scenario": scenario,
            "engine": ENGINE_NAME,
            "model": model,
            "compare_model": compare,
            "budget": budget,
        },
    )
    if isinstance(client, LiveClient) and not runtime.effective_key():
        finished = get_store().update_task(
            "analyses",
            task["id"],
            status="failed",
            error=NOT_CONFIGURED,
            requests_used=0,
            result={
                "engine": ENGINE_NAME,
                "not_oasis": True,
                "real_model": False,
                "requests_used": 0,
                "fabricated": False,
                "accuracy": None,
                "summary": None,
            },
        )
        return _ok(finished, 201)
    relations = get_store().list_relations(persona["id"])

    def runner() -> None:
        try:
            run_rounds(get_store(), task["id"], persona, chart, relations, scenario, client, compare)
        except Exception as exc:  # noqa: BLE001
            get_store().update_task(
                "analyses",
                task["id"],
                status="failed",
                error=redact(str(exc), runtime.effective_key()),
            )

    if isinstance(client, LiveClient):
        threading.Thread(target=runner, daemon=True).start()
        return _ok(get_store().get_task("analyses", task["id"]), 202)
    runner()
    return _ok(get_store().get_task("analyses", task["id"]), 201)


@bp.get("/analyses")
def list_analyses():
    return _ok(get_store().list_tasks("analyses"))


@bp.get("/analyses/<task_id>")
def get_analysis(task_id: str):
    try:
        return _ok(get_store().get_task("analyses", task_id))
    except KeyError:
        return _json_error("没有这条分析。", 404)


@bp.post("/analyses/<task_id>/cancel")
def cancel_analysis(task_id: str):
    try:
        return _ok(get_store().request_cancel("analyses", task_id))
    except KeyError:
        return _json_error("没有这条分析。", 404)


@bp.post("/experiments")
def create_experiment():
    payload = _body()
    persona, error = _missing(str(payload.get("persona_id", "")))
    if error:
        return error
    scenario = str(payload.get("scenario", "")).strip()
    if scenario not in SCENARIOS:
        return _json_error("请选择列表中的低风险场景。")
    chart = get_store().get_chart(persona["id"]) or {}
    try:
        prepared = build_arms(
            persona,
            chart,
            get_store().list_relations(persona["id"]),
            scenario,
            get_store().other_charts(persona["id"]),
        )
        budget = _budget(payload)
        client = _client()
    except ValueError as exc:
        return _json_error(str(exc))
    except PermissionError as exc:
        return _json_error(str(exc), 403)
    task = get_store().create_task(
        "experiments",
        {
            "persona_id": persona["id"],
            "persona_name": persona["display_name"],
            "scenario": scenario,
            "model": runtime.effective_model(payload.get("model")),
            "budget": budget,
        },
    )
    if isinstance(client, LiveClient) and not runtime.effective_key():
        prepared["accuracy"] = None
        prepared["requests_used"] = 0
        prepared["real_model"] = False
        finished = get_store().update_task(
            "experiments",
            task["id"],
            status="failed",
            error=NOT_CONFIGURED,
            requests_used=0,
            result=prepared,
        )
        return _ok(finished, 201)

    def runner() -> None:
        try:
            run_experiment(get_store(), task["id"], prepared, client)
        except Exception as exc:  # noqa: BLE001
            get_store().update_task("experiments", task["id"], status="failed", error=redact(str(exc), runtime.effective_key()))

    if isinstance(client, LiveClient):
        threading.Thread(target=runner, daemon=True).start()
        return _ok(get_store().get_task("experiments", task["id"]), 202)
    runner()
    return _ok(get_store().get_task("experiments", task["id"]), 201)


@bp.get("/experiments")
def list_experiments():
    return _ok(get_store().list_tasks("experiments"))


@bp.get("/experiments/<task_id>")
def get_experiment(task_id: str):
    try:
        return _ok(get_store().get_task("experiments", task_id))
    except KeyError:
        return _json_error("没有这条实验。", 404)


@bp.post("/experiments/<task_id>/cancel")
def cancel_experiment(task_id: str):
    try:
        return _ok(get_store().request_cancel("experiments", task_id))
    except KeyError:
        return _json_error("没有这条实验。", 404)


@bp.get("/personas/<persona_id>/export.md")
def export_persona_md(persona_id: str):
    _persona, error = _missing(persona_id)
    if error:
        return error
    return Response(_markdown_persona(persona_id), mimetype="text/markdown; charset=utf-8")


@bp.get("/personas/<persona_id>/export.json")
def export_persona_json(persona_id: str):
    _persona, error = _missing(persona_id)
    if error:
        return error
    return _ok(_bundle(persona_id))


@bp.get("/analyses/<task_id>/export.md")
def export_analysis_md(task_id: str):
    try:
        task = get_store().get_task("analyses", task_id)
    except KeyError:
        return _json_error("没有这条分析。", 404)
    lines = [
        f"# 分析 {task['id']}",
        "",
        f"- 状态：{task['status']}",
        f"- 引擎：{task.get('engine')}（不是 OASIS）",
        f"- 场景：{task['scenario']}",
        f"- 请求次数：{task['requests_used']}",
        f"- 准确率：不计算。{task['accuracy_reason']}",
        f"- 错误：{task['error'] or '无'}",
        "",
    ]
    return Response("\n".join(lines), mimetype="text/markdown; charset=utf-8")


def _cast(persona_id: str):
    store = get_store()
    persona = store.get_persona(persona_id)
    try:
        chart = cast_fields(persona)
    except Exception as exc:  # noqa: BLE001
        return _json_error(str(exc))
    store.save_chart(persona_id, chart)
    candidates = ((chart.get("rule_candidates") or {}).get("candidates") or [])
    note = (chart.get("rule_candidates") or {}).get("claim")
    texts = [f"{item}。{note}" if note else item for item in candidates]
    store.replace_rule_hypotheses(persona_id, texts)
    return None


def _bundle(persona_id: str) -> dict[str, Any]:
    store = get_store()
    return {
        "persona": store.get_persona(persona_id),
        "chart": store.get_chart(persona_id),
        "hypotheses": store.list_hypotheses(persona_id),
        "relations": store.list_relations(persona_id),
        "graph": _graph(persona_id),
    }


def _graph(persona_id: str) -> dict[str, Any]:
    store = get_store()
    persona = store.get_persona(persona_id)
    nodes = [{"id": persona_id, "label": persona["display_name"], "kind": "persona"}]
    edges = []
    for relation in store.list_relations(persona_id):
        nodes.append({"id": relation["id"], "label": relation["name"], "kind": relation["kind"]})
        edges.append({"source": persona_id, "target": relation["id"], "relation": relation["relation"], "kind": relation["kind"]})
    return {"nodes": nodes, "edges": edges}


def _markdown_persona(persona_id: str) -> str:
    bundle = _bundle(persona_id)
    persona = bundle["persona"]
    chart = bundle["chart"] or {}
    lines = [
        f"# {persona['display_name']}",
        "",
        f"- 虚构样例：{'是' if persona['fictional'] else '否'}",
        f"- 出生：{persona['birth_date']} {persona['birth_time']} {persona['timezone']}",
        f"- 出生地：{persona['birth_place'] or '未填'}。未用于真太阳时。",
        f"- 用户已知职业：{persona['known_occupation'] or '未填'}",
        f"- 用户已知生活背景：{persona['living_background'] or '未填'}",
        f"- 四柱：{chart.get('pillars') or chart.get('reason') or '尚未排盘'}",
        "",
        "## 假设（不是事实）",
    ]
    for item in bundle["hypotheses"]:
        lines.append(f"- {item['text']}")
    lines.append("")
    lines.append("## 关系")
    for item in bundle["relations"]:
        lines.append(f"- {item['name']} / {item['relation']} / {item['kind']}")
    lines.append("")
    return "\n".join(lines)
