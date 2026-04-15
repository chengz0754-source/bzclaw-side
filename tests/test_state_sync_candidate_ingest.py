from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "import_state_sync_candidate.py"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "state_sync_candidate_current_state_example.json"

SPEC = importlib.util.spec_from_file_location("import_state_sync_candidate", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StateSyncCandidateIngestTests(unittest.TestCase):
    def load_fixture(self) -> dict:
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_contract_alignment_matches_state_sync_schema(self) -> None:
        roots = MODULE.validate_contract_alignment(REPO_ROOT)
        self.assertEqual(
            roots,
            {
                "truth_pack_candidate": "docs/truth_pack/candidates",
                "board_candidate": "reports/board/candidates",
                "current_state_candidate": "docs/current_state/candidates",
            },
        )

    def test_ingest_materializes_candidate_record_and_payload(self) -> None:
        fixture = self.load_fixture()
        with tempfile.TemporaryDirectory() as tmpdir:
            destination_root = Path(tmpdir)
            plan = MODULE.build_ingest_plan(fixture, REPO_ROOT, destination_root=destination_root)
            MODULE.materialize_candidate(plan)

            record_path = plan["record_path"]
            payload_path = plan["payload_path"]
            self.assertTrue(record_path.exists())
            self.assertTrue(payload_path.exists())

            record = json.loads(record_path.read_text(encoding="utf-8"))
            payload = json.loads(payload_path.read_text(encoding="utf-8"))
            self.assertEqual(record["schema_version"], "bzclaw.side.state_sync_candidate_record.v1")
            self.assertEqual(record["candidate_family"], "current_state_candidate")
            self.assertEqual(payload["business_promotion_status"], "BUSINESS_NOT_PROMOTED")
            self.assertEqual(record["materialized_payload_path"], "docs/current_state/candidates/p15_current_state_candidate_sample.payload.json")

    def test_forbidden_provenance_path_is_rejected(self) -> None:
        fixture = self.load_fixture()
        fixture["provenance_refs"][0]["ref_path"] = "playwright/screenshots/raw.png"
        with self.assertRaisesRegex(ValueError, "Forbidden provenance"):
            MODULE.build_ingest_plan(fixture, REPO_ROOT)

    def test_manual_only_family_is_rejected(self) -> None:
        fixture = self.load_fixture()
        fixture["candidate_family"] = "owner_writeback"
        with self.assertRaisesRegex(ValueError, "manual-only"):
            MODULE.build_ingest_plan(fixture, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
