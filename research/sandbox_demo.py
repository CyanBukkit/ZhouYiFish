# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Write the fictional persona demo. No real birth data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from research.human_behavior import exploratory_case_controls, real_validation_status
from research.persona import (
    assign_synthetic_occupation,
    build_fictional_persona,
    build_relationship_graph,
    export_same_background_inputs,
    simulated_cooperation_output,
)
from research.calendar_time import SHANGHAI

SANDBOX = Path(__file__).resolve().parent / "sandbox"


def demo_bundle() -> dict[str, object]:
    birth = datetime(2001, 6, 15, 10, 30, tzinfo=SHANGHAI)
    persona = assign_synthetic_occupation(
        build_fictional_persona(
            "sandbox-focal-01",
            birth,
            display_name="沙盒甲",
            living_place_label="虚构街区的社区档案室，不是真实地址",
        ),
        "社区记录",
    )
    graph = build_relationship_graph(
        persona["persona_id"],
        persona["synthetic_occupation"]["title"],
    )
    inputs = export_same_background_inputs(persona, graph)
    return {
        "object": "fictional_human_persona_sandbox",
        "persona": persona,
        "graph": graph,
        "same_background_inputs": inputs,
        "simulated_behavior": simulated_cooperation_output(persona["persona_id"], "cooperate"),
        "historical_cases": exploratory_case_controls(),
        "real_validation": real_validation_status(),
        "weather_answers_this_question": False,
    }


def example_markdown(bundle: dict[str, object]) -> str:
    persona = bundle["persona"]
    occupation = persona["synthetic_occupation"]
    inputs = bundle["same_background_inputs"]
    return "\n".join(
        [
            "# 虚构人物示例",
            "",
            "沙盒甲不是真人。出生时刻是拟定的。职业是研究设定，不是八字事实。",
            "",
            f"编号：{persona['persona_id']}",
            f"拟定时刻：{persona['birth']['clock']}",
            f"四柱：{persona['chart']['pillars']}",
            f"候选职业：{'、'.join(persona['occupation_hypothesis']['candidates'])}",
            f"选定职业：{occupation['title']}",
            "选定职业的字段类别是 synthetic_research_setting，is_bazi_fact 为假。",
            "生活环境：虚构街区的社区档案室。",
            "关系：与一位同事一起做社区记录，并有一位同楼邻居。",
            "",
            "下面两段输入使用同一背景。第二段只多出八字。没有调用模型。",
            "",
            "## 无八字",
            "",
            inputs["without_bazi"],
            "## 有八字",
            "",
            inputs["with_bazi"],
            "",
        ]
    )


def write_demo() -> Path:
    SANDBOX.mkdir(parents=True, exist_ok=True)
    bundle = demo_bundle()
    path = SANDBOX / "demo_persona.json"
    path.write_text(
        json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (SANDBOX / "EXAMPLE.md").write_text(example_markdown(bundle), encoding="utf-8")
    return path
