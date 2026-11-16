# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Four-arm prompts on the same chat shape as MiroFish's LLMClient.chat.

Compatibility target: ``backend/app/utils/llm_client.py`` method
``LLMClient.chat(messages, temperature, max_tokens, response_format)``.
This module does not import the backend, because that import loads ``.env``.
Arm A is a fixed-budget probability baseline, not an OASIS swarm run.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Protocol

from research.baselines import permute_within_lunar_month
from research.protocol import canonical_bytes, load_protocol
from research.scoring import aggregate_seed_probabilities

SYSTEM_PROMPT = (
    "你是概率预测器。只输出一个JSON对象，键只有p，p是0到1之间的数字，"
    "表示题面中二元事件发生的概率。不要输出理由、卦辞或裁决。"
    "你不能访问检索或工具。禁止检索这句话不能抹掉预训练里可能已经有的公开史实。"
)


class ChatClient(Protocol):
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int | None = 256,
        response_format: dict | None = None,
    ) -> str:
        """Return the assistant text. Same keyword names as MiroFish LLMClient.chat."""


class PromptError(ValueError):
    """The model text cannot be used as a probability."""


def rule_payload(cast: dict[str, Any], features: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "meihua_juan1_structural",
        "hexagram": cast["hexagram"],
        "changed_hexagram": cast["changed_hexagram"],
        "S": cast["S"],
        "S_plus_hour": cast["S_plus_hour"],
        "moving_line": cast["moving_line"],
        "features": features,
        "judgment_text": "not_included",
    }


def neutral_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {"kind": "neutral_placebo", "body": _neutralize(payload)}


def _neutralize(value: Any) -> Any:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return 0
    if isinstance(value, float):
        return 0.0
    if isinstance(value, str):
        return "NEUTRAL"
    if isinstance(value, list):
        return [_neutralize(item) for item in value]
    if isinstance(value, dict):
        return {key: _neutralize(item) for key, item in value.items()}
    raise PromptError(f"无法做等结构安慰剂的类型：{type(value).__name__}")


def _with_pad(payload: dict[str, Any], length: int) -> dict[str, Any]:
    copied = dict(payload)
    copied["pad"] = "x" * length
    return copied


def equalize_payloads(payloads: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Serialize every arm to the same UTF-8 byte length.

    Each extra ASCII ``x`` in ``pad`` adds one byte under the canonical encoder.
    """

    lengths = {
        name: len(canonical_bytes(_with_pad(payload, 0)))
        for name, payload in payloads.items()
    }
    target = max(lengths.values())
    fitted: dict[str, str] = {}
    for name, payload in payloads.items():
        pad_length = target - lengths[name]
        blob = canonical_bytes(_with_pad(payload, pad_length))
        if len(blob) != target:
            raise PromptError(f"{name} 臂序列化后是 {len(blob)} 字节，目标是 {target}。")
        fitted[name] = blob.decode("utf-8")
    return fitted


def user_message(question: str, local_time: str, latitude: float, longitude: float, block: str) -> str:
    return (
        f"事件: {question}\n"
        f"信息时间: {local_time}\n"
        f"地点: {latitude},{longitude}\n"
        "协议: 只使用题面。结局尚未提供，不要假设自己知道结局。\n"
        f"附加块:\n{block}\n"
    )


def parse_probability(text: str) -> float:
    try:
        obj = json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise PromptError("模型输出不是 JSON。按协议不重试。") from exc
    if not isinstance(obj, dict) or set(obj) != {"p"}:
        raise PromptError("模型输出必须只有键 p。按协议不重试。")
    value = obj["p"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PromptError("p 不是数字。")
    if not 0.0 <= float(value) <= 1.0:
        raise PromptError("p 超出 0 到 1。")
    return float(value)


def build_arm_messages(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build A/B/C/D messages. ``events`` must not contain outcomes.

    Arm C reuses the frozen within-month permutation of the rule payloads.
    Every seed of one event sees the same block.
    """

    protocol, _digest = load_protocol()
    donor_index = permute_within_lunar_month(
        [int(event["lunar_month_number"]) for event in events],
        list(range(len(events))),
    )
    messages = []
    for index, event in enumerate(events):
        if "outcome" in event or "precipitation_mm" in event:
            raise PromptError("四臂题面不能带结局或降水量。")
        real = rule_payload(event["cast"], event["features"])
        donor = rule_payload(events[donor_index[index]]["cast"], events[donor_index[index]]["features"])
        payloads = {
            "A": {"kind": "noninformative_pad", "note": "length equalizer, not a hexagram"},
            "B": real,
            "C": donor,
            "D": neutral_payload(real),
        }
        blocks = equalize_payloads(payloads)
        question = event["question"]
        arm_messages = {}
        for arm, block in blocks.items():
            arm_messages[arm] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": user_message(
                        question,
                        event["information_time_local"],
                        float(protocol["task"]["requested_latitude"]),
                        float(protocol["task"]["requested_longitude"]),
                        block,
                    ),
                },
            ]
        lengths = {arm: len(msgs[1]["content"].encode("utf-8")) for arm, msgs in arm_messages.items()}
        if len(set(lengths.values())) != 1:
            raise PromptError(f"四臂题面字节数不一致：{lengths}")
        messages.append({"event_id": event["event_id"], "arms": arm_messages, "utf8_bytes": lengths})
    return messages


def run_four_arm(
    events: list[dict[str, Any]],
    client: ChatClient,
    *,
    seeds: int | None = None,
) -> dict[str, Any]:
    """Call the injected client. Tests pass a fake. The delivery does not call a live model."""

    protocol, digest = load_protocol()
    spec = protocol["llm_four_arm"]
    seed_count = int(spec["seeds_per_event"] if seeds is None else seeds)
    if seed_count < 1:
        raise PromptError("种子数至少为 1。")
    temperature = float(spec["temperature"])
    max_tokens = int(spec["max_tokens"])
    response_format = {"type": "json_object"}
    built = build_arm_messages(events)
    rows = []
    call_log = []
    for event in built:
        per_arm: dict[str, list[float]] = {arm: [] for arm in ("A", "B", "C", "D")}
        failures = {arm: 0 for arm in per_arm}
        for seed in range(seed_count):
            for arm, messages in event["arms"].items():
                text = client.chat(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
                usage = getattr(client, "last_usage", None)
                call_log.append(
                    {
                        "event_id": event["event_id"],
                        "arm": arm,
                        "seed": seed,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "usage": usage,
                    }
                )
                try:
                    per_arm[arm].append(parse_probability(text))
                except PromptError:
                    failures[arm] += 1
        aggregated = {}
        complete = True
        for arm, values in per_arm.items():
            if len(values) != seed_count:
                complete = False
                aggregated[arm] = None
            else:
                aggregated[arm] = aggregate_seed_probabilities(values)
        rows.append(
            {
                "event_id": event["event_id"],
                "p": aggregated,
                "seed_count": seed_count,
                "failures": failures,
                "complete": complete,
                "n_event_rows": 1,
            }
        )
    return {
        "protocol_sha256": digest,
        "status": "executed_on_injected_client",
        "not_a_mirofish_swarm_run": True,
        "rows": rows,
        "calls": call_log,
        "event_count": len(rows),
        "call_count": len(call_log),
    }


def llm_run_status(config_path: str | None = None) -> dict[str, Any]:
    """Report the live four-arm blocker without searching the environment for secrets."""

    protocol, digest = load_protocol()
    status = {
        "status": "not_run",
        "protocol_sha256": digest,
        "study_primary": "paired_brier_B_minus_A",
        "not_a_mirofish_swarm_run": True,
        "config_example": protocol["llm_four_arm"]["config_example"],
        "blocker": "本次交付没有收到明确交给该任务的模型配置，因此没有调用模型。",
    }
    if config_path is None:
        return status
    path = Path(config_path)
    if not path.is_file():
        status["blocker"] = f"没有找到配置文件 {config_path}。"
        return status
    config = json.loads(path.read_text(encoding="utf-8"))
    env_name = str(config.get("credential_env") or "")
    if not env_name.isidentifier():
        status["blocker"] = "配置里的 credential_env 不是单个环境变量名。"
        return status
    if not os.environ.get(env_name):
        status["blocker"] = f"已看到配置文件，但环境变量 {env_name} 未设置。未读取其他变量，也未调用模型。"
        return status
    status["status"] = "configured_but_not_invoked_by_this_function"
    status["blocker"] = (
        "凭据变量已设置。live 调用仍需操作者执行 run-llm --execute，"
        "默认复现命令不会进入该路径。"
    )
    return status
