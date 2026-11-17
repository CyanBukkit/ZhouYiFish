# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Fictional persona sandbox. Charts do not supply real behavior labels."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from research.bazi import four_pillars

# Editable traditional imagery. Not a destiny table and not a validation label.
OCCUPATION_HYPOTHESIS = {
    "甲": ["文书沟通", "教学协助"],
    "乙": ["园艺协作", "资料整理"],
    "丙": ["公开讲解", "活动联络"],
    "丁": ["灯下编辑", "小型咨询"],
    "戊": ["仓储协调", "场地值守"],
    "己": ["后勤照料", "社区记录"],
    "庚": ["工具维护", "流程核对"],
    "辛": ["精细校对", "样品登记"],
    "壬": ["路线沟通", "信息转发"],
    "癸": ["夜间值班记录", "雨水无关的室内归档"],
}


class PersonaError(ValueError):
    """A sandbox object was used as if it were a real human label."""


def hypothetical_occupations(day_pillar: str) -> dict[str, Any]:
    stem = day_pillar[0]
    return {
        "source": "bazi_day_stem_hypothesis",
        "usable_as_validation_label": False,
        "claim": "传统类象假设，可编辑，不表示八字客观决定职业。",
        "candidates": list(OCCUPATION_HYPOTHESIS[stem]),
    }


def build_fictional_persona(
    persona_id: str,
    birth: datetime,
    *,
    display_name: str,
    living_place_label: str,
) -> dict[str, Any]:
    if not persona_id.startswith("sandbox-"):
        raise PersonaError("虚构人物编号必须以 sandbox- 开头，避免和真实个案混用。")
    chart = four_pillars(birth, hour_known=True)
    occupations = hypothetical_occupations(str(chart["day_pillar"]))
    return {
        "persona_id": persona_id,
        "fictional": True,
        "real_identity": None,
        "display_name": display_name,
        "birth": {
            "fictional": True,
            "clock": birth.isoformat(),
            "note": "拟定时刻，不是任何人的出生资料。",
        },
        "living_place_label": living_place_label,
        "chart": chart,
        "occupation_hypothesis": occupations,
        "occupation_label": None,
    }


def build_relationship_graph(focal_id: str) -> dict[str, Any]:
    return {
        "fictional": True,
        "usable_as_validation_label": False,
        "nodes": [
            {"id": focal_id, "fictional": True, "kind": "focal"},
            {"id": "sandbox-colleague-01", "fictional": True, "kind": "colleague"},
            {"id": "sandbox-neighbor-01", "fictional": True, "kind": "neighbor"},
        ],
        "edges": [
            {"source": focal_id, "target": "sandbox-colleague-01", "relation": "同一工作小组"},
            {"source": focal_id, "target": "sandbox-neighbor-01", "relation": "同一楼层邻居"},
        ],
    }


def simulated_cooperation_output(persona_id: str, choice: str) -> dict[str, Any]:
    if choice not in {"cooperate", "decline"}:
        raise PersonaError("沙盒场景只接受 cooperate 或 decline。")
    return {
        "persona_id": persona_id,
        "scenario": "是否把一份共享备忘录交给同事继续改",
        "choice": choice,
        "simulated_role_output": True,
        "usable_as_human_ground_truth": False,
    }


def assert_not_validation_label(label: dict[str, Any]) -> None:
    if label.get("usable_as_validation_label") is False or label.get("simulated_role_output") is True:
        raise PersonaError("从八字假设或角色模拟得到的职业/行为不能当作验证八字的真实标签。")
    if label.get("source") == "bazi_day_stem_hypothesis":
        raise PersonaError("八字衍生职业不是独立取得的职业标签。")
