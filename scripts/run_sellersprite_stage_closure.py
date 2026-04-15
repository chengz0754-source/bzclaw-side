from __future__ import annotations

import argparse
from pathlib import Path

from sellersprite_stage_closure_lib import (
    build_owner_writeback_bundle,
    evaluate_stage_status,
    find_repo_root,
    render_implementation_summary,
    repo_paths,
    reconcile_truth_hosts,
    write_current_state,
    write_json,
    write_text,
    write_owner_writeback_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic SellerSprite current-stage evaluation, reconciliation, and writeback.")
    parser.add_argument("--repo-root", type=Path, default=None, help="Optional repo root override.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/latest_sellersprite_stage_status.json"),
        help="Machine-readable result output path.",
    )
    args = parser.parse_args()

    repo_root = find_repo_root(args.repo_root)
    paths = repo_paths(repo_root)
    evaluation_before_write = evaluate_stage_status(repo_root)
    reconciliation = reconcile_truth_hosts(evaluation_before_write, repo_root)
    written_files = write_current_state(reconciliation, repo_root)
    evaluation_after_write = evaluate_stage_status(repo_root)
    owner_writeback_bundle = build_owner_writeback_bundle(
        evaluation_after_write,
        repo_root,
        generated_at_utc=evaluation_after_write["generated_at_utc"],
    )
    owner_writeback_written_files = write_owner_writeback_bundle(owner_writeback_bundle, repo_root)

    consistency_check = {
        "truth_pack_to_render_consistent": evaluation_after_write["host_alignment"]["all_required_hosts_aligned"],
        "readme_render_aligned": evaluation_after_write["host_alignment"]["readme_aligned"],
        "board_render_aligned": evaluation_after_write["host_alignment"]["board_aligned"],
        "owner_template_aligned": evaluation_after_write["host_alignment"]["owner_template_aligned"],
        "owner_writeback_boundary_preserved": owner_writeback_bundle["export_payload"]["business_promotion_boundary"] == "BUSINESS_NOT_PROMOTED"
        and owner_writeback_bundle["export_payload"]["overall_repo_wording"] == "SELLERSPRITE_FLOW_CLOSED__BUSINESS_NOT_PROMOTED",
    }

    final_result = {
        "generated_at_utc": evaluation_after_write["generated_at_utc"],
        "pipeline": [
            "evaluate_sellersprite_stage_status",
            "reconcile_sellersprite_truth_hosts",
            "write_sellersprite_current_state",
            "evaluate_sellersprite_stage_status(post_write_verification)",
            "write_owner_writeback_externalization",
        ],
        "evaluation_before_write": evaluation_before_write,
        "reconciliation": reconciliation,
        "written_files": written_files,
        "evaluation_after_write": evaluation_after_write,
        "owner_writeback_written_files": owner_writeback_written_files,
        "owner_writeback_externalization": owner_writeback_bundle["export_payload"],
        "consistency_check": consistency_check,
    }

    output_path = args.output if args.output.is_absolute() else repo_root / args.output
    write_json(output_path, final_result)
    summary_content = render_implementation_summary(final_result, repo_root)
    write_text(paths["implementation_summary"], summary_content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
