# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only

from research.baselines import permute_within_lunar_month
from research.scoring import (
    aggregate_seed_probabilities,
    brier,
    bootstrap_contrast,
    holm,
    interpret,
    nearest_rank,
)


def test_brier_and_nearest_rank():
    assert brier(0.25, 1) == 0.5625
    assert brier(0.25, 0) == 0.0625
    assert nearest_rank(list(range(10000)), 0.025) == 249
    assert nearest_rank(list(range(10000)), 0.975) == 9749


def test_holm_stepdown():
    adjusted = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adjusted == {"a": 0.03, "c": 0.06, "b": 0.06}


def test_interpret_describes_interval_location_only():
    assert interpret({"ci95_low": -0.01, "ci95_high": 0.01}, 0.02) == "interval_includes_zero"
    assert interpret({"ci95_low": -0.05, "ci95_high": -0.03}, 0.02) == "interval_entirely_below_minus_margin"
    assert interpret({"ci95_low": -0.03, "ci95_high": -0.005}, 0.02) == "interval_below_zero"
    assert interpret({"ci95_low": 0.03, "ci95_high": 0.04}, 0.02) == "interval_entirely_above_margin"


def test_bootstrap_reports_extreme_counts_and_does_not_rewrite_zero_as_a_bound():
    from research.explain import _mc_sentence

    zeros = bootstrap_contrast([0.0, 0.0, 0.0, 0.0], ["2023-W01", "2023-W01", "2023-W02", "2023-W02"], replicates=30)
    assert zeros["extreme_count"] == 30
    assert zeros["mc_n"] == 30
    shifted = bootstrap_contrast([1.0, 1.0, 1.0, 1.0], ["2023-W01", "2023-W01", "2023-W02", "2023-W02"], replicates=20)
    assert shifted["extreme_count"] == 0
    assert shifted["mc_n"] == 20
    text = _mc_sentence(shifted)
    assert "0/20" in text
    assert "也不能写成 p<0.0001" in text
    assert "小于 0.0001" not in text
    assert "精确的零" not in text
    assert shifted["mc_proportion_wilson95"][1] > 0
    holm_note = {
        **shifted,
        "holm_mc_proportion": 0.0,
        "ci95_low": shifted["ci95_low"],
        "ci95_high": shifted["ci95_high"],
    }
    rendered = _mc_sentence(holm_note)
    assert "不调整百分位区间" in rendered
    assert "也不检验差是否超过 0.02" in rendered
    assert holm({"only": shifted["mc_proportion"]})["only"] == shifted["mc_proportion"]


def test_symbol_control_preserves_each_month_and_ignores_nothing_but_values():
    months = [1, 1, 1, 2, 2]
    values = [0.125, 0.25, 0.375, 0.5, 0.625]
    first = permute_within_lunar_month(months, values)
    second = permute_within_lunar_month(months, values)
    indexes = permute_within_lunar_month(months, [0, 1, 2, 3, 4])
    assert first == second
    assert sorted(first[:3]) == sorted(values[:3])
    assert sorted(first[3:]) == sorted(values[3:])
    assert [values[index] for index in indexes] == first
    assert set(first) != {0.5}


def test_agent_seeds_collapse_before_they_can_be_counted_as_events():
    rows = [aggregate_seed_probabilities([0.2, 0.4, 0.6, 0.8]) for _ in range(10)]
    assert len(rows) == 10
    assert rows[0] == 0.5
