import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "skills" / "ingest-normalize"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
SCRIPT_DIR = SKILL_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ingest_normalize.models import SourceEntry
from tests.ingest_normalize.support import load_ingest_run_module


run = load_ingest_run_module("ingest_run_normalize_candidates_tests")


class NormalizeCandidatesTests(unittest.TestCase):
    def test_stable_normalized_candidate_id(self):
        entry = SourceEntry(
            source_entry_id="se_demo",
            source_entry_snapshot_id="snapshot_demo",
            source_adapter_type="RSS",
            source_id="rss-1",
            source_name="RSS One",
            origin_item_id="item-1",
            title="  Hello   World  ",
            url="HTTPS://Example.com:443/path?a=1&utm_source=x#frag",
            summary="summary",
            author="alice",
            published_at="2026-03-27T12:00:00+00:00",
            fetched_at="2026-03-27T13:00:00+00:00",
            raw_payload={"id": "item-1"},
            run_id="run-1",
            status="INGESTED",
        )

        candidates, failures = run.normalize_candidates([entry], run_id="run-1")

        self.assertEqual(1, len(candidates))
        self.assertEqual([], failures)
        self.assertEqual("se_demo", candidates[0].source_entry_id)
        self.assertEqual("Hello World", candidates[0].normalized_title)
        self.assertEqual("https://example.com/path?a=1", candidates[0].canonical_url)

        candidates_again, _ = run.normalize_candidates([entry], run_id="run-1")
        self.assertEqual(
            candidates[0].normalized_candidate_id,
            candidates_again[0].normalized_candidate_id,
        )


if __name__ == "__main__":
    unittest.main()
