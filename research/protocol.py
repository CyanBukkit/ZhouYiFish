# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Load the frozen protocol and reject silent edits."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PROTOCOL_PATH = ROOT / "protocol" / "protocol_v1.json"
PROTOCOL_SHA_PATH = ROOT / "protocol" / "protocol_v1.sha256"


def canonical_bytes(obj: Any) -> bytes:
    """UTF-8 JSON with sorted keys and no extra whitespace."""

    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_obj(obj: Any) -> str:
    return sha256_bytes(canonical_bytes(obj))


def load_protocol() -> tuple[dict[str, Any], str]:
    raw = PROTOCOL_PATH.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("protocol_v1.json 含有 UTF-8 BOM，已拒绝。")
    digest = sha256_bytes(raw)
    expected = PROTOCOL_SHA_PATH.read_text(encoding="utf-8").strip()
    if digest != expected:
        raise ValueError(
            "协议文件与 protocol_v1.sha256 不一致。"
            "结算前不能悄悄改规则；若确需新版本，应另建协议文件。"
        )
    data = json.loads(raw.decode("utf-8"))
    if data.get("protocol_id") != "zhouyi-fish-meihua-precip-v1":
        raise ValueError("协议标识与本版本代码不匹配。")
    return data, digest
