import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ingest-normalize"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
SCRIPT_DIR = SKILL_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ingest_normalize.models import IngestFailureRecord
from ingest_normalize.reporting import build_ingest_report, determine_workflow_status


class FailureLedgerTests(unittest.TestCase):
    def test_ingest_report_is_projected_from_failure_ledger(self):
        failures = [
            IngestFailureRecord(
                failure_id="f1",
                run_id="run-1",
                step_name="fetch_source_items",
                scope_type="SOURCE",
                scope_id="rss-1",
                failure_type="NETWORK_ERROR",
                message="timeout",
                details={"timeout": 10},
                retryable=True,
                recorded_at="2026-03-27T12:00:00+00:00",
            )
        ]
        manifest = {
            "run_id": "run-1",
            "workflow_name": "ingest-normalize",
            "workflow_status": "PARTIAL_SUCCESS",
            "artifact_paths": {},
            "step_results": [],
            "started_at": "2026-03-27T12:00:00+00:00",
            "finished_at": "2026-03-27T12:00:01+00:00",
        }

        report = build_ingest_report(
            manifest=manifest,
            failures=failures,
            metrics={"source_discovery_count": 1},
            generated_at="2026-03-27T12:00:01+00:00",
        )

        self.assertEqual("PARTIAL_SUCCESS", report.workflow_status)
        self.assertEqual(1, report.failure_summary["total_failures"])
        self.assertEqual(1, report.failure_summary["by_type"]["NETWORK_ERROR"])

    def test_workflow_status_uses_failures_for_partial_success(self):
        status = determine_workflow_status(
            step_results=[
                {"step_name": "discover_sources", "status": "SUCCESS_WITH_OUTPUT"},
                {"step_name": "normalize_candidates", "status": "SUCCESS_EMPTY"},
            ],
            failures=[
                IngestFailureRecord(
                    failure_id="f1",
                    run_id="run-1",
                    step_name="fetch_source_items",
                    scope_type="SOURCE",
                    scope_id="rss-1",
                    failure_type="NETWORK_ERROR",
                    message="timeout",
                    details={},
                    retryable=True,
                    recorded_at="2026-03-27T12:00:00+00:00",
                )
            ],
        )

        self.assertEqual("PARTIAL_SUCCESS", status)


if __name__ == "__main__":
    unittest.main()
