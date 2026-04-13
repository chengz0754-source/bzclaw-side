from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from sellersprite_stage_closure_lib import find_repo_root, read_json, relpath_str, repo_paths, utc_now_iso, write_csv_rows, write_json, write_text


def load_stage_evaluation(stage_status_path: Path) -> dict[str, Any]:
    payload = read_json(stage_status_path)
    if "evaluation_after_write" in payload:
        return payload["evaluation_after_write"]
    return payload


def build_reason_messages(reason_enums: dict[str, Any], reason_key: str) -> list[str]:
    catalog = reason_enums.get("catalog", {})
    return [catalog.get(code, code) for code in reason_enums.get(reason_key, [])]


def build_candidate_rows(truth_pack: dict[str, Any], owner_contract: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    packet_columns = owner_contract["packet_columns"]
    candidates: list[dict[str, Any]] = []
    for candidate in truth_pack.get("candidate_path_truth", []):
        if not candidate.get("eligible_for_owner_review"):
            continue
        row = {column: "" for column in packet_columns}
        row.update(
            {
                "candidate_id": candidate.get("candidate_id", ""),
                "direction_id": candidate.get("direction_id", ""),
                "keyword": candidate.get("keyword", ""),
                "site": candidate.get("site", ""),
                "candidate_source_mode": candidate.get("candidate_source_mode", "deterministic_truth_pack"),
                "candidate_path_id": candidate.get("candidate_path_id", ""),
                "eligible_candidate_count": str(candidate.get("eligible_candidate_count", "")),
                "sample_id": candidate.get("sample_id", ""),
                "sample_asin": candidate.get("sample_asin", ""),
                "sample_title": candidate.get("sample_title", ""),
                "candidate_market_name": candidate.get("candidate_market_name", ""),
                "current_pool_status": candidate.get("current_pool_status", ""),
                "owner_review_status": candidate.get("owner_review_status", owner_contract.get("default_owner_review_status", "PENDING")),
                "compliance": candidate.get("compliance", ""),
                "improvement_points": candidate.get("improvement_points", ""),
                "final_explanation": candidate.get("final_explanation", ""),
                "profit_pricing": candidate.get("profit_pricing", ""),
                "decision": candidate.get("decision", ""),
                "notes": candidate.get("notes", ""),
            }
        )
        candidates.append(row)
    return candidates, "deterministic_truth_pack"


def render_summary(handoff: dict[str, Any]) -> str:
    warnings = "\n".join(f"- {item}" for item in handoff["warnings"]) or "- none"
    eligible = "\n".join(
        f"- `{item['candidate_path_id']}` | `{item['direction_id']}` | `{item['keyword']}` | status `{item['current_pool_status']}` | eligible_count `{item['eligible_candidate_count']}`"
        for item in handoff["eligible_candidate_paths"]
    ) or "- none"
    debts = "\n".join(
        f"- `{item['line_id']}` | `{item['exact_debt']}`"
        for item in handoff["post_stage_open_debts_snapshot"]
    ) or "- none"
    return f"""# CODEX Implement Next-Stage Owner Handoff Generator Summary (2026-04-13)

## Scope

- Added deterministic owner/business next-stage handoff generation.
- The generator now reads machine-readable truth-pack and contract inputs only.
- The current-stage blocker hosts were not modified by this slice.

## Current Result

- `current_stage_closed = {str(handoff['current_stage_closed']).lower()}`
- `next_stage_required = {str(handoff['next_stage_required']).lower()}`
- `candidate_source_mode = {handoff['candidate_source_mode']}`
- owner writeback packet: `{handoff['owner_writeback_packet_path']}`

## Eligible Candidate Paths

{eligible}

## Post-Stage Open Debts

{debts}

## Warnings

{warnings}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic SellerSprite next-stage owner handoff outputs from structured truth-pack hosts.")
    parser.add_argument("--repo-root", type=Path, default=None, help="Optional repo root override.")
    parser.add_argument(
        "--stage-status",
        type=Path,
        default=Path("reports/latest_sellersprite_stage_status.json"),
        help="Stage evaluator result JSON path.",
    )
    args = parser.parse_args()

    repo_root = find_repo_root(args.repo_root)
    paths = repo_paths(repo_root)
    stage_status_path = args.stage_status if args.stage_status.is_absolute() else repo_root / args.stage_status
    stage_evaluation = load_stage_evaluation(stage_status_path)
    truth_pack = read_json(paths["truth_pack"])
    owner_contract = read_json(paths["owner_handoff_contract"])

    candidate_rows, candidate_source_mode = build_candidate_rows(truth_pack, owner_contract)
    owner_packet_path = repo_root / owner_contract["output_hosts"]["owner_writeback_packet_csv"]
    if candidate_rows:
        write_csv_rows(owner_packet_path, candidate_rows)
    else:
        write_csv_rows(owner_packet_path, [{field: "" for field in owner_contract["packet_columns"]}])

    warnings: list[str] = []
    if candidate_source_mode != "deterministic_truth_pack":
        warnings.append(f"Candidate source mode is `{candidate_source_mode}`, expected `deterministic_truth_pack`.")
    if not candidate_rows and bool(stage_evaluation["signals"]["next_stage_required"]):
        warnings.append("Truth pack did not expose any eligible owner-review candidate paths even though next_stage_required=true.")

    reason_enums = truth_pack.get("reason_enums", {})
    handoff = {
        "generated_at_utc": utc_now_iso(),
        "stage_status_path": relpath_str(stage_status_path, repo_root),
        "truth_pack_path": relpath_str(paths["truth_pack"], repo_root),
        "owner_handoff_contract_path": relpath_str(paths["owner_handoff_contract"], repo_root),
        "candidate_source_mode": candidate_source_mode,
        "candidate_source_reason": "Canonical candidate-path truth was loaded from the structured truth pack.",
        "current_stage_closed": bool(stage_evaluation["signals"]["current_stage_closed"]),
        "next_stage_required": bool(stage_evaluation["signals"]["next_stage_required"]),
        "current_legal_wording": truth_pack.get("current_legal_wording", {}),
        "next_stage_reason_codes": reason_enums.get("next_stage_required", []) if stage_evaluation["signals"]["next_stage_required"] else [],
        "why_next_stage_starts": build_reason_messages(reason_enums, "next_stage_required") if stage_evaluation["signals"]["next_stage_required"] else [],
        "eligible_candidate_paths": candidate_rows,
        "next_stage_candidate_list": candidate_rows,
        "required_owner_side_fields": owner_contract.get("required_owner_side_fields", []),
        "owner_handoff_field_schema": truth_pack.get("owner_handoff_field_schema", {}),
        "post_stage_open_debts_snapshot": truth_pack.get("post_stage_open_debts_snapshot", []),
        "owner_writeback_packet_path": relpath_str(owner_packet_path, repo_root),
        "warnings": warnings,
    }

    owner_handoff_json_path = repo_root / "reports" / "latest_sellersprite_owner_handoff.json"
    write_json(owner_handoff_json_path, handoff)
    summary_path = repo_root / "reports" / "CODEX_IMPLEMENT_NEXT_STAGE_OWNER_HANDOFF_GENERATOR_SUMMARY_20260413.md"
    write_text(summary_path, render_summary(handoff))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
