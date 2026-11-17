# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Write the fictional persona demo. No real birth data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from research.human_behavior import exploratory_case_controls, real_validation_status
from research.persona import (
    build_fictional_persona,
    build_relationship_graph,
    simulated_cooperation_output,
)
from research.calendar_time import SHANGHAI

SANDBOX = Path(__file__).resolve().parent / "sandbox"


def demo_bundle() -> dict[str, object]:
    birth = datetime(2001, 6, 15, 10, 30, tzinfo=SHANGHAI)
    persona = build_fictional_persona(
        "sandbox-focal-01",
        birth,
        display_name="沙盒甲",
        living_place_label="虚构街区，不是真实地址",
    )
    return {
        "object": "fictional_human_persona_sandbox",
        "persona": persona,
        "graph": build_relationship_graph(persona["persona_id"]),
        "simulated_behavior": simulated_cooperation_output(persona["persona_id"], "cooperate"),
        "historical_cases": exploratory_case_controls(),
        "real_validation": real_validation_status(),
        "weather_answers_this_question": False,
    }


def write_demo() -> Path:
    SANDBOX.mkdir(parents=True, exist_ok=True)
    path = SANDBOX / "demo_persona.json"
    path.write_text(
        json.dumps(demo_bundle(), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
