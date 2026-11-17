# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Fictional persona sandbox. Charts do not supply real behavior labels."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from research.bazi import four_pillars

# Editable traditional imagery. Not a destiny table and not a validation label.
# Human-written job titles for the sandbox. They look like ordinary occupations
# and are not quotations from a classical fortune-telling manual.
OCCUPATION_HYPOTHESIS = {
    "甲": ["中学语文教师", "出版社编辑"],
    "乙": ["城市园艺技师", "公共图书馆助理"],
    "丙": ["社区活动组织者", "博物馆讲解员"],
    "丁": ["杂志校对编辑", "社区法律咨询助理"],
    "戊": ["仓库管理员", "校园场地管理员"],
    "己": ["社区档案管理员", "养老院生活助理"],
    "庚": ["自行车维修技师", "实验室设备管理员"],
    "辛": ["药店调剂员", "博物馆藏品登记员"],
    "壬": ["公交调度员", "社区信息站值班员"],
    "癸": ["夜班档案值班员", "室内资料归档员"],
}


class PersonaError(ValueError):
    """A sandbox object was used as if it were a real human label."""


def hypothetical_occupations(day_pillar: str) -> dict[str, Any]:
    stem = day_pillar[0]
    return {
        "field_class": "hypothesis",
        "source": "sandbox_protocol_v1_human_set_table",
        "citation": "研究沙盒自行编写的日干类象表，不是古籍引文。",
        "usable_as_validation_label": False,
        "is_bazi_fact": False,
        "claim": "人为设定的候选，可编辑，不表示八字客观决定职业。",
        "candidates": list(OCCUPATION_HYPOTHESIS[stem]),
    }


def select_synthetic_occupation(candidates: list[str], chosen: str) -> dict[str, Any]:
    if chosen not in candidates:
        raise PersonaError("选定职业必须来自当前候选，不能另写一个未列出的头衔。")
    return {
        "field_class": "synthetic_research_setting",
        "title": chosen,
        "is_bazi_fact": False,
        "usable_as_validation_label": False,
        "selected_from_candidates": list(candidates),
        "editor": "sandbox_protocol_v1",
        "note": "这是研究设定的虚构职业，不是八字推算出的事实。",
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
        "synthetic_occupation": None,
        "occupation_label": None,
    }


def assign_synthetic_occupation(persona: dict[str, Any], chosen: str) -> dict[str, Any]:
    copied = dict(persona)
    copied["synthetic_occupation"] = select_synthetic_occupation(
        list(persona["occupation_hypothesis"]["candidates"]),
        chosen,
    )
    return copied


def build_relationship_graph(focal_id: str, occupation_title: str) -> dict[str, Any]:
    return {
        "field_class": "synthetic",
        "fictional": True,
        "usable_as_validation_label": False,
        "nodes": [
            {
                "id": focal_id,
                "fictional": True,
                "kind": "focal",
                "synthetic_occupation": occupation_title,
            },
            {
                "id": "sandbox-colleague-01",
                "fictional": True,
                "kind": "colleague",
                "synthetic_occupation": "社区档案室同事",
            },
            {
                "id": "sandbox-neighbor-01",
                "fictional": True,
                "kind": "neighbor",
                "synthetic_occupation": None,
            },
        ],
        "edges": [
            {
                "source": focal_id,
                "target": "sandbox-colleague-01",
                "relation": f"一起做{occupation_title}",
            },
            {"source": focal_id, "target": "sandbox-neighbor-01", "relation": "同一楼层邻居"},
        ],
    }


def export_same_background_inputs(persona: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    """Two prompts with the same setting. No model is called."""

    occupation = persona.get("synthetic_occupation") or {}
    if not occupation.get("title"):
        raise PersonaError("导出前必须已经选定虚构职业。")
    shared = (
        f"人物编号：{persona['persona_id']}。虚构。\n"
        f"生活环境：{persona['living_place_label']}。\n"
        f"研究设定职业：{occupation['title']}。这不是八字事实。\n"
        f"关系：{graph['edges'][0]['relation']}；{graph['edges'][1]['relation']}。\n"
        "场景：是否把一份共享备忘录交给同事继续改。只讨论合作或拒绝。\n"
    )
    chart = persona["chart"]["pillars"]
    without = shared + "本组不附八字。\n"
    with_chart = shared + f"本组附上八字：{chart}。八字不决定职业。\n"
    return {
        "model_run": False,
        "llm_called": False,
        "field_classes": {
            "birth_and_chart": "fictional",
            "occupation": "synthetic_research_setting",
            "graph": "synthetic",
            "behavior": "not_generated",
        },
        "without_bazi": without,
        "with_bazi": with_chart,
        "same_background": shared,
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
