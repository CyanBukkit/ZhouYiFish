# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only

import json

import pytest

from research.llm_adapter import PromptError, build_arm_messages, llm_run_status, parse_probability, run_four_arm
from research.mapping import structural_features
from research.meihua import cast_from_numbers


class FakeClient:
    def __init__(self, text: str = '{"p": 0.25}') -> None:
        self.text = text
        self.calls = []
        self.last_usage = {"prompt_tokens": 11, "completion_tokens": 4}

    def chat(self, messages, temperature=0.0, max_tokens=256, response_format=None):
        self.calls.append(
            {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "bytes": len(messages[1]["content"].encode("utf-8")),
            }
        )
        return self.text


def _events():
    casts = [cast_from_numbers(5, 12, 17, 9), cast_from_numbers(6, 3, 16, 4)]
    events = []
    for index, cast in enumerate(casts):
        events.append(
            {
                "event_id": f"e{index}",
                "question": "测试题面，不包含卦名。",
                "information_time_local": "2024-01-01T00:00:00+08:00",
                "lunar_month_number": index + 1,
                "cast": cast,
                "features": structural_features(cast),
            }
        )
    return events


def test_arms_match_length_and_placebo_has_no_hexagram_name():
    built = build_arm_messages(_events())
    for event in built:
        assert len(set(event["utf8_bytes"].values())) == 1
        user = {arm: messages[1]["content"] for arm, messages in event["arms"].items()}
        assert "泽火革" not in user["A"]
        assert "泽火革" not in user["D"]
        assert "NEUTRAL" in user["D"]
        assert "泽火革" in user["B"] or "天风姤" in user["B"]


def test_runner_uses_one_row_per_event_and_equal_budget():
    client = FakeClient()
    result = run_four_arm(_events(), client, seeds=3)
    assert result["event_count"] == 2
    assert result["call_count"] == 24
    assert result["not_a_mirofish_swarm_run"] is True
    assert {call["max_tokens"] for call in client.calls} == {256}
    assert {call["temperature"] for call in client.calls} == {0.0}
    assert len({call["bytes"] for call in client.calls}) == 1
    assert all(row["n_event_rows"] == 1 for row in result["rows"])
    assert result["rows"][0]["p"]["B"] == 0.25


def test_invalid_json_is_not_retried_or_repaired():
    client = FakeClient("不是概率")
    result = run_four_arm(_events()[:1], client, seeds=1)
    assert result["call_count"] == 4
    assert result["rows"][0]["complete"] is False
    with pytest.raises(PromptError):
        parse_probability('{"p": 1.2, "reason": "no"}')


def test_prompts_reject_outcomes_and_live_status_stays_blocked():
    events = _events()
    events[0]["outcome"] = 1
    with pytest.raises(PromptError):
        build_arm_messages(events)
    status = llm_run_status()
    assert status["status"] == "not_run"
    assert "没有调用模型" in status["blocker"]
