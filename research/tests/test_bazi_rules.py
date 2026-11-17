# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from research.bazi import four_pillars
from research.bazi_rules import HIDDEN, RULE_VERSION, chain_text, direction_from_sex, evaluate, ten_god

STEMS = "甲乙丙丁戊己庚辛壬癸"
# Hand-written ten-god grid. Columns are the other stem in STEMS order.
GRID = {
    "甲": "比肩 劫财 食神 伤官 偏财 正财 七杀 正官 偏印 正印".split(),
    "乙": "劫财 比肩 伤官 食神 正财 偏财 正官 七杀 正印 偏印".split(),
    "丙": "偏印 正印 比肩 劫财 食神 伤官 偏财 正财 七杀 正官".split(),
    "丁": "正印 偏印 劫财 比肩 伤官 食神 正财 偏财 正官 七杀".split(),
    "戊": "七杀 正官 偏印 正印 比肩 劫财 食神 伤官 偏财 正财".split(),
    "己": "正官 七杀 正印 偏印 劫财 比肩 伤官 食神 正财 偏财".split(),
    "庚": "偏财 正财 七杀 正官 偏印 正印 比肩 劫财 食神 伤官".split(),
    "辛": "正财 偏财 正官 七杀 正印 偏印 劫财 比肩 伤官 食神".split(),
    "壬": "食神 伤官 偏财 正财 七杀 正官 偏印 正印 比肩 劫财".split(),
    "癸": "伤官 食神 正财 偏财 正官 七杀 正印 偏印 劫财 比肩".split(),
}
HIDDEN_EXPECTED = {
    "子": ("癸",),
    "丑": ("己", "癸", "辛"),
    "寅": ("甲", "丙", "戊"),
    "卯": ("乙",),
    "辰": ("戊", "乙", "癸"),
    "巳": ("丙", "庚", "戊"),
    "午": ("丁", "己"),
    "未": ("己", "丁", "乙"),
    "申": ("庚", "壬", "戊"),
    "酉": ("辛",),
    "戌": ("戊", "辛", "丁"),
    "亥": ("壬", "甲"),
}
SH = ZoneInfo("Asia/Shanghai")


def reading_for(moment: datetime, **params):
    chart = four_pillars(moment, hour_known=True)
    return evaluate(chart, params)


def test_ten_god_grid_and_hidden_stems():
    for day, expected in GRID.items():
        for other, name in zip(STEMS, expected):
            assert ten_god(day, other) == name
    for branch, stems in HIDDEN_EXPECTED.items():
        assert tuple(stem for stem, _qi in HIDDEN[branch]) == stems


def test_three_fictional_charts_diverge_without_a_score():
    mixed = reading_for(datetime(2001, 6, 15, 10, 30, tzinfo=SH), luck_mode="manual", luck_direction="forward")
    strong = reading_for(datetime(1983, 2, 5, 0, 0, tzinfo=SH), luck_mode="traditional", luck_sex="male")
    weak = reading_for(datetime(1981, 8, 24, 11, 0, tzinfo=SH), luck_mode="manual", luck_direction="backward")
    assert mixed["steps"]["strength"]["verdict"] == "uncertain"
    assert mixed["steps"]["strength"]["de_ling"] is False
    assert mixed["steps"]["strength"]["seasonal_phase"] == "相"
    assert any(item["stem"] == "己" and item["qi"] == "中气" for item in mixed["steps"]["strength"]["roots"])
    assert mixed["steps"]["structure"]["established"]["name"] == "建禄"
    assert any(item["name"] == "从格" for item in mixed["steps"]["structure"]["unsupported"])
    assert mixed["steps"]["useful"]["favorable"] == []
    assert mixed["steps"]["strength"]["engineering_index"] is None
    assert mixed["steps"]["structure"]["not_derived_from_strength_verdict"] is True
    he = next(item for item in mixed["steps"]["ten_gods"]["combinations"] if item["kind"] == "天干五合")
    assert he["transform"] == "不化"
    assert strong["input"]["pillars"] == "癸亥甲寅甲子甲子"
    assert strong["steps"]["strength"]["verdict"] == "strong_candidate"
    assert strong["steps"]["structure"]["established"]["name"] == "建禄"
    assert strong["steps"]["useful"]["favorable"] == ["正官", "七杀", "食神", "伤官", "正财", "偏财"]
    assert strong["steps"]["luck"]["direction"] == "backward"
    assert weak["input"]["pillars"] == "辛酉丙申甲戌庚午"
    assert weak["steps"]["strength"]["verdict"] == "weak_candidate"
    assert weak["steps"]["structure"]["established"]["name"] == "七杀格"
    assert "月令本气庚为七杀" in weak["steps"]["structure"]["established"]["reason"]
    assert weak["steps"]["useful"]["unfavorable"][0] == "正官"
    assert {item["verdict"] for item in (mixed["steps"]["strength"], strong["steps"]["strength"], weak["steps"]["strength"])} == {
        "uncertain",
        "strong_candidate",
        "weak_candidate",
    }


def _hand_qi_yun(birth: datetime, target: datetime, forward: bool):
    delta = target - birth if forward else birth - target
    seconds = int(round(delta.total_seconds()))
    whole_days, rem_seconds = divmod(seconds, 86400)
    years, day_rem = divmod(whole_days, 3)
    months = day_rem * 4
    extra_days = int((rem_seconds / 7200) * 10)
    months += extra_days // 30
    days = extra_days % 30
    return {"years": years, "months": months, "days": days}


def test_luck_direction_and_solar_term_edges():
    birth = datetime(2001, 6, 15, 10, 30, tzinfo=SH)
    forward = reading_for(birth, luck_mode="manual", luck_direction="forward")
    backward = reading_for(birth, luck_mode="manual", luck_direction="backward")
    assert forward["steps"]["luck"]["target_jie"]["name"] == "小暑"
    assert forward["steps"]["luck"]["target_jie"]["at"] == "2001-07-07T09:06:42+08:00"
    assert backward["steps"]["luck"]["target_jie"]["name"] == "芒种"
    assert backward["steps"]["luck"]["target_jie"]["at"] == "2001-06-05T22:53:35+08:00"
    assert forward["steps"]["luck"]["qi_yun"] == _hand_qi_yun(birth, datetime(2001, 7, 7, 9, 6, 42, tzinfo=SH), True)
    assert backward["steps"]["luck"]["qi_yun"] == _hand_qi_yun(birth, datetime(2001, 6, 5, 22, 53, 35, tzinfo=SH), False)
    assert forward["steps"]["luck"]["cycles"][0]["pillar"] == "乙未"
    assert backward["steps"]["luck"]["cycles"][0]["pillar"] == "癸巳"
    assert forward["input_digest"] != backward["input_digest"]
    missing = reading_for(birth)
    assert missing["steps"]["luck"]["status"] == "incomplete"
    assert missing["steps"]["luck"]["cycles"] == []
    assert direction_from_sex("辛", "male") == "backward"
    assert direction_from_sex("辛", "female") == "forward"
    assert direction_from_sex("甲", "male") == "forward"


def test_lichun_cross_year_and_timezone_use_utc8():
    before = reading_for(datetime(2001, 2, 4, 2, 0, tzinfo=SH), luck_mode="manual", luck_direction="forward")
    after = reading_for(datetime(2001, 2, 4, 3, 0, tzinfo=SH), luck_mode="manual", luck_direction="forward")
    assert before["steps"]["luck"]["target_jie"]["name"] == "立春"
    assert after["steps"]["luck"]["target_jie"]["name"] == "惊蛰"
    assert before["input"]["pillars"][0:2] != after["input"]["pillars"][0:2]
    new_year = reading_for(datetime(2001, 12, 20, 12, 0, tzinfo=SH), luck_mode="manual", luck_direction="forward")
    assert new_year["steps"]["luck"]["target_jie"]["at"].startswith("2002-01-05")
    old_year = reading_for(datetime(2001, 1, 4, 12, 0, tzinfo=SH), luck_mode="manual", luck_direction="backward")
    assert old_year["steps"]["luck"]["target_jie"]["at"].startswith("2000-12-07")
    foreign = datetime(2001, 6, 15, 2, 30, tzinfo=ZoneInfo("America/New_York"))
    moved = reading_for(foreign, luck_mode="manual", luck_direction="forward", liunian_year=2010)
    assert moved["input"]["input_utc8"].startswith("2001-06-15T14:30:00")
    assert moved["steps"]["luck"]["target_jie"]["name"] == "小暑"
    assert moved["steps"]["luck"]["liunian"]["year_boundary"] == "立春"
    assert moved["steps"]["luck"]["liunian"]["pillar"][0] in STEMS
    assert "不因见合就判化" in chain_text(moved) or moved["steps"]["luck"]["liunian"]["interactions"] is not None


def test_missing_hour_does_not_invent_steps():
    result = evaluate({"status": "not_applicable", "reason": "没有钟点", "pillars": None}, {})
    assert result["status"] == "not_applicable"
    assert result["steps"] is None
    assert result["rule_version"] == RULE_VERSION
    text = chain_text(result)
    assert "不要编造" in text
