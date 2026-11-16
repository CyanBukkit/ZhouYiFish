# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""HMAC-SHA256 counter stream and Fisher-Yates. Big-endian, rejection sampling."""

from __future__ import annotations

import hashlib
import hmac
from typing import TypeVar

T = TypeVar("T")


class HmacCounter:
    def __init__(self, seed: str, domain: str) -> None:
        self._key = seed.encode("utf-8")
        self._domain = domain.encode("utf-8")
        self._counter = 0

    def next_u64(self) -> int:
        message = self._domain + self._counter.to_bytes(8, "big")
        digest = hmac.new(self._key, message, hashlib.sha256).digest()
        self._counter += 1
        return int.from_bytes(digest[:8], "big")

    def below(self, limit: int) -> int:
        if limit < 1:
            raise ValueError("抽样上界必须是正整数。")
        if limit == 1:
            return 0
        span = 1 << 64
        cutoff = span - (span % limit)
        while True:
            draw = self.next_u64()
            if draw < cutoff:
                return draw % limit


def fisher_yates(items: list[T], rng: HmacCounter) -> list[T]:
    out = list(items)
    for index in range(len(out) - 1, 0, -1):
        swap = rng.below(index + 1)
        out[index], out[swap] = out[swap], out[index]
    return out
