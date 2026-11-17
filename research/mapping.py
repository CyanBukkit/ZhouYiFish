# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""P-MAP-1, an engineering hypothesis. It is not a probability from the classic."""

from __future__ import annotations

from research.hexagrams import one_hot


def probability_from_lines(lines: list[int]) -> float:
    if len(lines) != 6 or any(bit not in (0, 1) or isinstance(bit, bool) for bit in lines):
        raise ValueError("概率映射只接受 6 个 0/1 爻。")
    return (sum(lines) + 1) / 8


def structural_features(cast: dict) -> dict[str, object]:
    return {
        "lines_bottom_up": list(cast["lines_bottom_up"]),
        "upper_one_hot": one_hot(int(cast["upper_number"])),
        "lower_one_hot": one_hot(int(cast["lower_number"])),
        "moving_line": int(cast["moving_line"]),
        "changed_lines_bottom_up": list(cast["changed_lines_bottom_up"]),
        "changed_upper_one_hot": one_hot(int(cast["changed_upper_number"])),
        "changed_lower_one_hot": one_hot(int(cast["changed_lower_number"])),
    }
