# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Local cast service. It does not settle events or call a model."""

from __future__ import annotations

import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from research.experiment import dumps_json
from research.meihua import cast_from_datetime, cast_from_numbers
from research.protocol import load_protocol


class CastHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send({"status": "ok", "model_arms": "not_run"})
            return
        if self.path == "/protocol":
            protocol, digest = load_protocol()
            self._send(
                {
                    "protocol_id": protocol["protocol_id"],
                    "sha256": digest,
                    "llm_four_arm": "not_run",
                }
            )
            return
        self._send({"error": "未知路径"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        if length > 4096:
            self._send({"error": "请求过大"}, status=413)
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self._send({"error": "需要 JSON"}, status=400)
            return
        try:
            if self.path == "/cast":
                payload = cast_from_datetime(datetime.fromisoformat(body["utc"]))
            elif self.path == "/cast-numbers":
                payload = cast_from_numbers(
                    int(body["year_branch"]),
                    int(body["month"]),
                    int(body["day"]),
                    int(body["hour_branch"]),
                )
            else:
                self._send({"error": "未知路径"}, status=404)
                return
        except Exception as exc:  # user input, returned as a client error
            self._send({"error": str(exc)}, status=400)
            return
        self._send(payload)

    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, payload: dict, status: int = 200) -> None:
        blob = dumps_json(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)


def serve(port: int) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), CastHandler)
    print(f"起卦服务仅监听 127.0.0.1:{port}")
    server.serve_forever()
