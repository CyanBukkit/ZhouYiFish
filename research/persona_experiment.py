# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Offline persona-sandbox checks. They do not call a model or score accuracy."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from research.calendar_time import SHANGHAI
from research.llm_adapter import llm_diagnose
from research.persona import (
    assign_synthetic_occupation,
    build_fictional_persona,
    build_relationship_graph,
    export_same_background_inputs,
)
from research.rngutil import HmacCounter, fisher_yates

OUT = Path(__file__).resolve().parent / "experiments" / "persona_sandbox_v1"

SPECS = [
    {
        "persona_id": "sandbox-focal-01",
        "display_name": "沙盒甲",
        "birth": "2001-06-15T10:30:00+08:00",
        "place": "虚构街区的社区档案室，不是真实地址",
    },
    {
        "persona_id": "sandbox-focal-02",
        "display_name": "沙盒乙",
        "birth": "1992-01-08T09:00:00+08:00",
        "place": "虚构小区的自行车维修点，不是真实地址",
    },
    {
        "persona_id": "sandbox-focal-03",
        "display_name": "沙盒丙",
        "birth": "1988-11-02T15:40:00+08:00",
        "place": "虚构文化馆的登记台，不是真实地址",
    },
]

SCENARIOS = [
    "是否把一份共享备忘录交给同事继续改",
    "是否报名参加社区读书会",
    "是否在小组会上说明自己的不同意见",
]


class ExperimentIntegrityError(RuntimeError):
    """The sandbox export leaked a chart or invented a behavior."""


def build_cohort() -> list[dict[str, Any]]:
    people = []
    for spec in SPECS:
        persona = build_fictional_persona(
            spec["persona_id"],
            datetime.fromisoformat(spec["birth"]).astimezone(SHANGHAI),
            display_name=spec["display_name"],
            living_place_label=spec["place"],
        )
        chosen = persona["occupation_hypothesis"]["candidates"][0]
        persona = assign_synthetic_occupation(persona, chosen)
        graph = build_relationship_graph(persona["persona_id"], chosen)
        inputs = export_same_background_inputs(persona, graph)
        people.append({"persona": persona, "graph": graph, "inputs": inputs})
    return people


def shuffled_charts(people: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [item["persona"]["persona_id"] for item in people]
    charts = {item["persona"]["persona_id"]: item["persona"]["chart"]["pillars"] for item in people}
    order = fisher_yates(list(ids), HmacCounter("persona-sandbox-v1", "chart-shuffle-v1"))
    adjusted = False
    if order == ids and len(ids) > 1:
        order = ids[1:] + ids[:1]
        adjusted = True
    return {
        "shuffle_is_full_distribution": False,
        "adjusted_because_draw_was_identity": adjusted,
        "pairs": [
            {
                "background_of": person_id,
                "chart_from": source,
                "pillars": charts[source],
                "own_chart": source == person_id,
            }
            for person_id, source in zip(ids, order)
        ],
    }


def scenario_prompts(person: dict[str, Any]) -> list[dict[str, Any]]:
    prompts = []
    for scenario in SCENARIOS:
        shared = person["inputs"]["same_background"].replace(
            "是否把一份共享备忘录交给同事继续改",
            scenario,
        )
        prompts.append(
            {
                "scenario": scenario,
                "without_bazi": shared + "本组不附八字。\n",
                "with_bazi": shared + f"本组附上八字：{person['persona']['chart']['pillars']}。八字不决定职业。\n",
                "behavior_output": None,
                "model_run": False,
            }
        )
    return prompts


def check_integrity(people: list[dict[str, Any]], shuffle: dict[str, Any]) -> dict[str, Any]:
    pillars = {item["persona"]["persona_id"]: item["persona"]["chart"]["pillars"] for item in people}
    for item in people:
        own = item["persona"]["chart"]["pillars"]
        if own in item["inputs"]["without_bazi"]:
            raise ExperimentIntegrityError("无八字输入泄漏了四柱。")
        if item["persona"]["synthetic_occupation"]["is_bazi_fact"] is not False:
            raise ExperimentIntegrityError("研究设定职业被标成了八字事实。")
        if item["inputs"]["model_run"] is not False:
            raise ExperimentIntegrityError("离线导出不能标记为已调用模型。")
    for pair in shuffle["pairs"]:
        if pair["pillars"] not in pillars.values():
            raise ExperimentIntegrityError("打乱对照出现了队列之外的八字。")
    return {
        "people": len(people),
        "scenarios": len(SCENARIOS),
        "leakage_without_bazi": "not_detected",
        "occupation_marked_research_setting": True,
        "behavior_outputs_invented": 0,
        "model_calls": 0,
    }


def refuse_accuracy_score(record: dict[str, Any]) -> None:
    if record.get("model_run") is not True:
        raise ExperimentIntegrityError("未调用模型，不能记行为准确率。")
    if record.get("simulated_role_output") is True or record.get("usable_as_human_ground_truth") is False:
        raise ExperimentIntegrityError("模拟或假说不能当作真人预测准确率。")
    raise ExperimentIntegrityError("当前没有已授权的真人行为标签，不能记准确率。")


def run_persona_experiment() -> dict[str, Any]:
    people = build_cohort()
    shuffle = shuffled_charts(people)
    prompts = {item["persona"]["persona_id"]: scenario_prompts(item) for item in people}
    integrity = check_integrity(people, shuffle)
    diagnosis = llm_diagnose()
    return {
        "kind": "engineering_sandbox_not_accuracy",
        "accuracy_claimed": False,
        "model_calls": 0,
        "llm_diagnosis": diagnosis,
        "integrity": integrity,
        "shuffle": shuffle,
        "people": [
            {
                "persona_id": item["persona"]["persona_id"],
                "fictional": True,
                "pillars": item["persona"]["chart"]["pillars"],
                "synthetic_occupation": item["persona"]["synthetic_occupation"],
                "graph": item["graph"],
                "inputs": item["inputs"],
            }
            for item in people
        ],
        "scenario_prompts": prompts,
    }


def dry_run_plan() -> str:
    return "\n".join(
        [
            "# 人物沙盒实验的 dry-run 计划",
            "",
            "这不是实验结果。模型调用次数为 0。",
            "",
            "若以后环境里明确提供 `ZHOUYI_LLM_API_KEY`，才可以进入受控调用。调用前仍要：",
            "",
            "1. 固定模型名、温度、max_tokens、每个场景一次调用。",
            "2. 三组输入使用同一事前背景：无八字、本人的八字、打乱后的八字。",
            "3. 不把八字衍生职业写进已知背景。",
            "4. 记录实际 prompt token 与 completion token。等字节不是等 token。",
            "5. 臂 A 只作为聊天基线，不称作原版 MiroFish。OASIS 仍需单独接通。",
            "6. 没有本人同意的未来行为标签时，输出只能存档，不能写成准确率。",
            "",
            "当前诊断不会读取或打印密钥。编码代理的这次对话也不是受控实验模型。",
            "",
        ]
    )


def write_persona_experiment() -> Path:
    payload = run_persona_experiment()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUT / "DRY_RUN_PLAN.md").write_text(dry_run_plan(), encoding="utf-8")
    (OUT / "llm_diagnosis.json").write_text(
        json.dumps(payload["llm_diagnosis"], ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return OUT / "result.json"

