# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only

import hashlib
import json
from pathlib import Path

import pytest

from app.zhouyi_app.engine import control_chart, neutral_block
from app.zhouyi_app.settings import redact, runtime


ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "research/experiments/persona_sandbox_v1/result.json"
V1_SHA = "8c5c997bbe0efd1d1df3e442e4894e97c5b5a75d300f01ca9b75a40e27d6169f"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ZHOUYI_DB_PATH", str(tmp_path / "zhouyi.sqlite"))
    monkeypatch.setenv("ZHOUYI_ALLOW_FIXTURE", "1")
    monkeypatch.delenv("ZHOUYI_LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("ZEP_API_KEY", raising=False)
    runtime.clear()
    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_health_and_chart_without_keys(client):
    health = client.get("/health").get_json()
    assert health["status"] == "ok"
    assert health["llm_configured"] is False
    assert health["zep_required_for_core"] is False
    created = client.post(
        "/api/zhouyi/personas",
        json={
            "display_name": "自建甲",
            "fictional": True,
            "birth_date": "2001-06-15",
            "birth_time": "10:30",
            "timezone": "Asia/Shanghai",
            "birth_place": "只作记录的地点",
            "known_occupation": "用户填写的档案员",
        },
    )
    assert created.status_code == 201
    persona_id = created.get_json()["data"]["id"]
    chart = client.post(f"/api/zhouyi/personas/{persona_id}/chart").get_json()["data"]
    assert chart["chart"]["pillars"] == "辛巳甲午己酉己巳"
    assert chart["chart"]["true_solar_time_applied"] is False
    assert chart["chart"]["birth_place_used_for_true_solar"] is False
    assert chart["persona"]["known_occupation"] == "用户填写的档案员"
    assert all(item["is_fact"] is False for item in chart["hypotheses"])
    assert any("社区档案管理员" in item["text"] for item in chart["hypotheses"])
    assert "用户填写的档案员" not in chart["hypotheses"][0]["text"]


def test_missing_hour_does_not_invent_a_chart(client):
    created = client.post("/api/zhouyi/personas", json={"display_name": "无时辰", "birth_date": "2001-06-15", "timezone": "Asia/Shanghai"}).get_json()
    bundle = client.post(f"/api/zhouyi/personas/{created['data']['id']}/chart").get_json()["data"]
    assert bundle["chart"]["pillars"] is None
    assert bundle["chart"]["status"] == "not_applicable"


def test_graph_roundtrip_and_hypothesis_cannot_become_fact(client):
    example = client.post("/api/zhouyi/examples/sandbox-jia").get_json()["data"]
    persona_id = example["persona"]["id"]
    assert example["persona"]["known_occupation"] == ""
    assert example["graph"]["edges"]
    updated = client.post(
        f"/api/zhouyi/personas/{persona_id}/relations",
        json={"name": "表亲", "relation": "用户说的亲属", "kind": "user_fact"},
    ).get_json()["data"]
    assert any(node["label"] == "表亲" for node in updated["graph"]["nodes"])
    rejected = client.post(f"/api/zhouyi/personas/{persona_id}/hypotheses", json={"text": "当成事实", "is_fact": True})
    assert rejected.status_code == 400


def test_analysis_without_key_does_not_fabricate(client):
    persona_id = client.post("/api/zhouyi/examples/sandbox-jia").get_json()["data"]["persona"]["id"]
    response = client.post(
        "/api/zhouyi/analyses",
        json={"persona_id": persona_id, "scenario": "是否报名参加社区读书会", "budget": 8},
    )
    body = response.get_json()["data"]
    assert body["status"] == "failed"
    assert body["requests_used"] == 0
    assert body["result"]["summary"] is None
    assert body["result"]["fabricated"] is False
    assert body["accuracy"] is None
    blob = json.dumps(body, ensure_ascii=False)
    assert "FIXTURE" not in blob
    assert "社区档案管理员会" not in blob


def test_fixture_is_marked_and_refused_outside_tests(client, monkeypatch):
    persona_id = client.post("/api/zhouyi/examples/sandbox-jia").get_json()["data"]["persona"]["id"]
    monkeypatch.delenv("ZHOUYI_ALLOW_FIXTURE", raising=False)
    blocked = client.post(
        "/api/zhouyi/analyses",
        json={"persona_id": persona_id, "scenario": "是否报名参加社区读书会"},
        headers={"X-Zhouyi-Fixture": "1"},
    )
    assert blocked.status_code == 403
    monkeypatch.setenv("ZHOUYI_ALLOW_FIXTURE", "1")
    allowed = client.post(
        "/api/zhouyi/analyses",
        json={"persona_id": persona_id, "scenario": "是否报名参加社区读书会", "compare_model": "gpt-6-astra"},
        headers={"X-Zhouyi-Fixture": "1"},
    )
    body = allowed.get_json()["data"]
    assert body["status"] == "succeeded"
    assert body["result"]["real_model"] is False
    assert body["result"]["model_call_kind"] == "test_fixture"
    assert body["accuracy"] is None
    assert body["requests_used"] > 0


def test_settings_mask_key_and_connection_stays_unsent(client):
    saved = client.post("/api/zhouyi/settings", json={"api_key": "super-secret-value", "base_url": "http://m4.cyanbukkit.cn:3000/v1", "model": "gpt-6-astra"}).get_json()
    blob = json.dumps(saved, ensure_ascii=False)
    assert "super-secret-value" not in blob
    assert saved["data"]["key_configured"] is True
    assert saved["data"]["plaintext_http"] is True
    assert saved["data"]["model"] == "gpt-6-astra"
    client.post("/api/zhouyi/settings", json={"clear_key": True})
    probed = client.post("/api/zhouyi/settings/test")
    assert probed.status_code == 400
    assert probed.get_json()["data"] if False else "未发送" in probed.get_json()["error"]


def test_experiment_uses_derangement_and_keeps_v1_bytes(client):
    first = client.post(
        "/api/zhouyi/personas",
        json={"display_name": "甲", "birth_date": "2001-06-15", "birth_time": "10:30", "timezone": "Asia/Shanghai"},
    ).get_json()["data"]["id"]
    second = client.post(
        "/api/zhouyi/personas",
        json={"display_name": "乙", "birth_date": "1992-01-08", "birth_time": "09:00", "timezone": "Asia/Shanghai"},
    ).get_json()["data"]["id"]
    client.post(f"/api/zhouyi/personas/{first}/chart")
    client.post(f"/api/zhouyi/personas/{second}/chart")
    response = client.post(
        "/api/zhouyi/experiments",
        json={"persona_id": first, "scenario": "是否把一份共享备忘录交给同事继续改", "budget": 8},
        headers={"X-Zhouyi-Fixture": "1"},
    )
    body = response.get_json()["data"]
    arms = body["result"]["arms"]
    own = client.get(f"/api/zhouyi/personas/{first}").get_json()["data"]["chart"]["pillars"]
    shuffled = arms["shuffled_bazi"]["control"]
    assert shuffled["own_chart"] is False
    assert shuffled["pillars"] != own
    assert own not in arms["without_bazi"]["prompt"]
    assert own not in arms["neutral"]["prompt"]
    assert len(arms["neutral"]["prompt"].encode("utf-8")) == len(arms["with_bazi"]["prompt"].encode("utf-8"))
    assert body["result"]["texts_differ"] is True
    assert body["accuracy"] is None
    assert hashlib.sha256(V1.read_bytes()).hexdigest() == V1_SHA


def test_export_mentions_place_policy(client):
    persona_id = client.post("/api/zhouyi/examples/sandbox-jia").get_json()["data"]["persona"]["id"]
    text = client.get(f"/api/zhouyi/personas/{persona_id}/export.md").get_data(as_text=True)
    assert "未用于真太阳时" in text
    assert "辛巳甲午己酉己巳" in text


def test_control_chart_refuses_self_pair():
    chosen = control_chart("sandbox-focal-01", "辛巳甲午己酉己巳", [])
    assert chosen["own_chart"] is False
    assert chosen["pillars"] != "辛巳甲午己酉己巳"
    assert neutral_block("辛巳") != "辛巳"
    assert "super-secret" not in redact("token super-secret", "super-secret")
