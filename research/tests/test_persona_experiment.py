# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only

import json

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
