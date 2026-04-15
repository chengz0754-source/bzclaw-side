from __future__ import annotations

import copy
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TASK_DATE = "2026-04-13"
TASK_STAMP = "20260413"
REPO_ROLE_FREEZE_DATE = "2026-04-15"
EXPECTED_LANES = ("T11", "T12")
EXPECTED_ARTIFACT_CODES = ("12", "22", "42", "60")
OWNER_WRITEBACK_EXPORT_CONTRACT_ID = "sellersprite_owner_writeback_export_contract_v1"
OWNER_WRITEBACK_EXPORT_VERSION = 1
OWNER_WRITEBACK_BOUNDARY = "BUSINESS_NOT_PROMOTED"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__).resolve()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    raise FileNotFoundError("Could not locate repo root from current script path.")


def read_text_best_effort(path: Path) -> str:
    encodings = ("utf-8", "utf-8-sig", "gb18030", "cp936")
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        return path.read_text(encoding="utf-8", errors="replace")
    return path.read_text()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip("\n") + "\n", encoding="utf-8", newline="\n")


def read_json(path: Path) -> Any:
    return json.loads(read_text_best_effort(path))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    text = read_text_best_effort(path)
    with io.StringIO(text) as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def read_csv_header(path: Path) -> list[str]:
    text = read_text_best_effort(path)
    with io.StringIO(text) as handle:
        reader = csv.reader(handle)
        return next(reader, [])


def write_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV to {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def relpath_str(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_existing_path(candidates: list[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def repo_paths(repo_root: Path) -> dict[str, Path]:
    reports_dir = repo_root / "reports"
    selection_reports_dir = reports_dir / "selection"
    return {
        "repo_root": repo_root,
        "readme": repo_root / "README.md",
        "registry": repo_root / "skills" / "skill_sellersprite_four_line_runtime_registry.md",
        "contract": repo_root / "contracts" / "sellersprite_current_stage_closure_contract_v1.json",
        "owner_handoff_contract": repo_root / "contracts" / "sellersprite_owner_handoff_contract_v1.json",
        "owner_writeback_export_contract": repo_root / "contracts" / "sellersprite_owner_writeback_export_contract_v1.json",
        "truth_pack": reports_dir / "sellersprite_truth_pack_current.json",
        "board": resolve_existing_path(
            [
                selection_reports_dir / "MASTER_PROGRESS_BOARD__20260412.csv",
                reports_dir / "MASTER_PROGRESS_BOARD__20260412.csv",
            ]
        ),
        "debt_register": resolve_existing_path(
            [
                selection_reports_dir / "SELLERSPRITE_POST_STAGE_OPEN_DEBT_REGISTER__20260413.csv",
                reports_dir / "SELLERSPRITE_POST_STAGE_OPEN_DEBT_REGISTER__20260413.csv",
            ]
        ),
        "owner_packet": repo_root / "templates" / "owner_manual_writeback" / "02__SELLERSPRITE_OWNER_STAGE_WRITEBACK_PACKET__20260413.csv",
        "latest_status": reports_dir / "latest_sellersprite_stage_status.json",
        "latest_owner_handoff": reports_dir / "latest_sellersprite_owner_handoff.json",
        "latest_owner_writeback_export": reports_dir / "latest_sellersprite_owner_writeback_export.json",
        "implementation_summary": reports_dir / "CODEX_IMPLEMENT_DETERMINISTIC_PY_STAGE_EVALUATOR_SUMMARY_20260413.md",
        "truth_pack_implementation_summary": reports_dir / "CODEX_IMPLEMENT_MACHINE_READABLE_TRUTH_PACK_AND_REMOVE_SUMMARY_PARSING_SUMMARY_20260413.md",
        "owner_handoff_summary": reports_dir / "CODEX_IMPLEMENT_NEXT_STAGE_OWNER_HANDOFF_GENERATOR_SUMMARY_20260413.md",
    }


def normalize_multiline_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_board_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["phase_id"]: row for row in rows}


def artifact_coverage(artifact_records: dict[str, dict[str, dict[str, Any]]]) -> dict[str, dict[str, bool]]:
    coverage: dict[str, dict[str, bool]] = {}
    for line_id in EXPECTED_LANES:
        coverage[line_id] = {}
        for artifact_code in EXPECTED_ARTIFACT_CODES:
            record = artifact_records.get(line_id, {}).get(artifact_code)
            coverage[line_id][artifact_code] = bool(record and record.get("exists") and record.get("parses"))
    return coverage


def coverage_complete(coverage: dict[str, dict[str, bool]]) -> bool:
    return all(coverage.get(line_id, {}).get(artifact_code, False) for line_id in EXPECTED_LANES for artifact_code in EXPECTED_ARTIFACT_CODES)


def build_artifact_evidence_from_truth_pack(truth_pack: dict[str, Any], truth_pack_path: Path, repo_root: Path) -> dict[str, Any]:
    matrix = truth_pack.get("artifact_matrix", {})
    records: dict[str, dict[str, dict[str, Any]]] = {}
    for line_id in EXPECTED_LANES:
        line_records: dict[str, dict[str, Any]] = {}
        for artifact_code in EXPECTED_ARTIFACT_CODES:
            source_record = matrix.get(line_id, {}).get(artifact_code)
            if source_record is None:
                continue
            record = copy.deepcopy(source_record)
            record.setdefault("line_id", line_id)
            record.setdefault("artifact_code", artifact_code)
            record.setdefault("source_kind", "truth_pack")
            record.setdefault("source_rank", 90)
            record.setdefault("source_path", relpath_str(truth_pack_path, repo_root))
            record.setdefault("exists", True)
            record.setdefault("parses", True)
            record.setdefault("status_counts", {})
            line_records[artifact_code] = record
        if line_records:
            records[line_id] = line_records

    coverage = artifact_coverage(records)
    complete = coverage_complete(coverage)
    source_observability = truth_pack.get("source_observability", {})
    source_mode = truth_pack.get("artifact_evidence_mode", "truth_pack")
    if not complete and source_mode == "truth_pack":
        source_mode = "truth_pack_incomplete"

    return {
        "records": records,
        "coverage": coverage,
        "coverage_complete": complete,
        "source_mode": source_mode,
        "artifact_evidence_mode": source_mode,
        "actual_csv_records_found": int(source_observability.get("actual_csv_records_found", 0)),
        "summary_records_used": 0,
        "summary_sources_checked": [],
        "truth_pack_path": relpath_str(truth_pack_path, repo_root),
        "truth_pack_version": truth_pack.get("version"),
        "raw_csv_visibility": source_observability,
    }


def phase_row_path_overrides(truth_pack: dict[str, Any]) -> dict[str, dict[str, str]]:
    overrides: dict[str, dict[str, str]] = {}
    mapping = truth_pack.get("board_path_mapping", {})
    phase_rows = mapping.get("phase_rows", {})
    for phase_id, fields in phase_rows.items():
        valid_fields = {key: str(value) for key, value in fields.items() if key in {"skill_file", "runner_py", "summary_file"}}
        if valid_fields:
            overrides[phase_id] = valid_fields
    return overrides


def build_phase_row_updates(evaluation: dict[str, Any], truth_pack: dict[str, Any]) -> dict[str, dict[str, str]]:
    current_stage_closed = evaluation["signals"]["current_stage_closed"]
    next_stage_required = evaluation["signals"]["next_stage_required"]
    post_stage_open_debt_present = evaluation["signals"]["post_stage_open_debt_present"]
    updates: dict[str, dict[str, str]] = {
        "P0": {
            "current_git_status": "FLOW_NOT_CLOSED__BUSINESS_NOT_APPLICABLE",
            "flow_closure_status": "FLOW_NOT_CLOSED",
            "business_promotion_status": "BUSINESS_NOT_APPLICABLE",
            "current_blocker": "NON_BLOCKING_HARDENING_DEBT__STEP1_PREPARE_EXPORT_CHECKPOINT__STEP4_EXPORT_LOG_BASELINE_CHECKPOINT__STEP2_KEYWORD_RESEARCH_EXPORT_CONTROL",
        }
    }
    if current_stage_closed:
        updates["P1"] = {
            "current_git_status": "CURRENT_STAGE_FLOW_CLOSED__STABILITY_CONFIRMED__NEXT_STAGE_OWNER_PROMOTION_PENDING"
            if next_stage_required
            else "CURRENT_STAGE_FLOW_CLOSED__STABILITY_CONFIRMED__NEXT_STAGE_NOT_REQUIRED",
            "flow_closure_status": "FLOW_CLOSED",
            "business_promotion_status": "BUSINESS_NOT_PROMOTED" if next_stage_required else "BUSINESS_PROMOTED",
            "current_blocker": "NONE__CURRENT_STAGE_FLOW_CLOSED",
        }
        t234_status = (
            "CURRENT_STAGE_FLOW_CLOSED__REUSABLE_LINE__POST_STAGE_OPEN_DEBT_TRACKED"
            if post_stage_open_debt_present
            else "CURRENT_STAGE_FLOW_CLOSED__REUSABLE_LINE"
        )
        for phase_id in ("P2", "P3", "P4"):
            updates[phase_id] = {
                "current_git_status": t234_status,
                "flow_closure_status": "FLOW_CLOSED",
                "business_promotion_status": "BUSINESS_NOT_PROMOTED",
                "current_blocker": "NONE__CURRENT_STAGE_FLOW_CLOSED",
            }
    else:
        updates["P1"] = {
            "current_git_status": "CURRENT_STAGE_FLOW_NOT_CLOSED__REPAIR_REQUIRED",
            "flow_closure_status": "FLOW_NOT_CLOSED",
            "business_promotion_status": "BUSINESS_NOT_PROMOTED",
            "current_blocker": evaluation["current_stage_blocker"]["status"],
        }

    for phase_id, field_overrides in phase_row_path_overrides(truth_pack).items():
        updates.setdefault(phase_id, {}).update(field_overrides)
    return updates


def apply_phase_row_updates(rows: list[dict[str, str]], updates: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    canonical_rows = copy.deepcopy(rows)
    for row in canonical_rows:
        phase_updates = updates.get(row["phase_id"])
        if phase_updates:
            row.update(phase_updates)
    return canonical_rows


def canonical_board_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["phase_id"]: row for row in rows}


def render_readme(evaluation: dict[str, Any], canonical_rows: list[dict[str, str]], root: Path) -> str:
    row_index = canonical_board_index(canonical_rows)
    artifact_source_mode = evaluation["artifacts"]["source_mode"]
    truth_pack_path = evaluation["paths"]["truth_pack"]
    current_legal_wording = evaluation["current_legal_wording"]
    return f"""# SellerSprite Current-Stage Closure Contract

> Repo role freeze on `{REPO_ROLE_FREEZE_DATE}`: `E:\\bzclaw-side` is the Machine B business
> state host. It is not an online execution bus, not a worker host, and not
> the A-side control plane. The frozen state-sync contract lives at
> `docs/state_sync_contract_current.md`.

## Repo Role Freeze

- A `bzclaw`: only control plane, approval plane, dispatch truth, and final
  verification owner
- B `amazon-selection-automation`: execution sidecar, local model runtime,
  Playwright, receipts, and runtime artifacts
- B `bzclaw-side`: business state host for truth-pack, board, current-state,
  and owner writeback
- Active truth-pack host: `reports/sellersprite_truth_pack_current.json`
- Active board host: `reports/selection/MASTER_PROGRESS_BOARD__20260412.csv`
- Active current-state hosts:
  - `README.md`
  - `reports/latest_sellersprite_stage_status.json`
- Active owner writeback hosts:
  - `templates/owner_manual_writeback/02__SELLERSPRITE_OWNER_STAGE_WRITEBACK_PACKET__20260413.csv`
  - `reports/latest_sellersprite_owner_handoff.json`
  - `reports/latest_sellersprite_owner_writeback_export.json`

## Candidate Sync Layer

Automated candidate ingest is frozen to reviewable staging roots only:

- `docs/truth_pack/candidates/`
- `reports/board/candidates/`
- `docs/current_state/candidates/`

Those roots accept candidate truth objects only. They do not replace the active
hosts above, and they must not become runtime drop zones.

Standardized Machine B receipts, manifests, and run summaries may appear only
as provenance refs inside candidate metadata. Raw runtime logs, Playwright
artifacts, queue traffic, and secrets still stay out of git truth.

This file is a deterministic current-state host rendered by `scripts/run_sellersprite_stage_closure.py`.

## Current Verdict

- SellerSprite current-stage closure = `{current_legal_wording["current_stage_closure_status"]}`.
- `flow_closed = {str(evaluation["signals"]["flow_closed"]).lower()}`
- `artifact_depth_reconciled = {str(evaluation["signals"]["artifact_depth_reconciled"]).lower()}`
- `hardening_debt_blocking = {str(evaluation["signals"]["hardening_debt_blocking"]).lower()}`
- `post_stage_open_debt_present = {str(evaluation["signals"]["post_stage_open_debt_present"]).lower()}`
- `current_stage_closed = {str(evaluation["signals"]["current_stage_closed"]).lower()}`
- `next_stage_required = {str(evaluation["signals"]["next_stage_required"]).lower()}`
- overall legal wording = `{current_legal_wording["overall_repo_wording"]}`

## Current Git Truth

- `P0` shared continuity remains `NON_BLOCKING_HARDENING_DEBT`.
- `T11 / T12` artifact-depth is reconciled and remains the canonical file-backed T01 reference pair.
- `T01`, `T02`, `T03`, and `T04` are SellerSprite line-level `FLOW_CLOSED` lines.
- `T02 / T03 / T04` remain `POST_STAGE_OPEN_DEBT`, but that debt does not reopen current-stage closure.
- Owner-side manual writeback fields remain outside the current-stage closure gate.

## Machine Status Host

- latest machine-readable status: `reports/latest_sellersprite_stage_status.json`
- latest machine-readable truth pack: `{truth_pack_path}`
- artifact evidence mode for the latest evaluation: `{artifact_source_mode}`
- physical progress-board host in this workspace: `{relpath_str(repo_paths(root)["board"], root)}`

## Current Board Snapshot

- `P1` = `{row_index["P1"]["current_git_status"]}`
- `P2` = `{row_index["P2"]["current_git_status"]}`
- `P3` = `{row_index["P3"]["current_git_status"]}`
- `P4` = `{row_index["P4"]["current_git_status"]}`

## Next-Stage Boundary

- `BUSINESS_PROMOTED` belongs to the next-stage owner/business flow.
- Owner-side manual writeback starts after current-stage flow closure.
- If promotion work is needed, move forward from current `HOLD` candidate rows without reopening current-stage SellerSprite continuity.
"""


def render_registry(evaluation: dict[str, Any], canonical_rows: list[dict[str, str]]) -> str:
    row_index = canonical_board_index(canonical_rows)
    truth_pack_path = evaluation["paths"]["truth_pack"]
    return f"""# skill_sellersprite_four_line_runtime_registry

This registry is a deterministic current-state host rendered by `scripts/run_sellersprite_stage_closure.py`.

## Current Git Truth

- SellerSprite current-stage closure contract is flow-only:
  - `current_stage_closure_status = FLOW_CLOSED`
  - `current_stage_closed = {str(evaluation["signals"]["current_stage_closed"]).lower()}`
  - `artifact_depth_reconciled = {str(evaluation["signals"]["artifact_depth_reconciled"]).lower()}`
- `business_promotion_status` belongs to the next-stage owner/business flow and does not reopen current-stage closure.
- `P0` remains non-blocking hardening debt:
  - `hardening_debt_blocking = {str(evaluation["signals"]["hardening_debt_blocking"]).lower()}`
- `T02 / T03 / T04` remain `POST_STAGE_OPEN_DEBT`, not current-stage blockers.
- latest machine-readable status host: `reports/latest_sellersprite_stage_status.json`
- latest machine-readable truth pack: `{truth_pack_path}`

## Runtime Registry

### T01 / MARKET_DISCOVERY

- flow_closure_status: `{row_index["P1"]["flow_closure_status"]}`
- business_promotion_status: `{row_index["P1"]["business_promotion_status"]}`
- current line truth: `{row_index["P1"]["current_git_status"]}`
- current-stage blocker status: `{row_index["P1"]["current_blocker"]}`

### T02 / PRODUCT_IDEA_VALIDATION

- flow_closure_status: `{row_index["P2"]["flow_closure_status"]}`
- business_promotion_status: `{row_index["P2"]["business_promotion_status"]}`
- current line truth: `{row_index["P2"]["current_git_status"]}`
- current-stage blocker status: `{row_index["P2"]["current_blocker"]}`

### T03 / COMPETITOR_REVERSE_MINING

- flow_closure_status: `{row_index["P3"]["flow_closure_status"]}`
- business_promotion_status: `{row_index["P3"]["business_promotion_status"]}`
- current line truth: `{row_index["P3"]["current_git_status"]}`
- current-stage blocker status: `{row_index["P3"]["current_blocker"]}`

### T04 / SUPPLY_CHAIN_BACKSOLVE

- flow_closure_status: `{row_index["P4"]["flow_closure_status"]}`
- business_promotion_status: `{row_index["P4"]["business_promotion_status"]}`
- current line truth: `{row_index["P4"]["current_git_status"]}`
- current-stage blocker status: `{row_index["P4"]["current_blocker"]}`
"""


def build_reason_messages(reason_enums: dict[str, Any], reason_key: str) -> list[str]:
    catalog = reason_enums.get("catalog", {})
    codes = reason_enums.get(reason_key, [])
    return [catalog.get(code, code) for code in codes]


def load_stage_evaluation_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if "evaluation_after_write" in payload:
        return payload["evaluation_after_write"]
    return payload


def build_owner_writeback_candidate_rows(truth_pack: dict[str, Any], owner_contract: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
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


def render_owner_writeback_summary(handoff: dict[str, Any], export_payload: dict[str, Any]) -> str:
    warnings = "\n".join(f"- {item}" for item in handoff["warnings"]) or "- none"
    eligible = "\n".join(
        f"- `{item['candidate_path_id']}` | `{item['direction_id']}` | `{item['keyword']}` | status `{item['current_pool_status']}` | eligible_count `{item['eligible_candidate_count']}`"
        for item in handoff["eligible_candidate_paths"]
    ) or "- none"
    debts = "\n".join(
        f"- `{item['line_id']}` | `{item['exact_debt']}`"
        for item in handoff["post_stage_open_debts_snapshot"]
    ) or "- none"
    return f"""# CODEX Implement Next-Stage Owner Handoff Generator Summary ({TASK_DATE})

## Scope

- Added deterministic owner/business next-stage handoff generation.
- The generator now reads machine-readable truth-pack and contract inputs only.
- The owner writeback export remains externalized from runtime logs.

## Current Result

- `current_stage_closed = {str(handoff['current_stage_closed']).lower()}`
- `next_stage_required = {str(handoff['next_stage_required']).lower()}`
- `candidate_source_mode = {handoff['candidate_source_mode']}`
- owner writeback packet: `{handoff['owner_writeback_packet_path']}`
- owner writeback export: `{export_payload['owner_writeback_export_path']}`
- business promotion boundary: `{export_payload['business_promotion_boundary']}`

## Eligible Candidate Paths

{eligible}

## Post-Stage Open Debts

{debts}

## Warnings

{warnings}
"""


def build_owner_writeback_bundle(
    stage_evaluation: dict[str, Any],
    repo_root: Path | None = None,
    *,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    root = find_repo_root(repo_root)
    paths = repo_paths(root)
    evaluation = load_stage_evaluation_payload(stage_evaluation)
    truth_pack = read_json(paths["truth_pack"])
    owner_contract = read_json(paths["owner_handoff_contract"])
    export_contract = read_json(paths["owner_writeback_export_contract"])

    candidate_rows, candidate_source_mode = build_owner_writeback_candidate_rows(truth_pack, owner_contract)
    generated_at = generated_at_utc or evaluation.get("generated_at_utc") or utc_now_iso()

    warnings: list[str] = []
    if candidate_source_mode != "deterministic_truth_pack":
        warnings.append(f"Candidate source mode is `{candidate_source_mode}`, expected `deterministic_truth_pack`.")
    if not candidate_rows and bool(evaluation["signals"]["next_stage_required"]):
        warnings.append("Truth pack did not expose any eligible owner-review candidate paths even though next_stage_required=true.")
    if evaluation.get("current_legal_wording", {}).get("overall_repo_wording") != "SELLERSPRITE_FLOW_CLOSED__BUSINESS_NOT_PROMOTED":
        warnings.append("Overall repo wording drifted away from the required BUSINESS_NOT_PROMOTED boundary.")

    reason_enums = truth_pack.get("reason_enums", {})
    handoff = {
        "generated_at_utc": generated_at,
        "stage_status_path": relpath_str(paths["latest_status"], root),
        "truth_pack_path": relpath_str(paths["truth_pack"], root),
        "owner_handoff_contract_path": relpath_str(paths["owner_handoff_contract"], root),
        "candidate_source_mode": candidate_source_mode,
        "candidate_source_reason": "Canonical candidate-path truth was loaded from the structured truth pack.",
        "current_stage_closed": bool(evaluation["signals"]["current_stage_closed"]),
        "next_stage_required": bool(evaluation["signals"]["next_stage_required"]),
        "current_legal_wording": truth_pack.get("current_legal_wording", {}),
        "next_stage_reason_codes": reason_enums.get("next_stage_required", []) if evaluation["signals"]["next_stage_required"] else [],
        "why_next_stage_starts": build_reason_messages(reason_enums, "next_stage_required") if evaluation["signals"]["next_stage_required"] else [],
        "eligible_candidate_paths": candidate_rows,
        "next_stage_candidate_list": candidate_rows,
        "required_owner_side_fields": owner_contract.get("required_owner_side_fields", []),
        "owner_handoff_field_schema": truth_pack.get("owner_handoff_field_schema", {}),
        "post_stage_open_debts_snapshot": truth_pack.get("post_stage_open_debts_snapshot", []),
        "owner_writeback_packet_path": relpath_str(paths["owner_packet"], root),
        "warnings": warnings,
    }

    export_payload = {
        "contract_id": export_contract.get("contract_id", OWNER_WRITEBACK_EXPORT_CONTRACT_ID),
        "version": export_contract.get("version", OWNER_WRITEBACK_EXPORT_VERSION),
        "generated_at_utc": generated_at,
        "scope": export_contract.get("scope", "SellerSprite owner writeback externalized export"),
        "stage_status_path": relpath_str(paths["latest_status"], root),
        "truth_pack_path": relpath_str(paths["truth_pack"], root),
        "owner_handoff_contract_path": relpath_str(paths["owner_handoff_contract"], root),
        "owner_writeback_packet_path": relpath_str(paths["owner_packet"], root),
        "owner_handoff_json_path": relpath_str(paths["latest_owner_handoff"], root),
        "owner_writeback_export_path": relpath_str(paths["latest_owner_writeback_export"], root),
        "business_promotion_boundary": OWNER_WRITEBACK_BOUNDARY,
        "current_stage_closure_status": evaluation["current_legal_wording"].get("current_stage_closure_status"),
        "overall_repo_wording": evaluation["current_legal_wording"].get("overall_repo_wording"),
        "current_stage_closed": bool(evaluation["signals"]["current_stage_closed"]),
        "next_stage_required": bool(evaluation["signals"]["next_stage_required"]),
        "eligible_candidate_count": len(candidate_rows),
        "eligible_candidate_ids": [row["candidate_id"] for row in candidate_rows],
        "eligible_candidate_paths": candidate_rows,
        "required_owner_side_fields": owner_contract.get("required_owner_side_fields", []),
        "next_stage_reason_codes": handoff["next_stage_reason_codes"],
        "why_next_stage_starts": handoff["why_next_stage_starts"],
        "warnings": warnings,
    }

    required_fields = export_contract.get("required_export_fields", [])
    missing_fields = [field for field in required_fields if field not in export_payload]
    if missing_fields:
        raise ValueError(f"Owner writeback export is missing required fields: {', '.join(missing_fields)}")

    return {
        "candidate_rows": candidate_rows,
        "handoff": handoff,
        "export_payload": export_payload,
    }


def write_owner_writeback_bundle(bundle: dict[str, Any], repo_root: Path | None = None) -> list[str]:
    root = find_repo_root(repo_root)
    paths = repo_paths(root)
    owner_contract = read_json(paths["owner_handoff_contract"])
    candidate_rows = bundle["candidate_rows"]
    if candidate_rows:
        write_csv_rows(paths["owner_packet"], candidate_rows)
    else:
        write_csv_rows(paths["owner_packet"], [{field: "" for field in owner_contract["packet_columns"]}])
    write_json(paths["latest_owner_handoff"], bundle["handoff"])
    write_json(paths["latest_owner_writeback_export"], bundle["export_payload"])
    write_text(paths["owner_handoff_summary"], render_owner_writeback_summary(bundle["handoff"], bundle["export_payload"]))
    return [
        relpath_str(paths["owner_packet"], root),
        relpath_str(paths["latest_owner_handoff"], root),
        relpath_str(paths["latest_owner_writeback_export"], root),
        relpath_str(paths["owner_handoff_summary"], root),
    ]


def validate_truth_pack(truth_pack: dict[str, Any], contract: dict[str, Any], owner_contract: dict[str, Any], paths: dict[str, Path], repo_root: Path) -> bool:
    board_path_mapping = truth_pack.get("board_path_mapping", {})
    required_path_matches = {
        "board_csv": board_path_mapping.get("board_csv") == relpath_str(paths["board"], repo_root),
        "debt_register_csv": board_path_mapping.get("debt_register_csv") == relpath_str(paths["debt_register"], repo_root),
        "owner_packet_csv": board_path_mapping.get("owner_packet_csv") == relpath_str(paths["owner_packet"], repo_root),
        "stage_status_json": board_path_mapping.get("stage_status_json") == relpath_str(paths["latest_status"], repo_root),
        "owner_handoff_json": board_path_mapping.get("owner_handoff_json") == relpath_str(paths["latest_owner_handoff"], repo_root),
    }
    return all(required_path_matches.values()) and all(
        [
            truth_pack.get("current_stage_closure_contract_version") == contract.get("version"),
            truth_pack.get("owner_handoff_contract_version") == owner_contract.get("version"),
            truth_pack.get("artifact_evidence_mode") == "truth_pack",
            truth_pack.get("current_legal_wording", {}).get("current_stage_closure_status") == contract["current_stage_closure"]["status"],
            truth_pack.get("current_legal_wording", {}).get("current_stage_statement") == contract["current_stage_closure"]["canonical_statement"],
        ]
    )


def validate_owner_handoff_contract(owner_contract: dict[str, Any], truth_pack: dict[str, Any]) -> bool:
    truth_pack_schema = truth_pack.get("owner_handoff_field_schema", {})
    return all(
        [
            owner_contract.get("version") == truth_pack.get("owner_handoff_contract_version"),
            owner_contract.get("packet_columns") == truth_pack_schema.get("packet_columns"),
            canonical_json(owner_contract.get("required_owner_side_fields", [])) == canonical_json(truth_pack_schema.get("required_owner_side_fields", [])),
        ]
    )


def evaluate_stage_status(repo_root: Path | None = None) -> dict[str, Any]:
    root = find_repo_root(repo_root)
    paths = repo_paths(root)
    board_rows = read_csv_rows(paths["board"])
    board_index = build_board_index(board_rows)
    contract = read_json(paths["contract"])
    owner_handoff_contract = read_json(paths["owner_handoff_contract"])
    truth_pack = read_json(paths["truth_pack"])
    debt_rows = read_csv_rows(paths["debt_register"])
    owner_packet_header = read_csv_header(paths["owner_packet"]) if paths["owner_packet"].exists() else []

    artifact_evidence = build_artifact_evidence_from_truth_pack(truth_pack, paths["truth_pack"], root)
    line_rows = [board_index[phase_id] for phase_id in ("P1", "P2", "P3", "P4")]

    flow_closed = (
        contract["current_stage_closure"]["status"] == "FLOW_CLOSED"
        and truth_pack.get("current_legal_wording", {}).get("current_stage_closure_status") == "FLOW_CLOSED"
        and all(row["flow_closure_status"] == "FLOW_CLOSED" for row in line_rows)
    )
    artifact_depth_reconciled = bool(truth_pack.get("signals", {}).get("artifact_depth_reconciled")) and artifact_evidence["coverage_complete"]
    hardening_debt_blocking = any(
        row["line_id"] == "P0" and (row["is_current_stage_blocker"] or "").strip().upper() == "YES" for row in debt_rows
    )
    post_stage_open_debt_present = any(
        row["debt_class"] == "POST_STAGE_OPEN_DEBT" and row["current_state"] == "OPEN" for row in debt_rows
    )
    current_stage_closed = (
        flow_closed
        and artifact_depth_reconciled
        and not hardening_debt_blocking
        and contract["current_stage_blocker"]["status"] == "NONE"
    )
    next_stage_required = current_stage_closed and bool(truth_pack.get("next_stage_required"))

    evaluation: dict[str, Any] = {
        "generated_at_utc": utc_now_iso(),
        "repo_root": root.as_posix(),
        "paths": {key: relpath_str(value, root) for key, value in paths.items() if key != "repo_root"},
        "truth_priority": truth_pack.get("artifact_truth_priority", []),
        "signals": {
            "flow_closed": flow_closed,
            "artifact_depth_reconciled": artifact_depth_reconciled,
            "hardening_debt_blocking": hardening_debt_blocking,
            "post_stage_open_debt_present": post_stage_open_debt_present,
            "current_stage_closed": current_stage_closed,
            "next_stage_required": next_stage_required,
        },
        "current_stage_blocker": {
            "status": contract["current_stage_blocker"]["status"],
            "superseded_blocker": contract["current_stage_blocker"].get("superseded_blocker"),
            "reason": contract["current_stage_blocker"].get("reason"),
        },
        "current_legal_wording": truth_pack.get("current_legal_wording", {}),
        "reason_enums": truth_pack.get("reason_enums", {}),
        "artifacts": artifact_evidence,
        "contract": {
            "current_stage_closure_status": contract["current_stage_closure"]["status"],
            "gated_by_business_promotion": contract["current_stage_closure"]["gated_by_business_promotion"],
            "business_promotion_layer": contract["business_promotion"]["layer"],
        },
        "owner_handoff_contract": {
            "version": owner_handoff_contract.get("version"),
            "packet_columns": owner_handoff_contract.get("packet_columns", []),
            "candidate_source_modes": owner_handoff_contract.get("candidate_source_modes", []),
        },
        "board": {
            "path": relpath_str(paths["board"], root),
            "rows": board_rows,
        },
    }

    phase_updates = build_phase_row_updates(evaluation, truth_pack)
    canonical_rows = apply_phase_row_updates(board_rows, phase_updates)
    expected_readme = render_readme(evaluation, canonical_rows, root)
    expected_registry = render_registry(evaluation, canonical_rows)
    actual_readme = read_text_best_effort(paths["readme"]) if paths["readme"].exists() else ""
    actual_registry = read_text_best_effort(paths["registry"]) if paths["registry"].exists() else ""

    readme_aligned = normalize_multiline_text(actual_readme) == normalize_multiline_text(expected_readme)
    registry_aligned = normalize_multiline_text(actual_registry) == normalize_multiline_text(expected_registry)
    board_aligned = canonical_json(board_rows) == canonical_json(canonical_rows)
    contract_aligned = (
        contract["current_stage_closure"]["status"] == "FLOW_CLOSED"
        and contract["current_stage_closure"]["gated_by_business_promotion"] is False
        and contract["current_stage_blocker"]["status"] == "NONE"
        and contract["current_stage_closure"]["canonical_statement"] == truth_pack.get("current_legal_wording", {}).get("current_stage_statement")
    )
    truth_pack_aligned = validate_truth_pack(truth_pack, contract, owner_handoff_contract, paths, root)
    owner_handoff_contract_aligned = validate_owner_handoff_contract(owner_handoff_contract, truth_pack)
    owner_template_aligned = owner_packet_header == owner_handoff_contract.get("packet_columns", [])

    warnings: list[str] = []
    if artifact_evidence["source_mode"] == "summary_extract":
        warnings.append("Artifact evidence unexpectedly fell back to summary_extract; truth pack input is not being honored.")
    if artifact_evidence["source_mode"] != "truth_pack":
        warnings.append(f"Artifact evidence mode is `{artifact_evidence['source_mode']}`, expected `truth_pack`.")
    if not truth_pack_aligned:
        warnings.append("reports/sellersprite_truth_pack_current.json is missing one or more required canonical fields or path mappings.")
    if not owner_handoff_contract_aligned:
        warnings.append("contracts/sellersprite_owner_handoff_contract_v1.json is out of sync with the truth-pack owner handoff schema.")
    if not owner_template_aligned:
        warnings.append("Owner manual writeback packet header is out of sync with the owner handoff contract.")
    if not readme_aligned:
        warnings.append("README.md is not aligned with the deterministic current-state render.")
    if not registry_aligned:
        warnings.append("skill_sellersprite_four_line_runtime_registry.md is not aligned with the deterministic current-state render.")

    evaluation["host_alignment"] = {
        "readme_aligned": readme_aligned,
        "registry_aligned": registry_aligned,
        "board_aligned": board_aligned,
        "contract_aligned": contract_aligned,
        "truth_pack_aligned": truth_pack_aligned,
        "owner_handoff_contract_aligned": owner_handoff_contract_aligned,
        "owner_template_aligned": owner_template_aligned,
        "all_required_hosts_aligned": all(
            [
                readme_aligned,
                registry_aligned,
                board_aligned,
                contract_aligned,
                truth_pack_aligned,
                owner_handoff_contract_aligned,
                owner_template_aligned,
            ]
        ),
    }
    evaluation["warnings"] = warnings
    evaluation["current_stage_reason_codes"] = truth_pack.get("reason_enums", {}).get("current_stage_closed", []) if current_stage_closed else []
    evaluation["current_stage_reason"] = build_reason_messages(truth_pack.get("reason_enums", {}), "current_stage_closed") if current_stage_closed else []
    evaluation["next_stage_reason_codes"] = truth_pack.get("reason_enums", {}).get("next_stage_required", []) if next_stage_required else []
    evaluation["next_stage_reason"] = build_reason_messages(truth_pack.get("reason_enums", {}), "next_stage_required") if next_stage_required else []
    return evaluation


def reconcile_truth_hosts(evaluation: dict[str, Any], repo_root: Path | None = None) -> dict[str, Any]:
    root = find_repo_root(repo_root)
    paths = repo_paths(root)
    truth_pack = read_json(paths["truth_pack"])
    board_rows = evaluation["board"]["rows"]
    phase_updates = build_phase_row_updates(evaluation, truth_pack)
    canonical_rows = apply_phase_row_updates(board_rows, phase_updates)
    return {
        "generated_at_utc": utc_now_iso(),
        "repo_root": root.as_posix(),
        "truth_priority_applied": evaluation["truth_priority"],
        "canonical_board_rows": canonical_rows,
        "host_payload": {
            "readme_path": relpath_str(paths["readme"], root),
            "board_path": relpath_str(paths["board"], root),
            "registry_path": relpath_str(paths["registry"], root),
            "readme_content": render_readme(evaluation, canonical_rows, root),
            "registry_content": render_registry(evaluation, canonical_rows),
        },
    }


def write_current_state(reconciled: dict[str, Any], repo_root: Path | None = None) -> list[str]:
    root = find_repo_root(repo_root)
    paths = repo_paths(root)
    payload = reconciled["host_payload"]
    write_text(paths["readme"], payload["readme_content"])
    write_csv_rows(paths["board"], reconciled["canonical_board_rows"])
    write_text(paths["registry"], payload["registry_content"])
    return [
        relpath_str(paths["readme"], root),
        relpath_str(paths["board"], root),
        relpath_str(paths["registry"], root),
    ]


def render_implementation_summary(final_result: dict[str, Any], repo_root: Path | None = None) -> str:
    root = find_repo_root(repo_root)
    post_eval = final_result["evaluation_after_write"]
    signals = post_eval["signals"]
    written_files = final_result["written_files"]
    owner_writeback_written_files = final_result.get("owner_writeback_written_files", [])
    consistency = final_result.get("consistency_check", {})
    artifact_mode = post_eval["artifacts"]["source_mode"]
    warning_lines = "\n".join(f"- {warning}" for warning in post_eval["warnings"]) or "- none"
    written_lines = "\n".join(f"- `{item}`" for item in [*written_files, *owner_writeback_written_files])
    truth_pack_path = post_eval["paths"]["truth_pack"]
    return f"""# CODEX Implement Deterministic Py Stage Evaluator Summary ({TASK_DATE})

## Scope

- Added a pure-py current-stage evaluation chain for SellerSprite stage closure.
- No T02/T03/T04 runtime was reopened.
- The active evaluator now reads a machine-readable truth pack instead of parsing markdown summaries.

## Current Run Result

- `flow_closed = {str(signals["flow_closed"]).lower()}`
- `artifact_depth_reconciled = {str(signals["artifact_depth_reconciled"]).lower()}`
- `hardening_debt_blocking = {str(signals["hardening_debt_blocking"]).lower()}`
- `post_stage_open_debt_present = {str(signals["post_stage_open_debt_present"]).lower()}`
- `current_stage_closed = {str(signals["current_stage_closed"]).lower()}`
- `next_stage_required = {str(signals["next_stage_required"]).lower()}`
- artifact evidence mode = `{artifact_mode}`
- truth pack host = `{truth_pack_path}`

## Files Written

{written_lines}
- `reports/latest_sellersprite_stage_status.json`

## Consistency Check

- `truth_pack_to_render_consistent = {str(consistency.get("truth_pack_to_render_consistent", False)).lower()}`
- `readme_render_aligned = {str(consistency.get("readme_render_aligned", False)).lower()}`
- `board_render_aligned = {str(consistency.get("board_render_aligned", False)).lower()}`
- `owner_template_aligned = {str(consistency.get("owner_template_aligned", False)).lower()}`
- `owner_writeback_boundary_preserved = {str(consistency.get("owner_writeback_boundary_preserved", False)).lower()}`

## Warnings

{warning_lines}

## Path Note

- The physical progress-board host in this workspace is `{relpath_str(repo_paths(root)["board"], root)}`.
"""
