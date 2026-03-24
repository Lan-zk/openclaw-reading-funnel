from __future__ import annotations

import json
from pathlib import Path

import httpx

from tests.conftest import REPO_ROOT, load_module

module = load_module("skills/source-fetch/run.py", "source_fetch")


def test_source_fetch_writes_raw_items_and_manifest(tmp_path: Path) -> None:
    fixture_text = (REPO_ROOT / "tests/fixtures/freshrss/stream_contents.json").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/accounts/ClientLogin"):
            return httpx.Response(200, text="SID=dummy\nAuth=test-token\n")
        if request.url.path.endswith("/reader/api/0/stream/contents/reading-list"):
            return httpx.Response(200, text=fixture_text, headers={"Content-Type": "application/json"})
        return httpx.Response(404)

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({
            "base_url": "https://rss.example.com/api/greader.php",
            "feed_ids": [],
            "limit_per_run": 10,
            "request_timeout_seconds": 10
        }),
        encoding="utf-8"
    )
    result = module.run_fetch(
        config_path=config_path,
        run_id="run-1",
        window_start=module.parse_iso8601("2024-03-23T00:00:00Z"),
        window_end=module.parse_iso8601("2024-03-25T00:00:00Z"),
        output_dir=tmp_path / "out",
        username="demo",
        password="demo",
        transport=httpx.MockTransport(handler)
    )

    assert result["raw_items"]["item_count"] == 3
    assert result["step_manifest"]["step_status"] == "SUCCEEDED"
    assert result["step_manifest"]["continue_recommended"] is True


def test_source_fetch_marks_failed_when_request_fails(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({
            "base_url": "https://rss.example.com/api/greader.php",
            "feed_ids": [],
            "limit_per_run": 10,
            "request_timeout_seconds": 10
        }),
        encoding="utf-8"
    )
    result = module.run_fetch(
        config_path=config_path,
        run_id="run-2",
        window_start=module.parse_iso8601("2024-03-23T00:00:00Z"),
        window_end=module.parse_iso8601("2024-03-25T00:00:00Z"),
        output_dir=tmp_path / "out",
        username="demo",
        password="demo",
        transport=httpx.MockTransport(handler)
    )

    assert result["raw_items"]["item_count"] == 0
    assert result["step_manifest"]["step_status"] == "FAILED"
    assert result["step_manifest"]["continue_recommended"] is False
