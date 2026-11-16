# Copyright (C) 2026 ZhouYiFish contributors
# SPDX-License-Identifier: AGPL-3.0-only

import re
from pathlib import Path

from research.experiment import OUTPUT_NAMES
from research.protocol import PROTOCOL_PATH, PROTOCOL_SHA_PATH, sha256_bytes

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "research"
SECRET = re.compile(
    r"sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{16}|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|LLM_API_KEY\s*=\s*\S+"
)


def test_protocol_hash_and_research_files_have_no_bom_or_secret():
    raw = PROTOCOL_PATH.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert sha256_bytes(raw) == PROTOCOL_SHA_PATH.read_text(encoding="utf-8").strip()
    for path in RESEARCH.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".md", ".json", ".txt", ".sh", ".sha256"}:
            continue
        blob = path.read_bytes()
        assert not blob.startswith(b"\xef\xbb\xbf"), path
        text = blob.decode("utf-8")
        assert SECRET.search(text) is None, path
        if path.suffix == ".py":
            assert re.search(r"(?m)^\s*(?:import backend|from backend|load_dotenv\()", text) is None
    assert "predictions.jsonl" in OUTPUT_NAMES


def test_committed_offline_run_matches_snapshot_when_present():
    summary = RESEARCH / "experiments" / "offline_v1" / "score_summary.json"
    if not summary.exists():
        return
    from research.cli import command_verify
    import argparse

    assert command_verify(argparse.Namespace()) == 0
