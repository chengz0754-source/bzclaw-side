from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "sellersprite_stage_closure_lib.py"

SPEC = importlib.util.spec_from_file_location("sellersprite_stage_closure_lib", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SellerSpriteRenderPipelineTests(unittest.TestCase):
    def test_render_readme_preserves_role_freeze_and_boundary(self) -> None:
        evaluation = MODULE.evaluate_stage_status(REPO_ROOT)
        reconciled = MODULE.reconcile_truth_hosts(evaluation, REPO_ROOT)
        readme = reconciled["host_payload"]["readme_content"]

        self.assertIn("## Repo Role Freeze", readme)
        self.assertIn("## Candidate Sync Layer", readme)
        self.assertIn("reports/latest_sellersprite_owner_writeback_export.json", readme)
        self.assertIn("SELLERSPRITE_FLOW_CLOSED__BUSINESS_NOT_PROMOTED", readme)
        self.assertIn("scripts/run_sellersprite_stage_closure.py", readme)

    def test_owner_writeback_export_preserves_manual_boundary(self) -> None:
        evaluation = MODULE.evaluate_stage_status(REPO_ROOT)
        bundle = MODULE.build_owner_writeback_bundle(
            evaluation,
            REPO_ROOT,
            generated_at_utc="2026-04-16T00:00:00+00:00",
        )
        export_payload = bundle["export_payload"]

        self.assertEqual(export_payload["contract_id"], "sellersprite_owner_writeback_export_contract_v1")
        self.assertEqual(export_payload["business_promotion_boundary"], "BUSINESS_NOT_PROMOTED")
        self.assertEqual(export_payload["overall_repo_wording"], "SELLERSPRITE_FLOW_CLOSED__BUSINESS_NOT_PROMOTED")
        self.assertEqual(export_payload["owner_writeback_export_path"], "reports/latest_sellersprite_owner_writeback_export.json")
        self.assertGreaterEqual(export_payload["eligible_candidate_count"], 1)

    def test_reconcile_and_owner_export_are_deterministic_for_fixed_inputs(self) -> None:
        evaluation_a = MODULE.evaluate_stage_status(REPO_ROOT)
        evaluation_b = MODULE.evaluate_stage_status(REPO_ROOT)
        reconciled_a = MODULE.reconcile_truth_hosts(evaluation_a, REPO_ROOT)
        reconciled_b = MODULE.reconcile_truth_hosts(evaluation_b, REPO_ROOT)
        self.assertEqual(reconciled_a["canonical_board_rows"], reconciled_b["canonical_board_rows"])
        self.assertEqual(reconciled_a["host_payload"]["readme_content"], reconciled_b["host_payload"]["readme_content"])
        self.assertEqual(reconciled_a["host_payload"]["registry_content"], reconciled_b["host_payload"]["registry_content"])

        bundle_a = MODULE.build_owner_writeback_bundle(
            evaluation_a,
            REPO_ROOT,
            generated_at_utc="2026-04-16T00:00:00+00:00",
        )
        bundle_b = MODULE.build_owner_writeback_bundle(
            evaluation_b,
            REPO_ROOT,
            generated_at_utc="2026-04-16T00:00:00+00:00",
        )
        self.assertEqual(bundle_a["candidate_rows"], bundle_b["candidate_rows"])
        self.assertEqual(bundle_a["handoff"], bundle_b["handoff"])
        self.assertEqual(bundle_a["export_payload"], bundle_b["export_payload"])


if __name__ == "__main__":
    unittest.main()
