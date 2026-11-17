# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Structural trigram and hexagram labels.

Line patterns are the usual trigram figures, bottom to top, yin 0 and
yang 1. They are fixed here so that the worked example 泽火革初爻变泽山咸
is well-defined. The pre-heaven number is not the integer value of those bits.
"""

from __future__ import annotations

TRIGRAM_NUMBERS = {
    "乾": 1,
    "兑": 2,
    "离": 3,
    "震": 4,
    "巽": 5,
    "坎": 6,
    "艮": 7,
    "坤": 8,
}

TRIGRAM_BY_NUMBER = {number: name for name, number in TRIGRAM_NUMBERS.items()}

# Bottom to top.
TRIGRAM_LINES = {
    1: (1, 1, 1),
    2: (1, 1, 0),
    3: (1, 0, 1),
    4: (1, 0, 0),
    5: (0, 1, 1),
    6: (0, 1, 0),
    7: (0, 0, 1),
    8: (0, 0, 0),
}

LINES_TO_NUMBER = {lines: number for number, lines in TRIGRAM_LINES.items()}

NATURE = {
    1: "天",
    2: "泽",
    3: "火",
    4: "雷",
    5: "风",
    6: "水",
    7: "山",
    8: "地",
}

# (upper, lower) -> short name. Upper is the top trigram.
# Key is (upper, lower). The label's two nature characters follow that order:
# 天风姤 is upper 乾 and lower 巽, not 风天小畜.
HEXAGRAM_SHORT = {
    (1, 1): "乾",
    (1, 2): "履",
    (1, 3): "同人",
    (1, 4): "无妄",
    (1, 5): "姤",
    (1, 6): "讼",
    (1, 7): "遁",
    (1, 8): "否",
    (2, 1): "夬",
    (2, 2): "兑",
    (2, 3): "革",
    (2, 4): "随",
    (2, 5): "大过",
    (2, 6): "困",
    (2, 7): "咸",
    (2, 8): "萃",
    (3, 1): "大有",
    (3, 2): "睽",
    (3, 3): "离",
    (3, 4): "噬嗑",
    (3, 5): "鼎",
    (3, 6): "未济",
    (3, 7): "旅",
    (3, 8): "晋",
    (4, 1): "大壮",
    (4, 2): "归妹",
    (4, 3): "丰",
    (4, 4): "震",
    (4, 5): "恒",
    (4, 6): "解",
    (4, 7): "小过",
    (4, 8): "豫",
    (5, 1): "小畜",
    (5, 2): "中孚",
    (5, 3): "家人",
    (5, 4): "益",
    (5, 5): "巽",
    (5, 6): "涣",
    (5, 7): "渐",
    (5, 8): "观",
    (6, 1): "需",
    (6, 2): "节",
    (6, 3): "既济",
    (6, 4): "屯",
    (6, 5): "井",
    (6, 6): "坎",
    (6, 7): "蹇",
    (6, 8): "比",
    (7, 1): "大畜",
    (7, 2): "损",
    (7, 3): "贲",
    (7, 4): "颐",
    (7, 5): "蛊",
    (7, 6): "蒙",
    (7, 7): "艮",
    (7, 8): "剥",
    (8, 1): "泰",
    (8, 2): "临",
    (8, 3): "明夷",
    (8, 4): "复",
    (8, 5): "升",
    (8, 6): "师",
    (8, 7): "谦",
    (8, 8): "坤",
}


def line_bits_value(lines: tuple[int, ...] | list[int]) -> int:
    """Integer with the bottom line as the least significant bit."""

    return sum(int(bit) << index for index, bit in enumerate(lines))


def one_hot(number: int) -> list[int]:
    if number not in TRIGRAM_BY_NUMBER:
        raise ValueError(f"卦数超出 1–8：{number}")
    values = [0] * 8
    values[number - 1] = 1
    return values


def hexagram_label(upper: int, lower: int) -> str:
    short = HEXAGRAM_SHORT[(upper, lower)]
    return f"{NATURE[upper]}{NATURE[lower]}{short}"


def compose_lines(upper: int, lower: int) -> list[int]:
    lower_lines = TRIGRAM_LINES[lower]
    upper_lines = TRIGRAM_LINES[upper]
    return [*lower_lines, *upper_lines]


def split_lines(lines: list[int]) -> tuple[int, int]:
    if len(lines) != 6:
        raise ValueError("六爻必须自下而上共 6 位。")
    lower = LINES_TO_NUMBER[tuple(lines[:3])]
    upper = LINES_TO_NUMBER[tuple(lines[3:])]
    return upper, lower
