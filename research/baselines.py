# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Pilot-only base rate, lunar-month rate, and within-month symbol control."""

from __future__ import annotations

from research.protocol import load_protocol
from research.rngutil import HmacCounter, fisher_yates


def _rate(successes: int, count: int, smooth_extremes: bool) -> tuple[float, bool]:
    if count <= 0:
        raise ValueError("没有已结算样本，不能估计比率。")
    if smooth_extremes and (successes == 0 or successes == count):
        return (successes + 0.5) / (count + 1), True
    return successes / count, False


def fit_reference_rates(pilot_rows: list[dict]) -> dict[str, object]:
    """Fit on resolved pilot rows only. Holdout labels are not an argument."""

    protocol, _digest = load_protocol()
    minimum = 5
    resolved = [row for row in pilot_rows if row["outcome"] in (0, 1)]
    if not resolved:
        raise ValueError("先导期没有可结算事件，不能拟合基率。")
    successes = sum(int(row["outcome"]) for row in resolved)
    base, base_smoothed = _rate(successes, len(resolved), True)
    by_month: dict[int, list[int]] = {month: [] for month in range(1, 13)}
    for row in resolved:
        by_month[int(row["lunar_month_number"])].append(int(row["outcome"]))
    month_rates: dict[str, float] = {}
    fallbacks = []
    smoothed_months = []
    for month, outcomes in by_month.items():
        key = str(month)
        if len(outcomes) < minimum:
            month_rates[key] = base
            fallbacks.append(month)
            continue
        rate, smoothed = _rate(sum(outcomes), len(outcomes), True)
        month_rates[key] = rate
        if smoothed:
            smoothed_months.append(month)
    return {
        "protocol_id": protocol["protocol_id"],
        "pilot_resolved": len(resolved),
        "pilot_successes": successes,
        "base_rate": base,
        "base_rate_smoothed": base_smoothed,
        "month_rates": month_rates,
        "month_fallback_to_base": fallbacks,
        "month_smoothed": smoothed_months,
        "minimum_month_count": minimum,
        "labels_used": "pilot_resolved_only",
    }


def calendar_probability(rates: dict[str, object], lunar_month_number: int) -> float:
    return float(rates["month_rates"][str(lunar_month_number)])


def permute_within_lunar_month(month_numbers: list[int], values: list) -> list:
    """Permute values inside each lunar month with the frozen HMAC stream.

    The stream depends on the month sizes and the input order, not on labels.
    """

    if len(month_numbers) != len(values):
        raise ValueError("月份和数值必须等长。")
    protocol, _digest = load_protocol()
    rng = HmacCounter(
        protocol["random_control"]["seed_utf8"],
        protocol["random_control"]["symbol_domain"],
    )
    order = sorted(range(len(values)), key=lambda index: int(month_numbers[index]))
    assigned: list = [None] * len(values)
    month = None
    bucket: list[int] = []

    def flush() -> None:
        if not bucket:
            return
        shuffled = fisher_yates([values[index] for index in bucket], rng)
        for index, value in zip(bucket, shuffled):
            assigned[index] = value

    for index in order:
        current = int(month_numbers[index])
        if month is None:
            month = current
        if current != month:
            flush()
            bucket = []
            month = current
        bucket.append(index)
    flush()
    if any(value is None for value in assigned):
        raise RuntimeError("符号对照没有覆盖全部事件。")
    return assigned


def symbol_control_probabilities(rows: list[dict]) -> list[float]:
    """Permute rule probabilities inside each lunar month. Labels are ignored."""

    permuted = permute_within_lunar_month(
        [int(row["lunar_month_number"]) for row in rows],
        [float(row["p_rule"]) for row in rows],
    )
    return [float(value) for value in permuted]
