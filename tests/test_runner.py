from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tests.conftest import REPO_ROOT


class FreshRSSHandler(BaseHTTPRequestHandler):
    fixture_text = (REPO_ROOT / "tests/fixtures/freshrss/stream_contents.json").read_text(encoding="utf-8")

    def do_POST(self) -> None:  # noqa: N802
        if self.path.endswith("/accounts/ClientLogin"):
            body = "SID=dummy\nAuth=test-token\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/greader.php/reader/api/0/stream/contents/reading-list"):
            body = self.fixture_text
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


def test_runner_executes_full_chain(tmp_path: Path) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), FreshRSSHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "base_url": f"http://127.0.0.1:{server.server_port}/api/greader.php",
                    "feed_ids": [],
                    "limit_per_run": 10,
                    "request_timeout_seconds": 10
                }
            ),
            encoding="utf-8"
        )
        env = os.environ.copy()
        env["FRESHRSS_USERNAME"] = "demo"
        env["FRESHRSS_API_PASSWORD"] = "demo"
        env["PYTHON_BIN"] = sys.executable
        subprocess.run(
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(REPO_ROOT / "scripts/run_phase1_local.ps1"),
                "-Config",
                str(config_path),
                "-WindowStart",
                "2024-03-23T00:00:00Z",
                "-WindowEnd",
                "2024-03-25T00:00:00Z",
                "-RunId",
                "runner-test",
                "-BaseDir",
                str(tmp_path / "runs")
            ],
            cwd=REPO_ROOT,
            env=env,
            check=True
        )
        run_manifest = json.loads((tmp_path / "runs" / "runner-test" / "run-review" / "run-manifest.json").read_text(encoding="utf-8"))
        assert run_manifest["run_status"] in {"SUCCEEDED", "PARTIAL_SUCCESS"}
        assert any(item["artifact_name"] == "reading-candidates" for item in run_manifest["artifact_index"])
    finally:
        server.shutdown()
        server.server_close()
