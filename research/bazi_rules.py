# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Versioned rule profile for a reviewable five-step reading.

This is an experimental calculation, not a verified account of anyone's life.
Scores that are not in the cited texts are not invented here. 格局 is not
read off a strength number.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from research.bazi import JIE_BRANCH, four_pillars, term_instant

RULE_VERSION = "yhzp-month-command-v1"
STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
ELEMENTS = ("木", "木", "火", "火", "土", "土", "金", "金", "水", "水")
YANG = {0, 2, 4, 6, 8}
PRODUCES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "火": "金", "土": "水", "金": "木", "水": "火"}
# 本气、中气、余气. 午藏丁己 is one common table; some editions list 己 as 余气 only.
HIDDEN = {
    "子": (("癸", "本气"),),
    "丑": (("己", "本气"), ("癸", "中气"), ("辛", "余气")),
    "寅": (("甲", "本气"), ("丙", "中气"), ("戊", "余气")),
    "卯": (("乙", "本气"),),
    "辰": (("戊", "本气"), ("乙", "中气"), ("癸", "余气")),
    "巳": (("丙", "本气"), ("庚", "中气"), ("戊", "余气")),
    "午": (("丁", "本气"), ("己", "中气")),
    "未": (("己", "本气"), ("丁", "中气"), ("乙", "余气")),
    "申": (("庚", "本气"), ("壬", "中气"), ("戊", "余气")),
    "酉": (("辛", "本气"),),
    "戌": (("戊", "本气"), ("辛", "中气"), ("丁", "余气")),
    "亥": (("壬", "本气"), ("甲", "中气")),
}
SEASON = {
    "寅": "春", "卯": "春", "辰": "春",
    "巳": "夏", "午": "夏", "未": "夏",
    "申": "秋", "酉": "秋", "戌": "秋",
    "亥": "冬", "子": "冬", "丑": "冬",
}
# 旺相休囚死 by season, from the standard seasonal cycle. 土旺四季 is a separate school.
PHASE = {
    "春": {"木": "旺", "火": "相", "水": "休", "金": "囚", "土": "死"},
    "夏": {"火": "旺", "土": "相", "木": "休", "水": "囚", "金": "死"},
    "秋": {"金": "旺", "水": "相", "土": "休", "火": "囚", "木": "死"},
    "冬": {"水": "旺", "木": "相", "金": "休", "土": "囚", "火": "死"},
}
LU = {"甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳", "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子"}
BLADE = {"甲": "卯", "丙": "午", "戊": "午", "庚": "酉", "壬": "子"}
STEM_HE = {"甲己": "土", "乙庚": "金", "丙辛": "水", "丁壬": "木", "戊癸": "火"}
BRANCH_HE = {"子丑": "土", "寅亥": "木", "卯戌": "火", "辰酉": "金", "巳申": "水", "午未": "土"}
CHONG = ("子午", "丑未", "寅申", "卯酉", "辰戌", "巳亥")
HARM = ("子未", "丑午", "寅巳", "卯辰", "申亥", "酉戌")
XING_GROUPS = (("寅", "巳", "申"), ("丑", "戌", "未"))
SELF_XING = set("辰午酉亥")
TRANSFORM_BRANCHES = {"土": set("辰戌丑未"), "金": set("申酉"), "水": set("亥子"), "木": set("寅卯"), "火": set("巳午")}
SUPPORT = {"正印", "偏印", "比肩", "劫财"}
DRAIN = {"正官", "七杀", "食神", "伤官", "正财", "偏财"}
REGULAR = {"正官", "七杀", "正印", "偏印", "正财", "偏财", "食神", "伤官"}
PROFILE = {
    "id": RULE_VERSION,
    "name": "月令取格扶抑剖面",
    "claim": "规则演算和实验解读，不是已经验证的现实命运。",
    "sources": [
        "十神与月令框架沿通行子平教学，公开讨论见《渊海子平》一类文献，本仓库没有做校勘。",
        "取格采用《子平真诠》「八字用神，专求月令」的月令取格约定：先看月支本气的十神，透干才立正格。",
        "藏干用本气、中气、余气的通行表。午藏丁为本气、己为中气；有的版本把己只列为余气。",
        "季节旺相休囚死用春木、夏火、秋金、冬水的通行表。土旺于辰戌丑未是另一派，只作分歧，不并进判断。",
        "喜忌只实现扶抑。调候出自《穷通宝鉴》一派，这里不逐日干月令查表。",
        "起运数到节，三日折一年、一日折四月、一个时辰折十日。余日再按 30 日进一月，这是本剖面的进位，不是古书唯一原文。",
        "年柱与流年年界用立春时刻，与 research/bazi.py 相同。真太阳时和子初换日没有实现。",
    ],
    "disagreements": [
        "土在四季月到底算不当令还是土旺，两派并存。判断看月令本气五行，不把四季土自动改成得令。",
        "午未合，有的书合土，有的书合火。本剖面记合土，并保留这条分歧。",
        "合是否化，条件各家不同。见合只记合绊；即使月令支持所合之行，也只标化候选，不判必然化。",
    ],
}


def stem_info(stem: str) -> dict[str, str]:
    index = STEMS.index(stem)
    return {"stem": stem, "yin_yang": "阳" if index in YANG else "阴", "element": ELEMENTS[index], "index": index}


def ten_god(day_stem: str, other: str) -> str:
    if other == day_stem:
        return "比肩"
    day = stem_info(day_stem)
    target = stem_info(other)
    same = day["yin_yang"] == target["yin_yang"]
    if target["element"] == day["element"]:
        return "比肩" if same else "劫财"
    if PRODUCES[day["element"]] == target["element"]:
        return "食神" if same else "伤官"
    if CONTROLS[day["element"]] == target["element"]:
        return "偏财" if same else "正财"
    if CONTROLS[target["element"]] == day["element"]:
        return "七杀" if same else "正官"
    if PRODUCES[target["element"]] == day["element"]:
        return "偏印" if same else "正印"
    raise ValueError(f"无法映射十神：{day_stem} {other}")


def _pair_key(left: str, right: str, table: dict[str, str]) -> str | None:
    key = left + right
    if key in table:
        return table[key]
    swapped = right + left
    if swapped in table:
        return table[swapped]
    return None


def _positions(pillars: str) -> list[dict[str, str]]:
    if len(pillars) != 8:
        raise ValueError("四柱必须是八个字。")
    names = ("年", "月", "日", "时")
    return [
        {"position": names[index], "stem": pillars[index * 2], "branch": pillars[index * 2 + 1]}
        for index in range(4)
    ]


def _pillar_rows(day_stem: str, pillars: str) -> list[dict[str, Any]]:
    rows = []
    for item in _positions(pillars):
        hidden = []
        for stem, qi in HIDDEN[item["branch"]]:
            hidden.append({"stem": stem, "qi": qi, "ten_god": ten_god(day_stem, stem), "element": stem_info(stem)["element"]})
        stem_god = "日主" if item["position"] == "日" else ten_god(day_stem, item["stem"])
        rows.append({**item, "stem_ten_god": stem_god, "stem_element": stem_info(item["stem"])["element"], "hidden": hidden})
    return rows


def _relations(rows: list[dict[str, Any]], month_branch: str) -> list[dict[str, Any]]:
    found = []
    stems = [row["stem"] for row in rows]
    branches = [row["branch"] for row in rows]
    for left, right in ((0, 1), (1, 2), (2, 3)):
        element = _pair_key(stems[left], stems[right], STEM_HE)
        if element:
            transform = month_branch in TRANSFORM_BRANCHES[element]
            found.append({
                "kind": "天干五合",
                "between": [rows[left]["position"], rows[right]["position"]],
                "pair": stems[left] + stems[right],
                "adjacent": True,
                "recorded_element": element,
                "transform": "化候选" if transform else "不化",
                "transform_reason": "月令五行与所合之行同类，仍不判必然化。" if transform else "月令不是所合之行的当令支，只记合绊。",
            })
    for left, right in ((0, 1), (1, 2), (2, 3)):
        element = _pair_key(branches[left], branches[right], BRANCH_HE)
        if not element:
            continue
        note = "午未合在有的书里作合火，本剖面记合土。" if {branches[left], branches[right]} == {"午", "未"} else ""
        transform = month_branch in TRANSFORM_BRANCHES[element]
        found.append({
            "kind": "地支六合",
            "between": [rows[left]["position"], rows[right]["position"]],
            "pair": branches[left] + branches[right],
            "adjacent": True,
            "recorded_element": element,
            "transform": "化候选" if transform else "不化",
            "note": note,
            "transform_reason": "见合不一律作化。",
        })
    for left in range(4):
        for right in range(left + 1, 4):
            pair = _pair_key(branches[left], branches[right], {item: item for item in (*CHONG, *HARM)})
            if pair in CHONG or (branches[left] + branches[right] in CHONG) or (branches[right] + branches[left] in CHONG):
                found.append({"kind": "六冲", "between": [rows[left]["position"], rows[right]["position"]], "pair": branches[left] + branches[right], "adjacent": right == left + 1})
            if (branches[left] + branches[right] in HARM) or (branches[right] + branches[left] in HARM):
                found.append({"kind": "六害", "between": [rows[left]["position"], rows[right]["position"]], "pair": branches[left] + branches[right], "adjacent": right == left + 1})
    present = set(branches)
    for group in XING_GROUPS:
        hit = [branch for branch in group if branch in present]
        if len(hit) >= 2:
            found.append({"kind": "三刑", "branches": hit, "complete": len(hit) == 3, "note": "三字不齐只记录已出现的字，不补成全刑。"})
    if "子" in present and "卯" in present:
        found.append({"kind": "子卯刑", "branches": ["子", "卯"], "complete": True})
    for branch in SELF_XING:
        if branches.count(branch) >= 2:
            found.append({"kind": "自刑", "branch": branch, "count": branches.count(branch)})
    return found


def strength(rows: list[dict[str, Any]]) -> dict[str, Any]:
    day = rows[2]
    day_stem = day["stem"]
    day_element = stem_info(day_stem)["element"]
    month = rows[1]
    command = month["hidden"][0]
    season = SEASON[month["branch"]]
    phase = PHASE[season][day_element]
    de_ling = command["element"] == day_element
    roots = []
    hidden_drain = []
    for row in rows:
        for item in row["hidden"]:
            if item["stem"] == day_stem:
                roots.append({"where": row["position"], "stem": item["stem"], "qi": item["qi"], "kind": "同干"})
            elif item["element"] == day_element:
                roots.append({"where": row["position"], "stem": item["stem"], "qi": item["qi"], "kind": "同五行不同干"})
            if item["qi"] == "本气" and item["ten_god"] in DRAIN:
                hidden_drain.append({"where": row["position"], "stem": item["stem"], "ten_god": item["ten_god"]})
    visible_support = []
    visible_drain = []
    for row in (rows[0], rows[1], rows[3]):
        god = row["stem_ten_god"]
        entry = {"where": row["position"], "stem": row["stem"], "ten_god": god}
        if god in SUPPORT:
            visible_support.append(entry)
        elif god in DRAIN:
            visible_drain.append(entry)
    same_stem_root = any(item["kind"] == "同干" for item in roots)
    same_element_root = any(item["kind"] == "同五行不同干" for item in roots)
    command_drain = [item for item in hidden_drain if item["ten_god"] in DRAIN]
    path = [
        f"月令本气是{command['stem']}{command['element']}，日主{day_stem}{day_element}。{'本气同行，记为得令。' if de_ling else '本气不同行，记为不得本气之令。'}",
        f"季节是{season}，日主五行在旺相休囚死表中为「{phase}」。这不是五行个数。",
        "土旺四季只作为分歧保留：辰戌丑未不因为是土月就把日主改判得令，除非本气五行本来就是日主五行。",
        f"同干通根 {len([item for item in roots if item['kind']=='同干'])} 处，同五行不同干 {len([item for item in roots if item['kind']!='同干'])} 处。",
        f"天干生扶 {len(visible_support)} 个，天干克泄耗 {len(visible_drain)} 个。地支本气克泄耗 {len(command_drain)} 处。",
    ]
    if de_ling and same_stem_root and not visible_drain and not command_drain:
        verdict = "strong_candidate"
        label = "偏旺候选"
        why = "月令本气与日主同行，本气或同干有根，天干和地支本气都没有克泄耗。"
    elif (not de_ling) and (not same_stem_root) and (not same_element_root) and (not visible_support) and visible_drain and CONTROLS[command["element"]] == day_element:
        verdict = "weak_candidate"
        label = "偏弱候选"
        why = "月令本气克日主，没有木同类通根，天干没有印比，并且天干已有克泄耗。" if day_element == "木" else "月令本气克日主，没有同干或同五行通根，天干没有印比，并且天干已有克泄耗。"
    else:
        verdict = "uncertain"
        label = "不确定"
        why = "得令、通根、透干生扶和克泄耗没有同时倒向一边。本剖面不把这种盘收成身旺或身弱。"
    return {
        "step": 1,
        "name": "旺衰",
        "depends_on": ["四柱", "月令本气", "藏干", "十神"],
        "day_master": stem_info(day_stem),
        "month_command": {"branch": month["branch"], **command},
        "season": season,
        "seasonal_phase": phase,
        "de_ling": de_ling,
        "roots": roots,
        "visible_support": visible_support,
        "visible_drain": visible_drain,
        "branch_benqi_drain": command_drain,
        "path": path,
        "verdict": verdict,
        "verdict_label": label,
        "reason": why,
        "engineering_index": None,
        "engineering_note": "没有采用五行个数或自定权重。没有出处的分数不计算。",
        "earth_season_school": "未并入" if month["branch"] in "辰戌丑未" else "本月不是辰戌丑未，这条分歧不改变本气。",
    }


def structure(rows: list[dict[str, Any]], strength_result: dict[str, Any]) -> dict[str, Any]:
    day_stem = rows[2]["stem"]
    month = rows[1]
    command = month["hidden"][0]
    command_god = command["ten_god"]
    visible = {row["stem"] for row in (rows[0], rows[1], rows[3])}
    candidates = []
    excluded = []
    penetrated = command["stem"] in visible
    if command_god in REGULAR and penetrated:
        candidates.append({"name": f"{command_god}格", "status": "成格候选", "reason": f"月令本气{command['stem']}为{command_god}，且透出天干。"})
    elif command_god in REGULAR:
        excluded.append({"name": f"{command_god}格", "reason": f"月令本气是{command_god}，但{command['stem']}没有透出年、月、时干。"})
    else:
        excluded.append({"name": f"{command_god}正格", "reason": "月令本气是比肩或劫财，不立为财官印食正格。"})
    for item in month["hidden"][1:]:
        if item["ten_god"] in REGULAR and item["stem"] in visible:
            candidates.append({"name": f"{item['ten_god']}格", "status": "杂气或余气透出候选", "reason": f"月令{item['qi']}{item['stem']}为{item['ten_god']}并且透干。不因本气未透就升成唯一正格。"})
    if month["branch"] == LU[day_stem]:
        candidates.append({"name": "建禄", "status": "月令为禄", "reason": f"月支{month['branch']}是{day_stem}的禄。这不是由旺衰结论推出来的。"})
    if day_stem in BLADE and month["branch"] == BLADE[day_stem]:
        candidates.append({"name": "月刃", "status": "阳干月刃", "reason": f"月支{month['branch']}是{day_stem}的阳刃。"})
    for row in (rows[0], rows[1], rows[3]):
        if row["stem_ten_god"] in REGULAR and row["stem"] not in {item["stem"] for item in month["hidden"]}:
            excluded.append({"name": f"月令{row['stem_ten_god']}格", "reason": f"{row['position']}干{row['stem']}是{row['stem_ten_god']}，但不在月支藏干里，不取月令格。"})
    established = next((item for item in candidates if item["status"] == "成格候选"), None)
    if established is None:
        established = next((item for item in candidates if item["name"] == "建禄"), None)
    rooted = bool(strength_result["roots"]) or any(row["stem_ten_god"] in {"比肩", "劫财"} for row in (rows[0], rows[1], rows[3]))
    unsupported = [
        {"name": "从格", "status": "unsupported", "reason": "有同干、同五行根或比劫透干，不能套从格。" if rooted else "即使缺少明显通根，本剖面也不判从格。"},
        {"name": "化气格", "status": "unsupported", "reason": "化气格没有实现，不能因为天干五合就判化气。"},
    ]
    return {
        "step": 2,
        "name": "格局",
        "depends_on": ["月令藏干", "十神", "透干"],
        "method": "月令本气取格",
        "source": "《子平真诠》月令取格约定；建禄按日主禄支，不按旺衰分数。",
        "not_derived_from_strength_verdict": True,
        "strength_verdict_ignored": strength_result["verdict"],
        "candidates": candidates,
        "established": established,
        "excluded": excluded,
        "unsupported": unsupported,
    }


def useful(rows: list[dict[str, Any]], strength_result: dict[str, Any], structure_result: dict[str, Any]) -> dict[str, Any]:
    month_branch = rows[1]["branch"]
    verdict = strength_result["verdict"]
    conditional = []
    if month_branch in "巳午未":
        conditional.append({"name": "调候", "item": "火令月有人会再考虑水来调燥", "status": "条件项", "source": "《穷通宝鉴》一派未逐条实现，不并入扶抑。"})
    if month_branch in "亥子丑":
        conditional.append({"name": "调候", "item": "水令月有人会再考虑火来调寒", "status": "条件项", "source": "《穷通宝鉴》一派未逐条实现，不并入扶抑。"})
    gods = [row["stem_ten_god"] for row in (rows[0], rows[1], rows[3])]
    if any(god in {"正官", "七杀"} for god in gods) and any(god in {"比肩", "劫财"} for god in gods):
        conditional.append({"name": "通关", "item": "官杀与比劫同透，通关只保留为条件，不另选一个通关用神。", "status": "条件项", "source": "本剖面没有通关公式。"})
    if verdict == "strong_candidate":
        favorable, unfavorable = ["正官", "七杀", "食神", "伤官", "正财", "偏财"], ["正印", "偏印", "比肩", "劫财"]
        reason = "扶抑：偏旺候选则喜克泄耗，忌印比。日干不映射职业。"
    elif verdict == "weak_candidate":
        favorable, unfavorable = ["正印", "偏印", "比肩", "劫财"], ["正官", "七杀", "食神", "伤官", "正财", "偏财"]
        reason = "扶抑：偏弱候选则喜印比，忌克泄耗。日干不映射职业。"
    else:
        favorable, unfavorable = [], []
        conditional.append({"name": "扶抑未决", "item": "若以后证据改判偏旺，喜克泄耗、忌印比。若改判偏弱，则相反。", "status": "有条件", "source": "旺衰结论是不确定。"})
        reason = "旺衰不确定，所以不输出单一喜用。"
    return {
        "step": 3,
        "name": "喜忌",
        "depends_on": ["旺衰结论", "天干十神"],
        "method": "扶抑",
        "scope": "只实现扶抑。调候和通关是条件项。",
        "structure_name": (structure_result.get("established") or {}).get("name"),
        "favorable": favorable,
        "unfavorable": unfavorable,
        "conditional": conditional,
        "reason": reason,
        "does_not_determine_occupation": True,
    }


def ten_god_step(rows: list[dict[str, Any]], strength_result: dict[str, Any], structure_result: dict[str, Any], useful_result: dict[str, Any]) -> dict[str, Any]:
    distribution: dict[str, int] = {}
    for row in rows:
        if row["stem_ten_god"] != "日主":
            distribution[row["stem_ten_god"]] = distribution.get(row["stem_ten_god"], 0) + 1
        for item in row["hidden"]:
            distribution[item["ten_god"]] = distribution.get(item["ten_god"], 0) + 1
    favorable = set(useful_result["favorable"])
    marks = []
    for row in rows:
        if row["stem_ten_god"] in favorable:
            marks.append({"where": row["position"] + "干", "ten_god": row["stem_ten_god"], "relation": "落在当前扶抑的喜里"})
        elif row["stem_ten_god"] in useful_result["unfavorable"]:
            marks.append({"where": row["position"] + "干", "ten_god": row["stem_ten_god"], "relation": "落在当前扶抑的忌里"})
    return {
        "step": 4,
        "name": "十神配合",
        "depends_on": ["日主", "旺衰", "格局", "喜忌"],
        "pillars": rows,
        "distribution": distribution,
        "distribution_note": "个数只描述分布，不反过来决定旺衰。",
        "combinations": _relations(rows, rows[1]["branch"]),
        "marks": marks,
        "strength_verdict": strength_result["verdict"],
        "structure": (structure_result.get("established") or {}).get("name"),
        "research_note": "十神可以产生研究性的职业或社交候选，那些候选不是用户的真实职业。",
    }


def _jie_instants(moment: datetime) -> list[tuple[datetime, str, str]]:
    found = []
    for shift in (-1, 0, 1):
        year = moment.year + shift
        for name, branch in JIE_BRANCH:
            found.append((term_instant(year, name), name, branch))
    return sorted(found, key=lambda item: item[0])


def _split_duration(delta: timedelta) -> dict[str, int]:
    seconds = int(round(delta.total_seconds()))
    if seconds < 0:
        raise ValueError("起运目标节早于出生时刻的方向反了。")
    whole_days, rem_seconds = divmod(seconds, 86400)
    years, day_rem = divmod(whole_days, 3)
    months = day_rem * 4
    extra_days = int((rem_seconds / 7200) * 10)
    months += extra_days // 30
    days = extra_days % 30
    return {"years": years, "months": months, "days": days}


def _add_ymd(moment: datetime, years: int, months: int, days: int) -> datetime:
    month_index = moment.month - 1 + months
    year = moment.year + years + month_index // 12
    month = month_index % 12 + 1
    day = moment.day
    while True:
        try:
            landed = moment.replace(year=year, month=month, day=day)
            break
        except ValueError:
            day -= 1
    return landed + timedelta(days=days)


def _shift_pillar(stem: str, branch: str, steps: int) -> str:
    return STEMS[(STEMS.index(stem) + steps) % 10] + BRANCHES[(BRANCHES.index(branch) + steps) % 12]


def direction_from_sex(year_stem: str, sex: str) -> str:
    yang = STEMS.index(year_stem) in YANG
    if sex == "male":
        return "forward" if yang else "backward"
    if sex == "female":
        return "backward" if yang else "forward"
    raise ValueError("传统排运需要明确选择男或女。")


def luck(rows: list[dict[str, Any]], birth: datetime, params: dict[str, Any]) -> dict[str, Any]:
    limits = [
        "真太阳时没有使用出生地。",
        "日界是换到 UTC+8 后的 00:00。23:00 不按子初换日柱。",
        "年界和流年按立春，不按公历元旦或春节。",
        "起运数到节，不数到中气。",
    ]
    mode = params.get("luck_mode") or ""
    sex = params.get("luck_sex") or ""
    manual = params.get("luck_direction") or ""
    if mode == "traditional":
        if sex not in {"male", "female"}:
            return {"step": 5, "name": "大运流年", "status": "incomplete", "reason": "选择了传统男女规则，但没有选择男或女。不猜测，不排运。", "cycles": [], "limits": limits}
        direction = direction_from_sex(rows[0]["stem"], sex)
        source = "traditional_sex"
    elif mode == "manual":
        if manual not in {"forward", "backward"}:
            return {"step": 5, "name": "大运流年", "status": "incomplete", "reason": "选择了手选顺逆，但没有选择顺或逆。", "cycles": [], "limits": limits}
        direction = manual
        source = "manual"
    else:
        return {"step": 5, "name": "大运流年", "status": "incomplete", "reason": "还没有排运参数。可以手选顺逆，或明确选择传统规则所需的性别。不从姓名或职业推断。", "cycles": [], "limits": limits}
    instants = _jie_instants(birth)
    if direction == "forward":
        target = next(item for item in instants if item[0] > birth)
        relation = "下一节"
    else:
        earlier = [item for item in instants if item[0] <= birth]
        target = earlier[-1]
        relation = "上一节或出生当刻的节"
    delta = target[0] - birth if direction == "forward" else birth - target[0]
    parts = _split_duration(delta)
    start = _add_ymd(birth, parts["years"], parts["months"], parts["days"])
    month_stem, month_branch = rows[1]["stem"], rows[1]["branch"]
    step = 1 if direction == "forward" else -1
    cycles = []
    cursor = start
    for index in range(8):
        pillar = _shift_pillar(month_stem, month_branch, step * (index + 1))
        end = _add_ymd(cursor, 10, 0, 0)
        cycles.append({
            "index": index + 1,
            "pillar": pillar,
            "stem_ten_god": ten_god(rows[2]["stem"], pillar[0]),
            "branch_benqi_ten_god": ten_god(rows[2]["stem"], HIDDEN[pillar[1]][0][0]),
            "start": cursor.isoformat(),
            "end": end.isoformat(),
            "age_start": {"years": parts["years"] + index * 10, "months": parts["months"], "days": parts["days"]},
        })
        cursor = end
    liunian = None
    year = params.get("liunian_year")
    if year:
        liunian = annual(rows, birth, cycles, int(year))
    return {
        "step": 5,
        "name": "大运流年",
        "depends_on": ["月柱", "出生时刻", "排运参数", "节气时刻"],
        "status": "complete",
        "direction": direction,
        "direction_label": "顺" if direction == "forward" else "逆",
        "direction_source": source,
        "sex_used": sex if source == "traditional_sex" else None,
        "target_jie": {"name": target[1], "branch": target[2], "at": target[0].isoformat(), "relation": relation},
        "qi_yun": parts,
        "qi_yun_rule": "三日一年，一日四月，一个时辰十日；余日按 30 日进一月。",
        "start_at": start.isoformat(),
        "cycles": cycles,
        "liunian": liunian,
        "limits": limits,
    }


def annual(rows: list[dict[str, Any]], birth: datetime, cycles: list[dict[str, Any]], year: int) -> dict[str, Any]:
    probe = datetime(year, 6, 15, 12, tzinfo=birth.tzinfo)
    year_pillar = str(four_pillars(probe, hour_known=True)["year_pillar"])
    lichun = term_instant(year, "立春")
    active = next((item for item in cycles if datetime.fromisoformat(item["start"]) <= lichun < datetime.fromisoformat(item["end"])), None)
    interactions = []
    natal = [row["branch"] for row in rows]
    for label, branch in (("流年", year_pillar[1]), ("大运", None if active is None else active["pillar"][1])):
        if branch is None:
            continue
        for index, other in enumerate(natal):
            where = ("年", "月", "日", "时")[index]
            if (branch + other in CHONG) or (other + branch in CHONG):
                interactions.append({"kind": "六冲", "who": label, "with": where, "pair": branch + other})
            if _pair_key(branch, other, BRANCH_HE):
                interactions.append({"kind": "六合", "who": label, "with": where, "pair": branch + other, "transform": "不因见合就判化"})
    return {
        "year": year,
        "pillar": year_pillar,
        "year_boundary": "立春",
        "lichun": lichun.isoformat(),
        "active_cycle": None if active is None else active["pillar"],
        "before_qi_yun": active is None,
        "interactions": interactions,
    }


def incomplete(reason: str) -> dict[str, Any]:
    return {
        "rule_version": RULE_VERSION,
        "profile": PROFILE,
        "status": "not_applicable",
        "reason": reason,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "input_digest": None,
        "steps": None,
        "claim": PROFILE["claim"],
    }


def evaluate(chart: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    if chart.get("status") != "complete_under_stated_policy" or not chart.get("pillars"):
        return incomplete(chart.get("reason") or "四柱不完整，五步都不计算。")
    birth = datetime.fromisoformat(str(chart["input_utc8"]))
    rows = _pillar_rows(str(chart["pillars"])[4], str(chart["pillars"]))
    first = strength(rows)
    second = structure(rows, first)
    third = useful(rows, first, second)
    fourth = ten_god_step(rows, first, second, third)
    fifth = luck(rows, birth, params)
    payload_input = {
        "pillars": chart["pillars"],
        "input_utc8": chart["input_utc8"],
        "luck_mode": params.get("luck_mode") or "",
        "luck_sex": params.get("luck_sex") or "",
        "luck_direction": params.get("luck_direction") or "",
        "liunian_year": params.get("liunian_year"),
        "true_solar_time_applied": False,
        "hour_known": True,
    }
    digest = hashlib.sha256(json.dumps(payload_input, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "rule_version": RULE_VERSION,
        "profile": PROFILE,
        "status": "complete",
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "input_digest": digest,
        "input": payload_input,
        "limits": [
            chart.get("place_notice"),
            chart.get("zi_chu_notice"),
            "子初、真太阳时未实现。时刻未知时不会补一个时柱。",
        ],
        "steps": {"strength": first, "structure": second, "useful": third, "ten_gods": fourth, "luck": fifth},
        "order": ["旺衰", "格局", "喜忌", "十神配合", "大运流年"],
        "claim": PROFILE["claim"],
    }


def chain_text(reading: dict[str, Any] | None) -> str:
    """Text the with-chart arm may see. It quotes calculated fields and forbids overrides."""

    if not reading or reading.get("status") != "complete":
        return "规则链未完成。不要编造旺衰、格局、喜忌或大运。\n"
    steps = reading["steps"]
    established = (steps["structure"].get("established") or {}).get("name") or "无成格"
    luck_step = steps["luck"]
    cycles = "、".join(item["pillar"] for item in luck_step.get("cycles", [])[:4]) or "未排"
    return (
        f"规则版本：{reading['rule_version']}。以下是已算出的值，解释时不得改写。\n"
        f"旺衰：{steps['strength']['verdict_label']}。{steps['strength']['reason']}\n"
        f"格局：{established}。\n"
        f"喜：{'、'.join(steps['useful']['favorable']) or '无单一喜项'}。忌：{'、'.join(steps['useful']['unfavorable']) or '无单一忌项'}。\n"
        f"大运方向：{luck_step.get('direction_label') or '未排'}。前四运：{cycles}。\n"
    )
