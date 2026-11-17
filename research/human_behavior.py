# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Schema for human-behavior records. No consented file is shipped."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from research.bazi import four_pillars

ALLOWED_DOMAINS = {"cooperation", "communication", "choice", "participation"}
BLOCKER = (
    "没有本人同意、可核验的真实职业或未来行为记录。"
    "不收集未授权的出生时间，也不用虚构人物或历史名人补成验证样本。"
)


class ConsentBlocked(RuntimeError):
    """Real-person validation cannot proceed."""


def validate_real_record(record: dict[str, Any]) -> dict[str, Any]:
    """Accept only a consented record. This repository does not include one."""

    if record.get("authorization") != "self_consented":
        raise ConsentBlocked(BLOCKER)
    if not record.get("consent_reference"):
        raise ConsentBlocked("缺少可核验的同意引用。")
    if record.get("fictional") is True or record.get("simulated_role_output") is True:
        raise ConsentBlocked("模拟角色输出不能当作真人标签。")
    domain = record.get("domain")
    if domain not in ALLOWED_DOMAINS:
        raise ConsentBlocked("只接受合作、沟通、选择或参与，不接受信贷、招聘或违法倾向。")
    background = record.get("prior_background")
    if not isinstance(background, dict) or background.get("contains_bazi_derived_hypothesis") is True:
        raise ConsentBlocked("八字衍生假设不能混进已知背景。")
    label = record.get("behavior_label")
    if not isinstance(label, dict) or label.get("independently_observed") is not True:
        raise ConsentBlocked("行为标签必须独立观察，不能由八字或模型生成。")
    birth = record.get("birth")
    if not isinstance(birth, dict) or birth.get("authorized") is not True:
        raise ConsentBlocked("出生时间未经本人授权，不排八字。")
    clock = birth.get("clock")
    if clock:
        four_pillars(datetime.fromisoformat(clock), hour_known=True)
    return {
        "status": "schema_accepted_not_a_score",
        "engineering_only": False,
        "accuracy_claim": None,
    }


def exploratory_case_controls() -> dict[str, Any]:
    """Pair public cases without scoring accuracy.

    The shuffle is one fixed permutation. It is not a full permutation
    distribution and not a blind test.
    """

    from research.rngutil import HmacCounter, fisher_yates

    path = Path(__file__).resolve().parent / "cases" / "public_figures.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    ids = [case["person_id"] for case in cases]
    shuffled = fisher_yates(ids, HmacCounter("persona-case-control-v1", "shuffle-v1"))
    return {
        "accuracy_scored": False,
        "blind_test": False,
        "sample_supports_validity_claim": False,
        "real_chart": [
            {
                "person_id": case["person_id"],
                "chart_status": case["chart_status"],
                "career_facts": case["career_source"]["facts"],
            }
            for case in cases
        ],
        "shuffled_pairing": [
            {"chart_from": source, "career_facts_from": target}
            for source, target in zip(ids, shuffled)
        ],
        "shuffle_is_full_distribution": False,
        "non_divination_control": [
            {"person_id": case["person_id"], "year": case["gregorian_date"][:4], "place": case["place"]}
            for case in cases
        ],
    }


def real_validation_status() -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": BLOCKER,
        "records_in_repo": 0,
        "four_arm_model_run": False,
        "oasis_connected": False,
    }
