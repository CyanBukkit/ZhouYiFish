# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only
"""Command line for casts, the offline trial, and the blocked model arms."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from research.data_openmeteo import fetch_snapshot, parse_snapshot
from research.experiment import (
    dumps_json,
    dumps_jsonl,
    run_experiment,
    snapshot_digest,
    utc_now,
)
from research.llm_adapter import llm_run_status
from research.meihua import cast_from_datetime, cast_from_numbers
from research.protocol import load_protocol

OUTPUT_DIR = Path(__file__).resolve().parent / "experiments" / "offline_v1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="周易研究模块：可审计起卦、离线评分，以及未运行的模型四臂。"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    cast = sub.add_parser("cast", help="按带时区的时间起卦")
    cast.add_argument("--utc", required=True, help="例如 2024-02-09T16:00:00+00:00")
    cast.set_defaults(func=command_cast)

    numbers = sub.add_parser("cast-numbers", help="按年支、月、日、时支起卦")
    numbers.add_argument("--year-branch", type=int, required=True)
    numbers.add_argument("--month", type=int, required=True)
    numbers.add_argument("--day", type=int, required=True)
    numbers.add_argument("--hour-branch", type=int, required=True)
    numbers.set_defaults(func=command_numbers)

    protocol = sub.add_parser("protocol", help="打印协议标识和哈希")
    protocol.set_defaults(func=command_protocol)

    offline = sub.add_parser("run-offline", help="解析快照并写出离线实验；不调用模型")
    offline.add_argument("--refresh-snapshot", action="store_true")
    offline.set_defaults(func=command_run_offline)

    verify = sub.add_parser("verify-offline", help="用已冻结快照重算并核对产出")
    verify.set_defaults(func=command_verify)

    blocked = sub.add_parser("run-llm", help="查看模型四臂为何未运行")
    blocked.add_argument("--config", default=None)
    blocked.set_defaults(func=command_llm)

    serve = sub.add_parser("serve", help="本机只读起卦服务")
    serve.add_argument("--port", type=int, default=8765)
    serve.set_defaults(func=command_serve)

    persona = sub.add_parser("persona-demo", help="写出虚构人物沙盒，不验证真实命中")
    persona.set_defaults(func=command_persona)
    experiment = sub.add_parser("persona-experiment", help="运行离线人物沙盒检查，不调用模型")
    experiment.set_defaults(func=command_persona_experiment)
    diagnose = sub.add_parser("llm-diagnose", help="检查是否有明确提供的模型变量，不打印密钥")
    diagnose.set_defaults(func=command_llm_diagnose)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


def command_cast(args: argparse.Namespace) -> int:
    moment = datetime.fromisoformat(args.utc)
    _print(cast_from_datetime(moment))
    return 0


def command_numbers(args: argparse.Namespace) -> int:
    _print(
        cast_from_numbers(args.year_branch, args.month, args.day, args.hour_branch)
    )
    return 0


def command_protocol(_args: argparse.Namespace) -> int:
    protocol, digest = load_protocol()
    _print({"protocol_id": protocol["protocol_id"], "sha256": digest})
    return 0


def command_llm(args: argparse.Namespace) -> int:
    status = llm_run_status(args.config)
    _print(status)
    print(status["blocker"], file=sys.stderr)
    return 2


def command_persona_experiment(_args: argparse.Namespace) -> int:
    from research.persona_experiment import write_persona_experiment

    path = write_persona_experiment()
    print(path, file=sys.stderr)
    return 0


def command_llm_diagnose(_args: argparse.Namespace) -> int:
    from research.llm_adapter import llm_diagnose

    status = llm_diagnose()
    _print(status)
    return 0 if status["credential_present"] else 2


def command_persona(_args: argparse.Namespace) -> int:
    from research.sandbox_demo import write_demo

    path = write_demo()
    print(path, file=sys.stderr)
    return 0


def command_serve(args: argparse.Namespace) -> int:
    from research.server import serve

    serve(args.port)
    return 0


def command_run_offline(args: argparse.Namespace) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = OUTPUT_DIR / "score_summary.json"
    if summary_path.exists() and not args.refresh_snapshot:
        print("离线结果已存在。复现请用 verify-offline，而不是覆盖。", file=sys.stderr)
        return 1
    if summary_path.exists() and args.refresh_snapshot:
        print("已有评分结果。刷新快照会变成另一次实验，本命令拒绝覆盖。", file=sys.stderr)
        return 1
    snapshot_path = OUTPUT_DIR / "openmeteo_snapshot.json"
    if snapshot_path.exists() and not args.refresh_snapshot:
        snapshot_bytes = snapshot_path.read_bytes()
    else:
        snapshot = fetch_snapshot()
        snapshot_bytes = dumps_json(snapshot).encode("utf-8")
        snapshot_path.write_bytes(snapshot_bytes)
    started = time.perf_counter()
    result = _result_from_snapshot(snapshot_bytes)
    _write_outputs(result)
    log = {
        "computed_at": utc_now(),
        "wall_clock_seconds": time.perf_counter() - started,
        "python": sys.version,
        "platform": platform.platform(),
        "git_rev": _git_rev(),
        "protocol_sha256": result["summary"]["protocol_sha256"],
        "snapshot_sha256": result["summary"]["snapshot_sha256"],
        "sample_class": result["summary"]["sample_class"],
        "llm_four_arm": "not_run",
    }
    (OUTPUT_DIR / "run_log.json").write_text(dumps_json(log), encoding="utf-8")
    print(f"写出 {OUTPUT_DIR}", file=sys.stderr)
    return 0


def command_verify(_args: argparse.Namespace) -> int:
    snapshot_path = OUTPUT_DIR / "openmeteo_snapshot.json"
    snapshot_bytes = snapshot_path.read_bytes()
    result = _result_from_snapshot(snapshot_bytes)
    expected = {
        "predictions.jsonl": dumps_jsonl(result["events"]),
        "score_summary.json": dumps_json(result["summary"]),
        "实验说明.md": result["explanation"],
    }
    from research.prospective import old_queue_disposition

    ledger_bytes = (OUTPUT_DIR / "future_ledger.jsonl").read_bytes()
    disposition = old_queue_disposition()
    mismatches = []
    if disposition["source_sha256"] != hashlib.sha256(ledger_bytes).hexdigest():
        mismatches.append("future_ledger.jsonl")
    stored = json.loads((OUTPUT_DIR / "future_ledger_disposition.json").read_text(encoding="utf-8"))
    if stored != disposition:
        mismatches.append("future_ledger_disposition.json")
    for name, text in expected.items():
        path = OUTPUT_DIR / name
        actual = path.read_text(encoding="utf-8")
        if actual != text:
            mismatches.append(name)
    log = json.loads((OUTPUT_DIR / "run_log.json").read_text(encoding="utf-8"))
    digest = snapshot_digest(snapshot_bytes)
    if log.get("snapshot_sha256") != digest or log.get("llm_four_arm") != "not_run":
        mismatches.append("run_log.json")
    if mismatches:
        print("核对失败：" + ", ".join(mismatches), file=sys.stderr)
        return 1
    print("离线实验与快照一致。", file=sys.stderr)
    return 0


def _result_from_snapshot(snapshot_bytes: bytes) -> dict:
    snapshot = json.loads(snapshot_bytes.decode("utf-8"))
    daily = parse_snapshot(snapshot)
    return run_experiment(
        daily,
        sample_class="historical_open_meteo_retrospective",
        snapshot_sha256=snapshot_digest(snapshot_bytes),
    )


def _write_outputs(result: dict) -> None:
    files = {
        "predictions.jsonl": dumps_jsonl(result["events"]),
        "score_summary.json": dumps_json(result["summary"]),
        "future_ledger.jsonl": dumps_jsonl(result["future_ledger"]),
        "实验说明.md": result["explanation"],
    }
    for name, text in files.items():
        blob = text.encode("utf-8")
        if blob.startswith(b"\xef\xbb\xbf"):
            raise RuntimeError(f"{name} 被写成了 BOM。")
        (OUTPUT_DIR / name).write_bytes(blob)


def _git_rev() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _print(payload: dict) -> None:
    sys.stdout.write(dumps_json(payload))


if __name__ == "__main__":
    raise SystemExit(main())
