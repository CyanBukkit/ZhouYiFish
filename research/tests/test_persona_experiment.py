# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only

import hashlib
import json
from pathlib import Path

import pytest

from research.llm_adapter import llm_diagnose
from research.persona_experiment import refuse_accuracy_score, run_persona_experiment


def test_cohort_has_real_looking_jobs_and_no_model_output():
    result = run_persona_experiment()
    assert result["model_calls"] == 0
    assert result["accuracy_claimed"] is False
    assert result["integrity"]["behavior_outputs_invented"] == 0
    titles = []
    for person in result["people"]:
        job = person["synthetic_occupation"]
        assert job["title"]
        assert job["is_bazi_fact"] is False
        assert job["field_class"] == "synthetic_research_setting"
        titles.append(job["title"])
        own = person["pillars"]
        assert own not in person["inputs"]["without_bazi"]
        assert own in person["inputs"]["with_bazi"]
        for prompt in result["scenario_prompts"][person["persona_id"]]:
            assert prompt["behavior_output"] is None
            assert prompt["model_run"] is False
            assert own not in prompt["without_bazi"]
    assert len(set(titles)) >= 2
    pillars = [pair["pillars"] for pair in result["shuffle"]["pairs"]]
    assert sorted(pillars) == sorted(person["pillars"] for person in result["people"])
    assert any(not pair["own_chart"] for pair in result["shuffle"]["pairs"])


def test_frozen_result_keeps_focal01_self_pair():
    path = Path(__file__).resolve().parents[1] / "experiments/persona_sandbox_v1/result.json"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == "8c5c997bbe0efd1d1df3e442e4894e97c5b5a75d300f01ca9b75a40e27d6169f"
    result = json.loads(path.read_text(encoding="utf-8"))
    pair = next(item for item in result["shuffle"]["pairs"] if item["background_of"] == "sandbox-focal-01")
    assert pair == {
        "background_of": "sandbox-focal-01",
        "chart_from": "sandbox-focal-01",
        "own_chart": True,
        "pillars": "辛巳甲午己酉己巳",
    }
    assert result["model_calls"] == 0
    assert result["shuffle"]["adjusted_because_draw_was_identity"] is False


def test_accuracy_path_fails_closed():
    with pytest.raises(Exception, match="不能记行为准确率"):
        refuse_accuracy_score({"model_run": False})
    with pytest.raises(Exception, match="不能当作真人预测准确率"):
        refuse_accuracy_score({"model_run": True, "simulated_role_output": True})


def test_diagnosis_does_not_echo_a_secret(monkeypatch):
    monkeypatch.setenv("ZHOUYI_LLM_API_KEY", "should-not-appear")
    status = llm_diagnose()
    blob = json.dumps(status)
    assert "should-not-appear" not in blob
    assert status["credential_present"] is True
    assert status["model_calls"] == 0
    assert status["will_call_model"] is False
