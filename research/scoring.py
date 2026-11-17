# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Brier score, recentered cluster bootstrap, and a narrow Holm helper.

The sample size is the number of events. Seeds and agents are aggregated
before anything in this module is called. Week-cluster intervals from one
year are exploratory descriptions: weeks are not independent.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Iterable

from research.protocol import load_protocol
from research.rngutil import HmacCounter


def brier(probability: float, outcome: int) -> float:
    if not 0.0 <= float(probability) <= 1.0:
        raise ValueError("概率必须在 0 到 1。")
    if outcome not in (0, 1):
        raise ValueError("结局必须是 0 或 1。未结算的行不能送进 Brier。")
    error = float(probability) - float(outcome)
    return error * error


def mean(values: Iterable[float]) -> float:
    pool = list(values)
    if not pool:
        raise ValueError("空样本没有均值。")
    return sum(pool) / len(pool)


def nearest_rank(sorted_values: list[float], probability: float) -> float:
    """Nearest-rank percentile. Index is ceil(p * n), clamped to the sample."""

    count = len(sorted_values)
    if count == 0:
        raise ValueError("空样本没有分位数。")
    if not 0 < probability <= 1:
        raise ValueError("分位必须在 (0, 1]。")
    rank = max(1, math.ceil(probability * count))
    return sorted_values[min(rank, count) - 1]


def wilson_interval(count: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """95% Wilson interval for a Monte Carlo proportion. Not a Brier interval."""

    if trials <= 0 or count < 0 or count > trials:
        raise ValueError("蒙特卡洛计数无效。")
    proportion = count / trials
    denom = 1.0 + z * z / trials
    center = (proportion + z * z / (2.0 * trials)) / denom
    half = z * math.sqrt(proportion * (1.0 - proportion) / trials + z * z / (4.0 * trials * trials)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def holm(proportions: dict[str, float]) -> dict[str, float]:
    """Holm step-down on a family of zero-difference Monte Carlo proportions.

    This does not adjust percentile intervals and does not test a margin.
    """

    ordered = sorted(proportions.items(), key=lambda item: (item[1], item[0]))
    family = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for index, (name, raw) in enumerate(ordered):
        step = min(1.0, (family - index) * raw)
        running = max(running, step)
        adjusted[name] = running
    return adjusted


def cluster_id(civil_date: str) -> str:
    iso = date.fromisoformat(civil_date).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def cluster_bootstrap_means(
    values_by_cluster: dict[str, list[float]],
    replicates: int,
    rng: HmacCounter,
) -> list[float]:
    keys = sorted(values_by_cluster)
    if not keys:
        raise ValueError("没有聚类可抽样。")
    stats = [(sum(values_by_cluster[key]), len(values_by_cluster[key])) for key in keys]
    if any(count == 0 for _total, count in stats):
        raise ValueError("聚类不能为空。")
    width = len(stats)
    means: list[float] = []
    for _ in range(replicates):
        total = 0.0
        count = 0
        for _draw in range(width):
            cluster_sum, cluster_count = stats[rng.below(width)]
            total += cluster_sum
            count += cluster_count
        means.append(total / count)
    return means


def bootstrap_contrast(
    paired_differences: list[float],
    clusters: list[str],
    *,
    replicates: int | None = None,
) -> dict[str, float | bool | str]:
    if len(paired_differences) != len(clusters) or not paired_differences:
        raise ValueError("配对差和聚类标识必须非空且等长。")
    protocol, _digest = load_protocol()
    stats = protocol["statistics"]
    if replicates is None:
        replicates = int(stats["bootstrap_replicates"])
    grouped: dict[str, list[float]] = {}
    for difference, cluster in zip(paired_differences, clusters):
        grouped.setdefault(cluster, []).append(difference)
    observed = sum(paired_differences) / len(paired_differences)
    rng = HmacCounter(
        protocol["random_control"]["seed_utf8"],
        protocol["random_control"]["bootstrap_domain"],
    )
    samples = cluster_bootstrap_means(grouped, replicates, rng)
    ordered = sorted(samples)
    low = nearest_rank(ordered, 0.025)
    high = nearest_rank(ordered, 0.975)
    extreme_count = sum(1 for sample in samples if abs(sample - observed) >= abs(observed))
    mc_n = len(samples)
    wilson_low, wilson_high = wilson_interval(extreme_count, mc_n)
    return {
        "estimate": observed,
        "ci95_low": low,
        "ci95_high": high,
        "ci_width": high - low,
        "covers_zero": low <= 0.0 <= high,
        "interval_role": "exploratory_percentile_interval",
        "bootstrap_null": "recentered_cluster_bootstrap",
        "null_statement": (
            "H0 is a zero event-weighted mean paired Brier difference. "
            "A replicate is extreme when |bootstrap mean - observed| >= |observed|. "
            "extreme_count/mc_n is a Monte Carlo proportion, not an exact p-value."
        ),
        "extreme_count": extreme_count,
        "mc_n": mc_n,
        "mc_proportion": extreme_count / mc_n,
        "mc_proportion_wilson95": [wilson_low, wilson_high],
        "n_events": len(paired_differences),
        "n_clusters": len(grouped),
        "bootstrap_replicates": replicates,
    }


def interpret(contrast: dict[str, float | bool | str], margin: float) -> str:
    low = float(contrast["ci95_low"])
    high = float(contrast["ci95_high"])
    if low <= 0.0 <= high:
        return "interval_includes_zero"
    if high <= -margin:
        return "interval_entirely_below_minus_margin"
    if high < 0.0:
        return "interval_below_zero"
    if low >= margin:
        return "interval_entirely_above_margin"
    if low > 0.0:
        return "interval_above_zero"
    return "unclassified"


def reliability_table(
    probabilities: list[float], outcomes: list[int], bins: int = 10
) -> dict[str, object]:
    if len(probabilities) != len(outcomes) or not probabilities:
        raise ValueError("校准表需要等长且非空的概率和结局。")
    rows = []
    ece = 0.0
    total = len(probabilities)
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        chosen = []
        for probability, outcome in zip(probabilities, outcomes):
            in_bin = probability >= low and (
                probability < high or (index == bins - 1 and probability <= high)
            )
            if in_bin:
                chosen.append((probability, outcome))
        if not chosen:
            rows.append(
                {
                    "bin_low": low,
                    "bin_high": high,
                    "n": 0,
                    "mean_p": None,
                    "outcome_rate": None,
                }
            )
            continue
        mean_p = sum(item[0] for item in chosen) / len(chosen)
        rate = sum(item[1] for item in chosen) / len(chosen)
        ece += (len(chosen) / total) * abs(rate - mean_p)
        rows.append(
            {
                "bin_low": low,
                "bin_high": high,
                "n": len(chosen),
                "mean_p": mean_p,
                "outcome_rate": rate,
            }
        )
    return {
        "bins": rows,
        "ece": ece,
        "calibration_in_the_large": mean(probabilities) - mean(outcomes),
        "frequentist_coverage_of_bootstrap_ci": "not_estimable_from_one_sample",
    }


def aggregate_seed_probabilities(seed_probabilities: list[float]) -> float:
    """Collapse every seed of one event to one probability before scoring."""

    if not seed_probabilities:
        raise ValueError("没有可聚合的种子概率。")
    return sum(float(value) for value in seed_probabilities) / len(seed_probabilities)
