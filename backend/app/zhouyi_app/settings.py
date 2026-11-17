# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Model configuration for the product process.

Priority, first match wins:
1. Values submitted to this running process (memory only; gone on restart).
2. ZHOUYI_LLM_API_KEY, ZHOUYI_LLM_BASE_URL, ZHOUYI_LLM_MODEL.
3. LLM_API_KEY only when the ZhouYiFish key is empty. LLM_BASE_URL and
   LLM_MODEL_NAME are MiroFish settings and are not reused here.
4. Default endpoint http://m4.cyanbukkit.cn:3000/v1 and the two named models.

A key is never written to sqlite, logs, or API responses.
"""

from __future__ import annotations

import os
import threading

DEFAULT_BASE_URL = "http://m4.cyanbukkit.cn:3000/v1"
DEFAULT_MODELS = ("mimo-v2.6-pro", "gpt-6-astra")
PLACEHOLDERS = {"", "your_api_key_here", "your_zep_api_key_here", "changeme"}
PRIORITY = [
    "单次请求里指定的模型名",
    "本进程运行时提交的端点、模型和密钥（只在内存，重启后消失）",
    "环境变量 ZHOUYI_LLM_API_KEY、ZHOUYI_LLM_BASE_URL、ZHOUYI_LLM_MODEL",
    "仅当专用密钥为空时，再读 LLM_API_KEY。不读取 LLM_BASE_URL 或 LLM_MODEL_NAME",
    "缺省端点 http://m4.cyanbukkit.cn:3000/v1，可选模型 mimo-v2.6-pro 与 gpt-6-astra",
]


def _clean(value: str | None) -> str:
    text = (value or "").strip()
    if text in PLACEHOLDERS:
        return ""
    return text


class RuntimeSettings:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._key = ""
        self._base_url = ""
        self._model = ""

    def clear(self) -> None:
        with self._lock:
            self._key = ""
            self._base_url = ""
            self._model = ""

    def update(self, *, api_key: str | None = None, clear_key: bool = False, base_url: str | None = None, model: str | None = None) -> None:
        with self._lock:
            if clear_key:
                self._key = ""
            elif api_key is not None and api_key != "":
                self._key = api_key.strip()
            if base_url is not None:
                self._base_url = base_url.strip().rstrip("/")
            if model is not None:
                self._model = model.strip()

    def effective_key(self) -> str:
        with self._lock:
            if self._key:
                return self._key
        return _clean(os.environ.get("ZHOUYI_LLM_API_KEY")) or _clean(os.environ.get("LLM_API_KEY"))

    def effective_base_url(self) -> str:
        with self._lock:
            if self._base_url:
                return self._base_url
        return _clean(os.environ.get("ZHOUYI_LLM_BASE_URL")) or DEFAULT_BASE_URL

    def effective_model(self, requested: str | None = None) -> str:
        if requested and requested.strip():
            return requested.strip()
        with self._lock:
            if self._model:
                return self._model
        return _clean(os.environ.get("ZHOUYI_LLM_MODEL")) or DEFAULT_MODELS[0]

    def key_source(self) -> str:
        with self._lock:
            if self._key:
                return "process_memory"
        if _clean(os.environ.get("ZHOUYI_LLM_API_KEY")):
            return "ZHOUYI_LLM_API_KEY"
        if _clean(os.environ.get("LLM_API_KEY")):
            return "LLM_API_KEY"
        return "absent"

    def public_view(self) -> dict[str, object]:
        key = self.effective_key()
        base = self.effective_base_url()
        return {
            "key_configured": bool(key),
            "key_mask": f"已配置（{len(key)} 字符）" if key else "未配置",
            "key_source": self.key_source() if key else "absent",
            "base_url": base,
            "model": self.effective_model(),
            "available_models": list(DEFAULT_MODELS),
            "plaintext_http": base.startswith("http://"),
            "plaintext_warning": "当前端点是 HTTP 明文。密钥和出生资料会经过网络，只在你信任这条链路时使用。",
            "priority": PRIORITY,
            "research_cli_sees_runtime_key": False,
            "zep_configured": bool(_clean(os.environ.get("ZEP_API_KEY"))),
            "zep_required_for_zhouyi": False,
            "hard_request_limit": 60,
        }


runtime = RuntimeSettings()


def redact(text: str, secret: str = "") -> str:
    cleaned = text or ""
    if secret:
        cleaned = cleaned.replace(secret, "[redacted]")
    lowered = cleaned.lower()
    for marker in ("authorization", "bearer ", "api_key", "apikey"):
        if marker in lowered:
            return "响应已省略，因为其中可能含有凭据字段名或内容。"
    if len(cleaned) > 240:
        cleaned = cleaned[:240] + "…"
    return cleaned
