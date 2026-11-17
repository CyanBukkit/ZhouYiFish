# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Lightweight round table. This is not OASIS and it does not call Zep."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.bazi_rules import chain_text

from .settings import redact, runtime

ENGINE_NAME = "zhouyi_roundtable_v1"
SHUFFLE_VERSION = "persona-shuffle-v2-no-self-pair"
PUBLISHED_V2 = (
    {"background_of": "sandbox-focal-01", "chart_from": "sandbox-focal-02", "pillars": "辛未辛丑癸未丁巳"},
    {"background_of": "sandbox-focal-02", "chart_from": "sandbox-focal-03", "pillars": "戊辰壬戌辛酉丙申"},
    {"background_of": "sandbox-focal-03", "chart_from": "sandbox-focal-01", "pillars": "辛巳甲午己酉己巳"},
)
NOT_CONFIGURED = "模型未配置。未发送请求，没有生成分析文本。"
ACCURACY = "没有真实结局，不计算准确率。模拟输出不是 ground truth。"


class ChatClient(Protocol):
    real_model: bool
    kind: str

    def complete(self, *, model: str, messages: list[dict[str, str]], max_tokens: int) -> dict[str, Any]:
        """One HTTP call or one fixture response. No hidden retry loop."""


class NotConfigured(RuntimeError):
    pass


class LiveClient:
    real_model = True
    kind = "openai_compatible_http"

    def complete(self, *, model: str, messages: list[dict[str, str]], max_tokens: int) -> dict[str, Any]:
        secret = runtime.effective_key()
        if not secret:
            raise NotConfigured(NOT_CONFIGURED)
        url = runtime.effective_base_url().rstrip("/") + "/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        raw = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=raw,
            headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            method="POST",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                body = response.read(8000).decode("utf-8", errors="replace")
                status = response.status
        except urllib.error.HTTPError as exc:
            excerpt = exc.read(800).decode("utf-8", errors="replace")
            return {
                "ok": False,
                "http_status": exc.code,
                "text": None,
                "usage": None,
                "response_model": None,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "error": f"HTTP {exc.code}",
                "body_excerpt": redact(excerpt, secret),
                "real_model": True,
            }
        except urllib.error.URLError as exc:
            return {
                "ok": False,
                "http_status": None,
                "text": None,
                "usage": None,
                "response_model": None,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "error": "网络错误",
                "body_excerpt": redact(str(exc.reason), secret),
                "real_model": True,
            }
        latency = int((time.monotonic() - started) * 1000)
        try:
            parsed = json.loads(body)
            text = parsed["choices"][0]["message"]["content"]
            usage = parsed.get("usage")
            response_model = parsed.get("model")
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            return {
                "ok": False,
                "http_status": status,
                "text": None,
                "usage": None,
                "response_model": None,
                "latency_ms": latency,
                "error": "响应里没有补全文本",
                "body_excerpt": redact(body, secret),
                "real_model": True,
            }
        return {
            "ok": True,
            "http_status": status,
            "text": text,
            "usage": usage if isinstance(usage, dict) else None,
            "response_model": response_model,
            "latency_ms": latency,
            "error": None,
            "body_excerpt": None,
            "real_model": True,
            "response_model_is_not_identity_verification": True,
        }


class FixtureClient:
    """Automatic tests only. The product UI has no control that selects this."""

    real_model = False
    kind = "test_fixture"

    def complete(self, *, model: str, messages: list[dict[str, str]], max_tokens: int) -> dict[str, Any]:
        user = messages[-1]["content"]
        if "choice" in messages[0]["content"]:
            if "臂: with_bazi" in user:
                choice = "refuse"
            elif "臂: shuffled_bazi" in user:
                choice = "unclear"
            else:
                choice = "cooperate"
            text = json.dumps({"choice": choice, "note": f"fixture-{choice}"}, ensure_ascii=False)
        else:
            text = json.dumps(
                {
                    "evidence": ["fixture 只复述测试输入"],
                    "hypotheses": ["这不是真实模型"],
                    "relationship_suggestions": "保持场景角色，不要当成真人建议。",
                    "action_suggestions": "FIXTURE_ONLY",
                    "simulated": True,
                },
                ensure_ascii=False,
            )
        return {
            "ok": True,
            "http_status": 200,
            "text": text,
            "usage": {"prompt_tokens": 4, "completion_tokens": 6, "total_tokens": 10},
            "response_model": "fixture-not-a-real-model",
            "latency_ms": 1,
            "error": None,
            "real_model": False,
        }


def control_chart(own_id: str, own_pillars: str, others: list[dict[str, str]]) -> dict[str, Any] | None:
    for other in others:
        if other.get("pillars") and other["pillars"] != own_pillars:
            return {
                "version": SHUFFLE_VERSION,
                "chart_from": other["id"],
                "pillars": other["pillars"],
                "own_chart": False,
                "source": "another_saved_chart",
            }
    for row in PUBLISHED_V2:
        if row["background_of"] == own_id and row["pillars"] != own_pillars:
            return {**row, "version": SHUFFLE_VERSION, "own_chart": False, "source": "published_fictional_cohort_v2"}
    for row in PUBLISHED_V2:
        if row["pillars"] != own_pillars:
            return {
                "version": SHUFFLE_VERSION,
                "chart_from": row["chart_from"],
                "pillars": row["pillars"],
                "own_chart": False,
                "source": "published_fictional_cohort_v2",
            }
    return None


def neutral_block(real_block: str) -> str:
    target = len(real_block.encode("utf-8"))
    base = "本臂是等长中性信息，不含四柱，也不含职业判断。"
    base_len = len(base.encode("utf-8"))
    fitted = ("x" * target) if base_len > target else base + ("x" * (target - base_len))
    if len(fitted.encode("utf-8")) != target:
        raise RuntimeError("中性臂长度没有对齐。")
    return fitted


def _facts_block(persona: dict[str, Any], relations: list[dict[str, Any]]) -> str:
    fact_relations = [item for item in relations if item["kind"] == "user_fact"]
    relation_text = "；".join(f"{item['name']}（{item['relation']}）" for item in fact_relations) or "用户没有填写已知关系"
    return (
        f"人物：{persona['display_name']}。虚构档案：{'是' if persona['fictional'] else '否，仍不是已验证个案'}。\n"
        f"用户已知职业：{persona['known_occupation'] or '未填'}。\n"
        f"用户已知生活背景：{persona['living_background'] or '未填'}。\n"
        f"用户已知关系：{relation_text}。\n"
    )


def build_arms(persona: dict[str, Any], chart: dict[str, Any], relations: list[dict[str, Any]], scenario: str, others: list[dict[str, str]]) -> dict[str, Any]:
    pillars = chart.get("pillars")
    if not pillars:
        raise ValueError("四柱不完整，不能做附八字对照。")
    facts = _facts_block(persona, relations)
    reading = chain_text(chart.get("reading"))
    with_block = facts + f"本组附上八字：{pillars}。八字不决定职业。\n{reading}场景：{scenario}。\n"
    control = control_chart(persona["id"], str(pillars), others)
    arms: dict[str, Any] = {
        "without_bazi": {
            "prompt": facts + "本组不附八字。\n" + f"场景：{scenario}。\n",
            "output": None,
        },
        "with_bazi": {"prompt": with_block, "output": None},
        "neutral": {
            "prompt": neutral_block(with_block),
            "output": None,
            "tokens_equal": None,
            "disclosure": "等字节不是等 token。这里只对齐 UTF-8 字节。",
        },
    }
    if control is None:
        arms["shuffled_bazi"] = {
            "prompt": None,
            "output": None,
            "status": "blocked",
            "error": "没有另一张不同的八字可作无自配对对照。不会把本人八字再放进打乱臂。",
        }
    else:
        if control["pillars"] == pillars or control["own_chart"] is not False:
            raise RuntimeError("打乱臂拒绝自配对。")
        arms["shuffled_bazi"] = {
            "prompt": facts + f"本组附上八字：{control['pillars']}。这不是此人自己的四柱。八字不决定职业。\n场景：{scenario}。\n",
            "output": None,
            "control": control,
        }
    for name, arm in arms.items():
        prompt = arm.get("prompt") or ""
        if name == "without_bazi" and (pillars in prompt or "旺衰" in prompt or "大运" in prompt):
            raise RuntimeError("无八字臂泄漏了四柱或规则链。")
        if name == "shuffled_bazi" and "旺衰" in prompt:
            raise RuntimeError("打乱臂不能附上本人的规则链。")
        if name == "neutral" and (pillars in prompt or "旺衰" in prompt):
            raise RuntimeError("中性臂泄漏了四柱或规则链。")
    return {
        "shuffle_version": SHUFFLE_VERSION,
        "v1_archive": "research/experiments/persona_sandbox_v1/result.json",
        "v1_policy": "原始已用输入保持自配对记录，本实验不回改那个文件。",
        "arms": arms,
    }


def run_rounds(store: Any, task_id: str, persona: dict[str, Any], chart: dict[str, Any], relations: list[dict[str, Any]], scenario: str, client: ChatClient, compare_model: str | None) -> None:
    budget = store.get_task("analyses", task_id)["budget"]
    used = 0
    steps: list[dict[str, Any]] = []
    roles = [("本人视角", "archive")]
    for relation in relations:
        roles.append((relation["name"], relation["kind"]))
    if len(roles) == 1:
        roles.append(("场景同事", "scene_role"))
    model = store.get_task("analyses", task_id)["model"]
    transcript: list[str] = []

    def fail(message: str) -> None:
        store.update_task(
            "analyses",
            task_id,
            status="failed",
            requests_used=used,
            error=message,
            result=_result(persona, chart, relations, scenario, steps, None, client, used),
        )

    store.update_task("analyses", task_id, status="running")
    for name, kind in roles:
        if store.cancel_requested("analyses", task_id):
            store.update_task("analyses", task_id, status="cancelled", requests_used=used, error="已取消", result=_result(persona, chart, relations, scenario, steps, None, client, used))
            return
        if used >= budget:
            fail("已达到本次预算，停止继续调用。")
            return
        messages = [
            {"role": "system", "content": "你参加的是实验性圆桌，不是原版 OASIS。只谈低风险合作或沟通。八字不决定职业。不要给出医疗、博彩或投资建议。不得改写已经算出的四柱、十神、格局候选和大运干支。"},
            {"role": "user", "content": _facts_block(persona, relations) + chain_text(chart.get("reading")) + f"角色：{name}（{kind}）。场景：{scenario}。用两三句中文说明这个角色会怎么回应。"},
        ]
        outcome = client.complete(model=model, messages=messages, max_tokens=180)
        used += 1
        step = {"step": len(steps) + 1, "role": name, "role_kind": kind, "model": model, **_public_call(outcome)}
        steps.append(step)
        if not outcome["ok"]:
            fail(outcome.get("error") or "模型调用失败")
            return
        transcript.append(f"{name}: {outcome['text']}")
    if store.cancel_requested("analyses", task_id):
        store.update_task("analyses", task_id, status="cancelled", requests_used=used, error="已取消", result=_result(persona, chart, relations, scenario, steps, None, client, used))
        return
    if used >= budget:
        fail("已达到本次预算，汇总没有调用。")
        return
    summary_prompt = "根据圆桌记录只输出一个 JSON 对象，键为 evidence, hypotheses, relationship_suggestions, action_suggestions, simulated。simulated 必须为 true。\n" + "\n".join(transcript)
    summary = client.complete(
        model=model,
        messages=[{"role": "system", "content": "只输出 JSON。"}, {"role": "user", "content": summary_prompt}],
        max_tokens=280,
    )
    used += 1
    steps.append({"step": len(steps) + 1, "role": "汇总", "role_kind": "summary", "model": model, **_public_call(summary)})
    if not summary["ok"]:
        fail(summary.get("error") or "汇总调用失败")
        return
    parsed = _parse_summary(summary["text"])
    comparison = None
    if compare_model and compare_model != model:
        if used >= budget:
            comparison = {"status": "not_run", "error": "预算已用完，对照模型没有调用。"}
        elif store.cancel_requested("analyses", task_id):
            store.update_task("analyses", task_id, status="cancelled", requests_used=used, error="已取消", result=_result(persona, chart, relations, scenario, steps, parsed, client, used))
            return
        else:
            second = client.complete(model=compare_model, messages=[{"role": "system", "content": "只输出 JSON。"}, {"role": "user", "content": summary_prompt}], max_tokens=280)
            used += 1
            steps.append({"step": len(steps) + 1, "role": "对照模型汇总", "role_kind": "summary", "model": compare_model, **_public_call(second)})
            comparison = {"model": compare_model, "ok": second["ok"], "text": second.get("text"), "error": second.get("error")}
    result = _result(persona, chart, relations, scenario, steps, parsed, client, used)
    result["comparison"] = comparison
    store.update_task("analyses", task_id, status="succeeded", requests_used=used, error=None, result=result)


def run_experiment(store: Any, task_id: str, prepared: dict[str, Any], client: ChatClient) -> None:
    task = store.get_task("experiments", task_id)
    used = 0
    outputs = []
    store.update_task("experiments", task_id, status="running", result=prepared)
    for name, arm in prepared["arms"].items():
        if arm.get("status") == "blocked":
            outputs.append({"arm": name, "ok": False, "status": "blocked"})
            continue
        if store.cancel_requested("experiments", task_id):
            prepared["outputs"] = outputs
            store.update_task("experiments", task_id, status="cancelled", requests_used=used, error="已取消", result=prepared)
            return
        if used >= task["budget"]:
            prepared["outputs"] = outputs
            store.update_task("experiments", task_id, status="failed", requests_used=used, error="已达到本次预算。", result=prepared)
            return
        outcome = client.complete(
            model=task["model"],
            messages=[
                {"role": "system", "content": "只输出 JSON，键为 choice 与 note。choice 取 cooperate、refuse 或 unclear。这是模拟，不是准确率。"},
                {"role": "user", "content": f"臂: {name}\n{arm['prompt']}"},
            ],
            max_tokens=120,
        )
        used += 1
        arm["output"] = _public_call(outcome)
        outputs.append({"arm": name, "ok": outcome["ok"]})
        if not outcome["ok"]:
            prepared["outputs"] = outputs
            prepared["accuracy"] = None
            store.update_task("experiments", task_id, status="failed", requests_used=used, error=outcome.get("error") or "调用失败", result=prepared)
            return
    texts = [prepared["arms"][name].get("output", {}).get("text") for name in prepared["arms"] if prepared["arms"][name].get("output")]
    prepared["outputs"] = outputs
    prepared["completion_count"] = sum(1 for item in outputs if item.get("ok"))
    prepared["arm_count"] = len(prepared["arms"])
    prepared["texts_differ"] = len(set(texts)) > 1 if texts else False
    prepared["accuracy"] = None
    prepared["accuracy_reason"] = ACCURACY
    prepared["real_model"] = client.real_model
    store.update_task("experiments", task_id, status="succeeded", requests_used=used, error=None, result=prepared)


def _public_call(outcome: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": outcome["ok"],
        "http_status": outcome.get("http_status"),
        "latency_ms": outcome.get("latency_ms"),
        "usage": outcome.get("usage"),
        "text": outcome.get("text"),
        "error": outcome.get("error"),
        "body_excerpt": outcome.get("body_excerpt"),
        "response_model": outcome.get("response_model"),
        "real_model": outcome.get("real_model"),
    }


def _parse_summary(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"raw_text": text, "json_parsed": False, "simulated": True}
    if not isinstance(parsed, dict):
        return {"raw_text": text, "json_parsed": False, "simulated": True}
    parsed["simulated"] = True
    parsed["json_parsed"] = True
    parsed["is_fact"] = False
    return parsed


def _result(persona: dict[str, Any], chart: dict[str, Any], relations: list[dict[str, Any]], scenario: str, steps: list[dict[str, Any]], summary: dict[str, Any] | None, client: ChatClient, used: int) -> dict[str, Any]:
    return {
        "engine": ENGINE_NAME,
        "not_oasis": True,
        "not_zep": True,
        "simulated": True,
        "usable_as_human_ground_truth": False,
        "accuracy": None,
        "accuracy_reason": ACCURACY,
        "real_model": client.real_model,
        "model_call_kind": client.kind,
        "scenario": scenario,
        "requests_used": used,
        "evidence": {
            "known_occupation": persona.get("known_occupation") or "",
            "living_background": persona.get("living_background") or "",
            "relations": relations,
            "pillars": chart.get("pillars"),
            "rule_version": (chart.get("reading") or {}).get("rule_version"),
            "strength_verdict": ((chart.get("reading") or {}).get("steps") or {}).get("strength", {}).get("verdict"),
            "chart_does_not_determine_occupation": True,
            "model_must_not_override_calculation": True,
        },
        "steps": steps,
        "summary": summary,
    }
