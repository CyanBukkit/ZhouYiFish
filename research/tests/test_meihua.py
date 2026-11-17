# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only

from datetime import datetime, timezone

import pytest

from research.hexagrams import (
    HEXAGRAM_SHORT,
    LINES_TO_NUMBER,
    NATURE,
    TRIGRAM_LINES,
    hexagram_label,
    line_bits_value,
    one_hot,
)
from research.mapping import probability_from_lines
from research.meihua import CastError, cast_from_datetime, cast_from_numbers, positive_remainder
from research.placeholders import fengshui, later_heaven_numbers, qimen, yarrow_stalks
from research.protocol import load_protocol


def test_guanmei_worked_example_and_mutual_lines():
    cast = cast_from_numbers(5, 12, 17, 9)
    assert cast["S"] == 34
    assert cast["upper_remainder_raw"] == 2
    assert cast["upper_number"] == 2
    assert cast["S_plus_hour"] == 43
    assert cast["lower_number"] == 3
    assert cast["moving_remainder_raw"] == 1
    assert cast["moving_line"] == 1
    assert cast["lines_bottom_up"] == [1, 0, 1, 1, 1, 0]
    assert cast["changed_lines_bottom_up"] == [0, 0, 1, 1, 1, 0]
    assert cast["hexagram"] == "泽火革"
    assert cast["changed_hexagram"] == "泽山咸"
    lines = cast["lines_bottom_up"]
    assert LINES_TO_NUMBER[tuple(lines[1:4])] == 5
    assert LINES_TO_NUMBER[tuple(lines[2:5])] == 1
    protocol, _digest = load_protocol()
    quote = protocol["quotes_from_simplified_transcription"]["worked_example_quote"]
    assert "三十四" in quote and "四十三" in quote and "泽火革" in quote
    assert "不是原文引句" in protocol["mod6_exact"]["note"]


def test_peony_example_changes_the_fifth_line_to_ding():
    cast = cast_from_numbers(6, 3, 16, 4)
    assert (cast["S"], cast["S_plus_hour"]) == (25, 29)
    assert cast["upper_number"] == 1
    assert cast["lower_number"] == 5
    assert cast["moving_line"] == 5
    assert cast["hexagram"] == "天风姤"
    assert cast["changed_hexagram"] == "火风鼎"


def test_exact_division_policies():
    assert positive_remainder(8, 8, 8) == (0, 8)
    assert positive_remainder(16, 8, 8) == (0, 8)
    assert positive_remainder(6, 6, 6) == (0, 6)
    assert positive_remainder(12, 6, 6) == (0, 6)
    top = cast_from_numbers(1, 1, 4, 6)
    assert top["S_plus_hour"] == 12
    assert top["moving_line"] == 6
    assert top["mod6_zero_policy"].startswith("map_to_6_protocol_boundary")


def test_preheaven_number_is_not_the_bit_integer():
    assert line_bits_value(TRIGRAM_LINES[1]) == 7
    assert one_hot(1) == [1, 0, 0, 0, 0, 0, 0, 0]
    assert [line_bits_value(TRIGRAM_LINES[number]) for number in range(1, 9)] != list(range(1, 9))
    assert len(HEXAGRAM_SHORT) == 64
    assert len(set(HEXAGRAM_SHORT.values())) == 64
    for (upper, lower), short in HEXAGRAM_SHORT.items():
        assert hexagram_label(upper, lower) == f"{NATURE[upper]}{NATURE[lower]}{short}"
    assert hexagram_label(8, 1) == "地天泰"
    assert hexagram_label(1, 8) == "天地否"
    assert hexagram_label(5, 1) == "风天小畜"


def test_mapping_reads_only_original_lines():
    lines = [1, 0, 1, 1, 1, 0]
    assert probability_from_lines(lines) == 0.625
    assert probability_from_lines(lines) == probability_from_lines(list(lines))


def test_cast_rejects_labels_and_is_repeatable():
    with pytest.raises(CastError):
        cast_from_numbers(5, 12, 17, 9, outcome=1)
    moment = datetime(2024, 6, 15, 0, 0, tzinfo=timezone.utc)
    assert cast_from_datetime(moment) == cast_from_datetime(moment)
    with pytest.raises(CastError):
        cast_from_datetime(moment, outcome=0)


def test_unsupported_methods_do_not_emit_a_result():
    for function in (qimen, fengshui, yarrow_stalks, later_heaven_numbers):
        with pytest.raises(NotImplementedError, match="未实现|不在本协议"):
            function()
