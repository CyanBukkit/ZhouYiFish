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


def test_interpret_does_not_call_zero_equivalence():
    assert interpret({"ci95_low": -0.01, "ci95_high": 0.01}, 0.02) == "ci_includes_zero_not_equivalence"
    assert interpret({"ci95_low": -0.05, "ci95_high": -0.03}, 0.02) == "lower_brier_entire_ci_beyond_margin"
    assert interpret({"ci95_low": -0.03, "ci95_high": -0.005}, 0.02) == "lower_brier_detectable_but_not_entirely_beyond_margin"
    assert interpret({"ci95_low": 0.03, "ci95_high": 0.04}, 0.02) == "higher_brier_entire_ci_beyond_margin"


def test_bootstrap_is_deterministic_and_zero_difference_is_not_a_discovery():
    differences = [0.0, 0.0, 0.0, 0.0]
    clusters = ["2023-W01", "2023-W01", "2023-W02", "2023-W02"]
    first = bootstrap_contrast(differences, clusters, replicates=30)
    second = bootstrap_contrast(differences, clusters, replicates=30)
    assert first == second
    assert first["p_unadjusted"] == 1
    assert first["n_events"] == 4
    assert first["n_clusters"] == 2


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
