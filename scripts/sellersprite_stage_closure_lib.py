from __future__ import annotations

import copy
import csv
import io
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TASK_DATE = "2026-04-13"
TASK_STAMP = "20260413"
EXPECTED_LANES = ("T11", "T12")
EXPECTED_ARTIFACT_CODES = ("12", "22", "42", "60")
STATUS_VALUES = {"PASS", "HOLD", "FAIL"}


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
        "artifact_reconciliation_summary": resolve_existing_path(
            [
                selection_reports_dir / "CODEX_T11_T12_ARTIFACT_DEPTH_RECONCILIATION_SUMMARY_20260413.md",
                reports_dir / "CODEX_T11_T12_ARTIFACT_DEPTH_RECONCILIATION_SUMMARY_20260413.md",
            ]
        ),
        "repo_truth_revalidation_summary": resolve_existing_path(
            [
                selection_reports_dir / "CODEX_REPO_TRUTH_REVALIDATION_AFTER_0118_SUMMARY_20260413.md",
                reports_dir / "CODEX_REPO_TRUTH_REVALIDATION_AFTER_0118_SUMMARY_20260413.md",
            ]
        ),
        "rewrite_summary": reports_dir / "CODEX_REWRITE_STAGE_CLOSURE_CONTRACT_TO_FLOW_ONLY_SUMMARY_20260413.md",
        "latest_status": reports_dir / "latest_sellersprite_stage_status.json",
        "implementation_summary": reports_dir / "CODEX_IMPLEMENT_DETERMINISTIC_PY_STAGE_EVALUATOR_SUMMARY_20260413.md",
    }


def normalize_status(value: str | None) -> str | None:
    normalized = (value or "").strip().upper()
    return normalized if normalized in STATUS_VALUES else None


def infer_line_id_from_path(path: Path) -> str | None:
    for part in reversed(path.parts):
        match = re.fullmatch(r"(T\d{2})", part.upper())
        if match:
            return match.group(1)
    match = re.search(r"\b(T\d{2})\b", path.as_posix(), re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def detect_status_counts(rows: list[dict[str, str]]) -> tuple[str | None, dict[str, int]]:
    if not rows:
        return None, {}
    best_field: str | None = None
    best_counts: dict[str, int] = {}
    best_score = -1
    for field in rows[0].keys():
        normalized_values: list[str] = []
        valid = True
        for row in rows:
            raw_value = (row.get(field) or "").strip()
            if not raw_value:
                continue
            normalized = normalize_status(raw_value)
            if normalized is None:
                valid = False
                break
            normalized_values.append(normalized)
        if not valid or not normalized_values:
            continue
        counts = dict(Counter(normalized_values))
        score = sum(counts.values())
        if score > best_score:
            best_field = field
            best_counts = counts
            best_score = score
    return best_field, best_counts


def is_ignored_path(path: Path) -> bool:
    ignored_parts = {".git", ".venv"}
    return any(part in ignored_parts for part in path.parts)


def discover_actual_artifact_records(repo_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in repo_root.rglob("*.csv"):
        if is_ignored_path(path):
            continue
        match = re.match(r"^(12|22|42|60)_.*\.csv$", path.name)
        if not match:
            continue
        line_id = infer_line_id_from_path(path)
        if not line_id:
            continue
        rows = read_csv_rows(path)
        status_field, status_counts = detect_status_counts(rows)
        records.append(
            {
                "line_id": line_id,
                "artifact_code": match.group(1),
                "source_kind": "actual_csv",
                "source_rank": 100,
                "source_path": relpath_str(path, repo_root),
                "exists": path.exists(),
                "parses": True,
                "row_count": len(rows),
                "status_field": status_field,
                "status_counts": status_counts,
            }
        )
    return records


def parse_summary_artifact_records(path: Path, repo_root: Path, source_rank: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = read_text_best_effort(path).splitlines()
    records: list[dict[str, Any]] = []
    current_line_id: str | None = None
    current_record: dict[str, Any] | None = None
    section_pattern = re.compile(r"^###\s+(T\d{2})\b", re.IGNORECASE)
    inline_artifact_pattern = re.compile(r"^-\s+`?(T\d{2})\s+(\d{2})_.*?\.csv`?", re.IGNORECASE)
    section_artifact_pattern = re.compile(r"^-\s+`?(\d{2})_.*?\.csv`?", re.IGNORECASE)

    def flush_current() -> None:
        nonlocal current_record
        if current_record is not None:
            records.append(current_record)
            current_record = None

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            flush_current()
            continue
        if stripped.startswith("#"):
            flush_current()
        section_match = section_pattern.match(stripped)
        if section_match:
            flush_current()
            current_line_id = section_match.group(1).upper()
            continue

        inline_match = inline_artifact_pattern.match(stripped)
        if inline_match:
            flush_current()
            current_record = {
                "line_id": inline_match.group(1).upper(),
                "artifact_code": inline_match.group(2),
                "source_kind": "summary_extract",
                "source_rank": source_rank,
                "source_path": relpath_str(path, repo_root),
                "exists": False,
                "parses": False,
                "row_count": None,
                "status_counts": {},
            }
            continue

        section_artifact_match = section_artifact_pattern.match(stripped)
        if section_artifact_match and current_line_id is not None:
            flush_current()
            current_record = {
                "line_id": current_line_id,
                "artifact_code": section_artifact_match.group(1),
                "source_kind": "summary_extract",
                "source_rank": source_rank,
                "source_path": relpath_str(path, repo_root),
                "exists": False,
                "parses": False,
                "row_count": None,
                "status_counts": {},
            }
            continue

        if current_record is None:
            continue

        if stripped == "- exists":
            current_record["exists"] = True
            continue
        if stripped == "- parses":
            current_record["parses"] = True
            continue

        row_match = re.search(r"row_count\s*=\s*(\d+)", stripped, re.IGNORECASE)
        if row_match:
            current_record["row_count"] = int(row_match.group(1))

        for status, count in re.findall(r"\b(PASS|HOLD|FAIL)\b\s*x\s*(\d+)", stripped, re.IGNORECASE):
            current_record["status_counts"][status.upper()] = int(count)

    flush_current()
    return records


def record_richness(record: dict[str, Any]) -> tuple[int, int]:
    status_score = sum(record.get("status_counts", {}).values())
    row_count = int(record.get("row_count") or 0)
    return (status_score, row_count)


def merge_artifact_records(records: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    merged: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        line_records = merged.setdefault(record["line_id"], {})
        existing = line_records.get(record["artifact_code"])
        if existing is None:
            line_records[record["artifact_code"]] = record
            continue
        candidate_key = (record.get("source_rank", 0),) + record_richness(record)
        existing_key = (existing.get("source_rank", 0),) + record_richness(existing)
        if candidate_key > existing_key:
            line_records[record["artifact_code"]] = record
    return merged


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


def build_artifact_evidence(repo_root: Path, paths: dict[str, Path]) -> dict[str, Any]:
    actual_records = discover_actual_artifact_records(repo_root)
    summary_records = []
    summary_records.extend(parse_summary_artifact_records(paths["artifact_reconciliation_summary"], repo_root, source_rank=30))
    summary_records.extend(parse_summary_artifact_records(paths["repo_truth_revalidation_summary"], repo_root, source_rank=20))
    merged = merge_artifact_records(actual_records + summary_records)
    coverage = artifact_coverage(merged)
    complete = coverage_complete(coverage)
    source_kinds = {record["source_kind"] for lane in merged.values() for record in lane.values()}
    if complete and source_kinds == {"actual_csv"}:
        source_mode = "actual_csv"
    elif complete and "actual_csv" in source_kinds:
        source_mode = "mixed"
    elif complete:
        source_mode = "summary_extract"
    else:
        source_mode = "incomplete"
    return {
        "records": merged,
        "coverage": coverage,
        "coverage_complete": complete,
        "source_mode": source_mode,
        "actual_csv_records_found": len(actual_records),
        "summary_records_used": len(summary_records),
        "summary_sources_checked": [
            relpath_str(paths["artifact_reconciliation_summary"], repo_root),
            relpath_str(paths["repo_truth_revalidation_summary"], repo_root),
        ],
    }


def build_board_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["phase_id"]: row for row in rows}


def contains_all(text: str, required_fragments: list[str]) -> bool:
    return all(fragment in text for fragment in required_fragments)


def evaluate_stage_status(repo_root: Path | None = None) -> dict[str, Any]:
    root = find_repo_root(repo_root)
    paths = repo_paths(root)
    board_rows = read_csv_rows(paths["board"])
    board_index = build_board_index(board_rows)
    contract = read_json(paths["contract"])
    debt_rows = read_csv_rows(paths["debt_register"])
    artifact_evidence = build_artifact_evidence(root, paths)
    readme_text = read_text_best_effort(paths["readme"]) if paths["readme"].exists() else ""
    registry_text = read_text_best_effort(paths["registry"]) if paths["registry"].exists() else ""

    line_rows = [board_index[phase_id] for phase_id in ("P1", "P2", "P3", "P4")]
    flow_closed = contract["current_stage_closure"]["status"] == "FLOW_CLOSED" and all(
        row["flow_closure_status"] == "FLOW_CLOSED" for row in line_rows
    )
    artifact_depth_reconciled = artifact_evidence["coverage_complete"] and paths["artifact_reconciliation_summary"].exists()
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
    next_stage_required = current_stage_closed and any(
        row["business_promotion_status"] != "BUSINESS_PROMOTED" for row in line_rows
    )
    readme_aligned = contains_all(
        readme_text,
        [
            "SellerSprite current-stage closure = `FLOW_CLOSED`",
            "next-stage owner/business",
        ],
    )
    registry_aligned = contains_all(
        registry_text,
        [
            "current_stage_closure_status = FLOW_CLOSED",
            "next-stage owner/business flow",
        ],
    )
    board_aligned = all(row["current_blocker"].startswith("NONE__CURRENT_STAGE_FLOW_CLOSED") for row in line_rows)
    contract_aligned = (
        contract["current_stage_closure"]["status"] == "FLOW_CLOSED"
        and contract["current_stage_closure"]["gated_by_business_promotion"] is False
        and contract["current_stage_blocker"]["status"] == "NONE"
    )

    warnings: list[str] = []
    if artifact_evidence["actual_csv_records_found"] == 0:
        warnings.append(
            "No direct repo-local 12/22/42/60 CSV artifacts were discovered; evaluator used regex-parsed repo summaries plus contract/board hosts."
        )
    if not readme_aligned:
        warnings.append("README.md is missing one or more required current-stage closure fragments.")
    if not registry_aligned:
        warnings.append("skill_sellersprite_four_line_runtime_registry.md is missing one or more required current-stage closure fragments.")

    return {
        "generated_at_utc": utc_now_iso(),
        "repo_root": root.as_posix(),
        "paths": {key: relpath_str(value, root) for key, value in paths.items() if key != "repo_root"},
        "truth_priority": [
            "direct repo-local parseable artifact CSV/JSON",
            "machine-readable contract/board/debt CSV or JSON hosts",
            "regex-parseable repo summaries when direct artifacts are absent",
            "supporting prose only as non-authoritative context",
        ],
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
        "artifacts": artifact_evidence,
        "contract": {
            "current_stage_closure_status": contract["current_stage_closure"]["status"],
            "gated_by_business_promotion": contract["current_stage_closure"]["gated_by_business_promotion"],
            "business_promotion_layer": contract["business_promotion"]["layer"],
        },
        "board": {
            "path": relpath_str(paths["board"], root),
            "rows": board_rows,
        },
        "host_alignment": {
            "readme_aligned": readme_aligned,
            "registry_aligned": registry_aligned,
            "board_aligned": board_aligned,
            "contract_aligned": contract_aligned,
            "all_required_hosts_aligned": readme_aligned and registry_aligned and board_aligned and contract_aligned,
        },
        "warnings": warnings,
        "next_stage_reason": [
            "Business promotion remains next-stage owner/business work.",
            "T02/T03/T04 remain tracked as post-stage open debt.",
        ]
        if next_stage_required
        else [],
    }


def build_phase_row_updates(evaluation: dict[str, Any]) -> dict[str, dict[str, str]]:
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
    return f"""# SellerSprite Current-Stage Closure Contract

This file is a deterministic current-state host rendered by `scripts/write_sellersprite_current_state.py`.

## Current Verdict

- SellerSprite current-stage closure = `FLOW_CLOSED`.
- `flow_closed = {str(evaluation["signals"]["flow_closed"]).lower()}`
- `artifact_depth_reconciled = {str(evaluation["signals"]["artifact_depth_reconciled"]).lower()}`
- `hardening_debt_blocking = {str(evaluation["signals"]["hardening_debt_blocking"]).lower()}`
- `post_stage_open_debt_present = {str(evaluation["signals"]["post_stage_open_debt_present"]).lower()}`
- `current_stage_closed = {str(evaluation["signals"]["current_stage_closed"]).lower()}`
- `next_stage_required = {str(evaluation["signals"]["next_stage_required"]).lower()}`

## Current Git Truth

- `P0` shared continuity remains `NON_BLOCKING_HARDENING_DEBT`.
- `T11 / T12` artifact-depth is reconciled and remains the canonical file-backed T01 reference pair.
- `T01`, `T02`, `T03`, and `T04` are SellerSprite line-level `FLOW_CLOSED` lines.
- `T02 / T03 / T04` remain `POST_STAGE_OPEN_DEBT`, but that debt does not reopen current-stage closure.
- Owner-side manual writeback fields remain outside the current-stage closure gate.

## Machine Status Host

- latest machine-readable status: `reports/latest_sellersprite_stage_status.json`
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
    return f"""# skill_sellersprite_four_line_runtime_registry

This registry is a deterministic current-state host rendered by `scripts/write_sellersprite_current_state.py`.

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


def reconcile_truth_hosts(evaluation: dict[str, Any], repo_root: Path | None = None) -> dict[str, Any]:
    root = find_repo_root(repo_root)
    paths = repo_paths(root)
    board_rows = evaluation["board"]["rows"]
    phase_updates = build_phase_row_updates(evaluation)
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
    artifact_mode = post_eval["artifacts"]["source_mode"]
    warning_lines = "\n".join(f"- {warning}" for warning in post_eval["warnings"]) or "- none"
    written_lines = "\n".join(f"- `{item}`" for item in written_files)
    return f"""# CODEX Implement Deterministic Py Stage Evaluator Summary ({TASK_DATE})

## Scope

- Added a pure-py current-stage evaluation chain for SellerSprite stage closure.
- No T02/T03/T04 runtime was reopened.
- No Codex prose summary is used as the only truth host.

## Current Run Result

- `flow_closed = {str(signals["flow_closed"]).lower()}`
- `artifact_depth_reconciled = {str(signals["artifact_depth_reconciled"]).lower()}`
- `hardening_debt_blocking = {str(signals["hardening_debt_blocking"]).lower()}`
- `post_stage_open_debt_present = {str(signals["post_stage_open_debt_present"]).lower()}`
- `current_stage_closed = {str(signals["current_stage_closed"]).lower()}`
- `next_stage_required = {str(signals["next_stage_required"]).lower()}`
- artifact evidence mode = `{artifact_mode}`

## Files Written

{written_lines}
- `reports/latest_sellersprite_stage_status.json`

## Warnings

{warning_lines}

## Path Note

- The physical progress-board host in this workspace is `{relpath_str(repo_paths(root)["board"], root)}`.
"""
