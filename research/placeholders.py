# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Methods that are named only so they cannot be mistaken for implementations."""


class UnsupportedMethodError(NotImplementedError):
    """Raised when a caller asks for a method this version does not compute."""


def qimen(*_args: object, **_kwargs: object) -> None:
    raise UnsupportedMethodError("奇门遁甲未实现严格算法。此入口不产生盘、卦或概率。")


def fengshui(*_args: object, **_kwargs: object) -> None:
    raise UnsupportedMethodError("风水未实现严格算法。此入口不产生判断或概率。")


def yarrow_stalks(*_args: object, **_kwargs: object) -> None:
    raise UnsupportedMethodError("揲蓍不在本协议内。年月日时起卦不能改走蓍草。")


def later_heaven_numbers(*_args: object, **_kwargs: object) -> None:
    raise UnsupportedMethodError("后天卦数不在本协议内。")
