from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path
from typing import Any

from sellersprite_stage_closure_lib import (
    find_repo_root,
    read_csv_rows,
    read_json,
    read_text_best_effort,
    relpath_str,
    repo_paths,
    utc_now_iso,
    write_csv_rows,
    write_json,
    write_text,
)

OWNER_PACKET_FIELDS = [
    "candidate_id",
    "direction_id",
    "keyword",
    "site",
    "candidate_source_mode",
    "candidate_path_id",
    "eligible_candidate_count",
    "sample_id",
    "sample_asin",
    "sample_title",
    "candidate_market_name",
    "current_pool_status",
    "owner_review_status",
    "compliance",
    "improvement_points",
    "final_explanation",
    "profit_pricing",
    "decision",
    "notes",
]

REQUIRED_OWNER_SIDE_FIELDS = [
    {
        "field_id": "owner_review_status",
        "csv_column": "owner_review_status",
        "required": True,
        "description": "Track owner-side packet progress with PENDING / IN_PROGRESS / DONE.",
    },
    {
        "field_id": "compliance_review",
        "csv_column": "compliance",
        "required": True,
        "description": "Owner-side compliance judgment for the candidate path.",
    },
    {
        "field_id": "improvement_points",
        "csv_column": "improvement_points",
        "required": True,
        "description": "Owner-side improvement plan before promotion or sourcing.",
    },
    {
        "field_id": "final_explanation",
        "csv_column": "final_explanation",
        "required": True,
        "description": "Owner-side final business explanation for why the path should continue or stop.",
    },
    {
        "field_id": "profit_pricing",
        "csv_column": "profit_pricing",
        "required": True,
        "description": "Owner-side profit and pricing check for the next-stage decision.",
    },
    {
        "field_id": "decision",
        "csv_column": "decision",
        "required": True,
        "description": "Owner-side next-stage decision such as HOLD / GO / NO_GO.",
    },
    {
        "field_id": "notes",
        "csv_column": "notes",
        "required": False,
        "description": "Optional owner/business annotations for the packet.",
    },
]


def load_stage_evaluation(stage_status_path: Path) -> dict[str, Any]:
    payload = read_json(stage_status_path)
    if "evaluation_after_write" in payload:
        return payload["evaluation_after_write"]
    return payload


def normalize_status(value: str | None) -> str:
    return (value or "").strip().upper()


def discover_candidate_pool_csv(repo_root: Path) -> Path | None:
    candidates: list[Path] = []
    for path in repo_root.rglob("60_*.csv"):
        if ".git" in path.parts or ".venv" in path.parts:
            continue
        if "templates" in path.parts:
            continue
        candidates.append(path)
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0]


def read_csv_rows_by_index(path: Path) -> list[list[str]]:
    text = read_text_best_effort(path)
    with io.StringIO(text) as handle:
        return list(csv.reader(handle))


def load_lane_metadata(repo_root: Path) -> dict[str, dict[str, str]]:
    metadata_path = repo_root / "templates" / "selection_input_batches" / "05__INPUT__T11_T12_STABILITY_CHECK__20260412.csv"
    rows = read_csv_rows_by_index(metadata_path)
    lane_metadata: dict[str, dict[str, str]] = {}
    for row in rows[1:]:
        if len(row) < 6:
            continue
        direction_id = row[0].strip()
        if not direction_id:
            continue
        lane_metadata[direction_id] = {
            "direction_id": direction_id,
            "task_name": row[1].strip() if len(row) > 1 else "",
            "purpose_type": row[2].strip() if len(row) > 2 else "",
            "keyword": row[4].strip() if len(row) > 4 else "",
            "site": row[5].strip() if len(row) > 5 else "",
            "note": row[12].strip() if len(row) > 12 else "",
        }
    return lane_metadata


def pick_value(row: dict[str, str], aliases: list[str]) -> str:
    for alias in aliases:
        if alias in row and str(row[alias]).strip():
            return str(row[alias]).strip()
    normalized = {str(key).strip().lower(): key for key in row.keys()}
    for alias in aliases:
        key = normalized.get(alias.strip().lower())
        if key is not None and str(row[key]).strip():
            return str(row[key]).strip()
    return ""


def build_direct_candidate_rows(candidate_pool_path: Path) -> tuple[list[dict[str, Any]], str]:
    rows = read_csv_rows(candidate_pool_path)
    candidates: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        current_pool_status = normalize_status(pick_value(row, ["当前下推状态", "current_pool_status"]))
        if current_pool_status not in {"HOLD", "PASS"}:
            continue
        direction_id = pick_value(row, ["方向ID", "direction_id"])
        sample_id = pick_value(row, ["样品ID", "sample_id"])
        candidate_id = sample_id or f"{direction_id or 'UNKNOWN'}__{index:03d}"
        candidate = {
            "candidate_id": candidate_id,
            "direction_id": direction_id,
            "keyword": pick_value(row, ["方向词", "direction_word", "keyword", "关键词"]),
            "site": pick_value(row, ["站点", "site"]),
            "candidate_source_mode": "direct_60_csv",
            "candidate_path_id": candidate_id,
            "eligible_candidate_count": 1,
            "sample_id": sample_id,
            "sample_asin": pick_value(row, ["样品ASIN", "sample_asin"]),
            "sample_title": pick_value(row, ["样品标题", "sample_title", "title"]),
            "candidate_market_name": pick_value(row, ["候选市场名称", "candidate_market_name"]),
            "current_pool_status": current_pool_status,
            "owner_review_status": "PENDING",
            "compliance": "",
            "improvement_points": "",
            "final_explanation": "",
            "profit_pricing": "",
            "decision": "",
            "notes": "direct 60 candidate row",
        }
        candidates.append(candidate)
    return candidates, "direct_60_csv"


def build_fallback_candidate_rows(stage_evaluation: dict[str, Any], lane_metadata: dict[str, dict[str, str]]) -> tuple[list[dict[str, Any]], str]:
    candidates: list[dict[str, Any]] = []
    artifact_records = stage_evaluation.get("artifacts", {}).get("records", {})
    for direction_id, metadata in lane_metadata.items():
        record = artifact_records.get(direction_id, {}).get("60")
        if not record:
            continue
        status_counts = record.get("status_counts", {})
        eligible_count = int(status_counts.get("HOLD", 0)) + int(status_counts.get("PASS", 0))
        if eligible_count <= 0:
            continue
        primary_status = "HOLD" if int(status_counts.get("HOLD", 0)) > 0 else "PASS"
        candidates.append(
            {
                "candidate_id": f"{direction_id}__CURRENT_HOLD_CANDIDATE_PATH",
                "direction_id": direction_id,
                "keyword": metadata.get("keyword", ""),
                "site": metadata.get("site", ""),
                "candidate_source_mode": "stage_truth_fallback",
                "candidate_path_id": f"{direction_id}::CURRENT_HOLD_CANDIDATE_PATH",
                "eligible_candidate_count": eligible_count,
                "sample_id": "",
                "sample_asin": "",
                "sample_title": "",
                "candidate_market_name": metadata.get("keyword", ""),
                "current_pool_status": primary_status,
                "owner_review_status": "PENDING",
                "compliance": "",
                "improvement_points": "",
                "final_explanation": "",
                "profit_pricing": "",
                "decision": "",
                "notes": "fallback packet synthesized from current stage truth because direct 60 csv is not visible in repo",
            }
        )
    return candidates, "stage_truth_fallback"


def load_post_stage_open_debts(repo_root: Path) -> list[dict[str, str]]:
    debt_rows = read_csv_rows(repo_paths(repo_root)["debt_register"])
    return [
        row
        for row in debt_rows
        if row.get("debt_class") == "POST_STAGE_OPEN_DEBT" and row.get("current_state") == "OPEN"
    ]


def why_next_stage_starts(stage_evaluation: dict[str, Any]) -> list[str]:
    signals = stage_evaluation["signals"]
    reasons: list[str] = []
    if signals.get("current_stage_closed"):
        reasons.append("SellerSprite current stage is already FLOW_CLOSED by deterministic evaluator output.")
    if signals.get("next_stage_required"):
        reasons.append("Business promotion remains pending and belongs to the next-stage owner/business flow.")
    if signals.get("post_stage_open_debt_present"):
        reasons.append("T02/T03/T04 remain tracked as post-stage open debt and do not block the current-stage closure.")
    reasons.append("Owner-side manual writeback fields were externalized from the current-stage closure gate.")
    return reasons


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
- The generator no longer depends on Codex to hand-assemble the next move.
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
    parser = argparse.ArgumentParser(description="Generate deterministic SellerSprite next-stage owner handoff outputs.")
    parser.add_argument("--repo-root", type=Path, default=None, help="Optional repo root override.")
    parser.add_argument(
        "--stage-status",
        type=Path,
        default=Path("reports/latest_sellersprite_stage_status.json"),
        help="Stage evaluator result JSON path.",
    )
    parser.add_argument(
        "--candidate-pool-csv",
        type=Path,
        default=None,
        help="Optional explicit 60_候选样品池.csv path. If omitted, the script will auto-discover one or use fallback mode.",
    )
    args = parser.parse_args()

    repo_root = find_repo_root(args.repo_root)
    stage_status_path = args.stage_status if args.stage_status.is_absolute() else repo_root / args.stage_status
    stage_evaluation = load_stage_evaluation(stage_status_path)
    lane_metadata = load_lane_metadata(repo_root)
    explicit_candidate_pool = None
    if args.candidate_pool_csv is not None:
        explicit_candidate_pool = args.candidate_pool_csv if args.candidate_pool_csv.is_absolute() else repo_root / args.candidate_pool_csv
    candidate_pool_path = explicit_candidate_pool if explicit_candidate_pool and explicit_candidate_pool.exists() else discover_candidate_pool_csv(repo_root)

    warnings: list[str] = []
    if candidate_pool_path is not None:
        candidate_rows, candidate_source_mode = build_direct_candidate_rows(candidate_pool_path)
        if not candidate_rows:
            warnings.append("Direct 60 csv was discovered but did not yield any HOLD/PASS candidate rows; fallback mode was used instead.")
            candidate_rows, candidate_source_mode = build_fallback_candidate_rows(stage_evaluation, lane_metadata)
    else:
        candidate_rows, candidate_source_mode = build_fallback_candidate_rows(stage_evaluation, lane_metadata)
        warnings.append("No direct repo-local 60 candidate-pool CSV was discovered; owner handoff was synthesized from deterministic stage truth.")

    owner_packet_path = repo_root / "templates" / "owner_manual_writeback" / "02__SELLERSPRITE_OWNER_STAGE_WRITEBACK_PACKET__20260413.csv"
    if candidate_rows:
        write_csv_rows(owner_packet_path, candidate_rows)
    else:
        write_csv_rows(owner_packet_path, [{field: "" for field in OWNER_PACKET_FIELDS}])

    post_stage_open_debts = load_post_stage_open_debts(repo_root)
    handoff = {
        "generated_at_utc": utc_now_iso(),
        "stage_status_path": relpath_str(stage_status_path, repo_root),
        "candidate_pool_csv_path": relpath_str(candidate_pool_path, repo_root) if candidate_pool_path is not None else None,
        "candidate_source_mode": candidate_source_mode,
        "current_stage_closed": bool(stage_evaluation["signals"]["current_stage_closed"]),
        "next_stage_required": bool(stage_evaluation["signals"]["next_stage_required"]),
        "why_next_stage_starts": why_next_stage_starts(stage_evaluation),
        "eligible_candidate_paths": candidate_rows,
        "next_stage_candidate_list": candidate_rows,
        "required_owner_side_fields": REQUIRED_OWNER_SIDE_FIELDS,
        "post_stage_open_debts_snapshot": post_stage_open_debts,
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
