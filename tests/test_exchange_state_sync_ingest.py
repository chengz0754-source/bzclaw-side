from __future__ import annotations

import codecs
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "import_exchange_state_sync.py"

SPEC = importlib.util.spec_from_file_location("import_exchange_state_sync", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ExchangeStateSyncIngestTests(unittest.TestCase):
    def test_preflight_keeps_happy_and_rollback_and_cleans_stale_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as exchange_root_text:
            exchange_paths = MODULE.ExchangeStatePaths.from_root(Path(exchange_root_text))
            exchange_paths.ensure_dirs()
            self._write_json(
                exchange_paths.verification_results_dir / "20260416_120001__verification_result__packet_exchange_happy.json",
                self._verification_result("packet_exchange_happy", downstream_allowed=True),
            )
            self._write_json(
                exchange_paths.verification_results_dir / "20260416_120002__verification_result__packet_exchange_rollback.json",
                self._verification_result("packet_exchange_rollback", downstream_allowed=False),
            )
            self._write_json(
                exchange_paths.verification_results_dir / "20260416_110000__verification_result__packet_exchange_cli.json",
                self._verification_result("packet_exchange_cli", downstream_allowed=True),
            )
            (exchange_paths.verification_results_dir / "20260416_120001__verification_summary__packet_exchange_happy.md").write_text(
                "# happy\n",
                encoding="utf-8",
            )
            (exchange_paths.verification_results_dir / "20260416_120002__verification_summary__packet_exchange_rollback.md").write_text(
                "# rollback\n",
                encoding="utf-8",
            )
            (exchange_paths.verification_results_dir / "20260416_110000__verification_summary__packet_exchange_cli.md").write_text(
                "# stale cli\n",
                encoding="utf-8",
            )
            self._write_json(
                exchange_paths.state_candidates_dir / "20260416_120101__state_candidate__packet_exchange_happy.json",
                self._candidate_envelope("packet_exchange_happy", "exchange_bridge_packet_exchange_happy"),
            )
            self._write_json(
                exchange_paths.state_candidates_dir / "20260416_120102__state_candidate__packet_exchange_rollback.json",
                self._candidate_envelope("packet_exchange_rollback", "exchange_bridge_packet_exchange_rollback"),
            )
            (exchange_paths.state_candidates_dir / "20260416_110001__state_candidate__packet_exchange_happy.json").write_text(
                json.dumps({"event_id": "decision-packet-event:packet_exchange_happy"}, ensure_ascii=False),
                encoding="utf-8",
            )

            preflight = MODULE.run_exchange_preflight(exchange_paths, repo_root=REPO_ROOT)

            self.assertEqual(
                [item.packet_id for item in preflight.kept_verification_results],
                ["packet_exchange_happy", "packet_exchange_rollback"],
            )
            self.assertEqual(
                [item.packet_id for item in preflight.kept_candidates],
                ["packet_exchange_happy", "packet_exchange_rollback"],
            )
            self.assertTrue(any(item["reason_code"] == "stale_nonselected_verification_result" for item in preflight.archived))
            self.assertTrue(any(item["reason_code"] == "stale_nonselected_verification_summary" for item in preflight.archived))
            self.assertTrue(any(item["reason_code"] == "nonconforming_state_candidate" for item in preflight.quarantined))

    def test_process_accepts_allowed_candidate_and_rejects_denied_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as exchange_root_text, tempfile.TemporaryDirectory() as import_root_text:
            exchange_paths = MODULE.ExchangeStatePaths.from_root(Path(exchange_root_text))
            exchange_paths.ensure_dirs()
            self._write_json(
                exchange_paths.verification_results_dir / "20260416_120001__verification_result__packet_exchange_happy.json",
                self._verification_result("packet_exchange_happy", downstream_allowed=True),
            )
            self._write_json(
                exchange_paths.verification_results_dir / "20260416_120002__verification_result__packet_exchange_rollback.json",
                self._verification_result("packet_exchange_rollback", downstream_allowed=False),
            )
            self._write_json(
                exchange_paths.state_candidates_dir / "20260416_120101__state_candidate__packet_exchange_happy.json",
                self._candidate_envelope("packet_exchange_happy", "exchange_bridge_packet_exchange_happy"),
            )
            self._write_json(
                exchange_paths.state_candidates_dir / "20260416_120102__state_candidate__packet_exchange_rollback.json",
                self._candidate_envelope("packet_exchange_rollback", "exchange_bridge_packet_exchange_rollback"),
            )

            preflight = MODULE.run_exchange_preflight(exchange_paths, repo_root=REPO_ROOT)
            proof = MODULE.process_exchange_state_sync(
                exchange_paths,
                repo_root=REPO_ROOT,
                preflight=preflight,
                import_destination_root=Path(import_root_text),
            )
            proof_paths = MODULE.write_proof_notes(exchange_paths, proof)

            self.assertEqual(proof["accepted_count"], 1)
            self.assertEqual(proof["rejected_count"], 1)
            happy = self._decision_by_packet(proof, "packet_exchange_happy")
            rollback = self._decision_by_packet(proof, "packet_exchange_rollback")
            self.assertEqual(happy["decision"], "accepted")
            self.assertEqual(rollback["decision"], "rejected")
            self.assertEqual(rollback["reason_code"], "DOWNSTREAM_STATE_SYNC_DENIED")

            import_root = Path(import_root_text)
            happy_record = import_root / happy["record_path"]
            happy_payload = import_root / happy["payload_path"]
            self.assertTrue(happy_record.exists())
            self.assertTrue(happy_payload.exists())
            payload = json.loads(happy_payload.read_text(encoding="utf-8"))
            self.assertEqual(payload["business_promotion_status"], "BUSINESS_NOT_PROMOTED")

            rollback_candidate_root = import_root / "docs" / "current_state" / "candidates"
            self.assertFalse((rollback_candidate_root / "exchange_bridge_packet_exchange_rollback.candidate.json").exists())
            self.assertFalse((rollback_candidate_root / "exchange_bridge_packet_exchange_rollback.payload.json").exists())

            self.assertTrue(proof_paths["json"].exists())
            self.assertTrue(proof_paths["md"].exists())
            self.assertFalse(proof_paths["json"].read_bytes().startswith(codecs.BOM_UTF8))

    def test_missing_verification_gate_rejects_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as exchange_root_text, tempfile.TemporaryDirectory() as import_root_text:
            exchange_paths = MODULE.ExchangeStatePaths.from_root(Path(exchange_root_text))
            exchange_paths.ensure_dirs()
            self._write_json(
                exchange_paths.state_candidates_dir / "20260416_120101__state_candidate__packet_exchange_happy.json",
                self._candidate_envelope("packet_exchange_happy", "exchange_bridge_packet_exchange_happy"),
            )

            preflight = MODULE.run_exchange_preflight(exchange_paths, repo_root=REPO_ROOT)
            proof = MODULE.process_exchange_state_sync(
                exchange_paths,
                repo_root=REPO_ROOT,
                preflight=preflight,
                import_destination_root=Path(import_root_text),
            )
            happy = self._decision_by_packet(proof, "packet_exchange_happy")
            self.assertEqual(happy["decision"], "rejected")
            self.assertEqual(happy["reason_code"], "VERIFICATION_GATE_MISSING")

    @staticmethod
    def _candidate_envelope(packet_id: str, candidate_id: str) -> dict[str, object]:
        return {
            "schema_version": "bzclaw.side.state_sync_candidate_input.v1",
            "candidate_family": "current_state_candidate",
            "candidate_id": candidate_id,
            "candidate_created_at_utc": "2026-04-16T00:00:00Z",
            "source_repo": "chengz0754-source/amazon-selection-automation",
            "source_plane": "B_EXECUTION_SIDECAR",
            "source_job": {
                "job_id": f"machine-b-job:decision-packet-event:{packet_id}",
                "run_id": f"run:machine-b-job_decision-packet-event_{packet_id}",
                "event_id": f"decision-packet-event:{packet_id}",
                "packet_id": packet_id,
            },
            "content_format": "json",
            "candidate_payload_json": {
                "schema_version": "bzclaw.side.current_state_candidate_payload.v1",
                "event_id": f"decision-packet-event:{packet_id}",
                "packet_id": packet_id,
                "job_id": f"machine-b-job:decision-packet-event:{packet_id}",
                "business_promotion_status": "BUSINESS_NOT_PROMOTED",
                "business_completion_claim": "NOT_CLAIMED",
            },
            "provenance_refs": [
                {
                    "ref_kind": "machine_b_run_receipt",
                    "ref_path": f"outputs/worker_runs/exchange_bridge/{packet_id}/02_generated_outputs/machine_b_run_receipt.json",
                },
                {
                    "ref_kind": "machine_b_artifact_manifest",
                    "ref_path": f"outputs/worker_runs/exchange_bridge/{packet_id}/02_generated_outputs/machine_b_artifact_manifest.json",
                },
                {
                    "ref_kind": "machine_b_run_summary",
                    "ref_path": f"outputs/worker_runs/exchange_bridge/{packet_id}/00_run_summary.md",
                },
            ],
            "review_flags": {
                "candidate_truth_only": True,
                "runtime_payload_embedded": False,
                "business_promotion_claimed": False,
            },
            "summary_lines": [
                "Candidate truth object only.",
                "Receipt visibility remains technical only.",
                "Business promotion remains not promoted.",
            ],
        }

    @staticmethod
    def _verification_result(packet_id: str, *, downstream_allowed: bool) -> dict[str, object]:
        return {
            "harness_kind": "a_exchange_verification_result_v1",
            "verified_at": "2026-04-16T00:10:00Z",
            "event_id": f"decision-packet-event:{packet_id}",
            "packet_id": packet_id,
            "job_id": f"machine-b-job:decision-packet-event:{packet_id}",
            "receipt_id": f"receipt:machine-b-job:decision-packet-event:{packet_id}",
            "verification_disposition": "PASS_TECHNICAL_CHECK_PENDING_STATE_SYNC" if downstream_allowed else "FAIL_ROLLBACK_VISIBLE",
            "downstream_state_sync_allowed": downstream_allowed,
            "lifecycle_after_verification": "RECEIPT_VISIBLE" if downstream_allowed else "ROLLED_BACK",
            "business_verified": False,
            "truth_sync_attempt_id": None,
            "verification": {
                "receipt_visible": True,
                "manifest_present": True,
                "summary": "test verification",
            },
        }

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _decision_by_packet(proof: dict[str, object], packet_id: str) -> dict[str, object]:
        for decision in proof["decisions"]:
            if decision["packet_id"] == packet_id:
                return decision
        raise AssertionError(f"Missing decision for packet_id={packet_id}")


if __name__ == "__main__":
    unittest.main()
