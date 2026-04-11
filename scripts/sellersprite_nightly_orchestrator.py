from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from benchmark_chain_common import BenchmarkContext, ensure_within_repo, resolve_context_from_namespace
from keyword_chain_common import ROOT, append_jsonl, iso_now, write_json_atomic
from sellersprite_route_router import PRODUCT_IDEA_VALIDATION, resolve_route_decision, route_sequence


LATEST_STATE = "latest_nightly_state.json"
RUN_HISTORY = "nightly_runs.jsonl"
TERMINAL_STATUSES = {"PASS", "HOLD", "SOURCE_EMPTY", "FALLBACK_NEXT", "BLOCKED"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the resilient SellerSprite nightly state machine with route-aware fallbacks.")
    parser.add_argument("--context-row-index", type=int, default=1)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--direction-id", default=None)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--category-hint", default=None)
    parser.add_argument("--site", default=None)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--sample-top-n", type=int, default=None)
    parser.add_argument("--max-candidate-samples", type=int, default=None)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--log-dir", required=True)
    parser.add_argument("--download-root", default=None)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--execution-mode", choices=("auto", "persistent", "storage_state"), default="auto")
    return parser.parse_args()


def repo_path(raw_path: str, label: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return ensure_within_repo(path, label)


def step_state_path(log_dir: Path, step_key: str) -> Path:
    return ensure_within_repo(log_dir / f"latest_{step_key}_state.json", f"{step_key}_state_path")


def persist_state(log_dir: Path, state: dict[str, Any], final: bool = False) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(log_dir / LATEST_STATE, state)
    if final:
        append_jsonl(log_dir / RUN_HISTORY, state)


def persist_step_state(log_dir: Path, step_key: str, payload: dict[str, Any]) -> None:
    write_json_atomic(step_state_path(log_dir, step_key), payload)


def load_existing_state(log_dir: Path) -> dict[str, Any] | None:
    state_path = log_dir / LATEST_STATE
    if not state_path.exists():
        return None
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def compatible_resume_state(existing: dict[str, Any] | None, context: BenchmarkContext, output_dir: Path) -> dict[str, Any] | None:
    if not existing:
        return None
    existing_context = existing.get("context", {})
    if not isinstance(existing_context, dict):
        return None
    if str(existing_context.get("keyword", "")).strip() != context.keyword:
        return None
    if str(existing_context.get("site", "")).strip().upper() != context.site:
        return None
    if str(existing.get("output_dir", "")).strip() != str(output_dir):
        return None
    return existing


def should_skip_step(state: dict[str, Any], step_key: str) -> bool:
    steps = state.get("steps", {})
    if not isinstance(steps, dict):
        return False
    payload = steps.get(step_key, {})
    if not isinstance(payload, dict):
        return False
    if str(payload.get("status", "")).strip().upper() not in TERMINAL_STATUSES:
        return False
    summary_path = str(payload.get("summary_path", "")).strip()
    if summary_path:
        summary_file = Path(summary_path)
        if not summary_file.exists():
            return False
    return True


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def auth_meta_from_summary(summary: dict[str, Any]) -> dict[str, Any]:
    auth_incident_path = str(summary.get("auth_incident_path", "")).strip()
    auth_replay_attempted = bool(summary.get("auth_replay_attempted"))
    auth_replay_result = summary.get("auth_replay_result", {})
    if not auth_incident_path and not auth_replay_attempted:
        return {}
    return {
        "auth_incident_path": auth_incident_path,
        "auth_surface_family": str(summary.get("auth_surface_family", "")).strip(),
        "auth_replay_available": bool(summary.get("auth_replay_available")),
        "auth_replay_snippet_path": str(summary.get("auth_replay_snippet_path", "")).strip(),
        "auth_owner_recording_drop_path": str(summary.get("auth_owner_recording_drop_path", "")).strip(),
        "auth_replay_attempted": auth_replay_attempted,
        "auth_replay_status": str(auth_replay_result.get("status", "")).strip(),
        "auth_replay_reason_code": str(auth_replay_result.get("reason_code", "")).strip(),
    }


def summarize_output(text: str, max_chars: int = 2000) -> str:
    compact = str(text or "").strip()
    if len(compact) <= max_chars:
        return compact
    return compact[-max_chars:]


def run_command(command: list[str], workdir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(workdir),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="backslashreplace",
        check=False,
    )


def csv_has_pass_rows(path: Path) -> bool:
    if not path.exists():
        return False
    rows = list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))
    return any(str(row.get("整体状态", "")).strip().upper() == "PASS" for row in rows)


def update_step(state: dict[str, Any], log_dir: Path, step_key: str, payload: dict[str, Any]) -> None:
    state.setdefault("steps", {})[step_key] = payload
    state["last_updated_at"] = iso_now()
    persist_step_state(log_dir, step_key, payload)
    persist_state(log_dir, state, final=False)


def route_step(context: BenchmarkContext, log_dir: Path) -> dict[str, Any]:
    payload = resolve_route_decision(
        context_row_index=context.context_row_index,
        run_name=context.run_name,
        direction_id=context.direction_id,
        keyword=context.keyword,
        site=context.site,
    )
    payload["summary_path"] = str(step_state_path(log_dir, "route"))
    return payload


def step1_product(context: BenchmarkContext, output_dir: Path, log_dir: Path, execution_mode: str) -> dict[str, Any]:
    export_log_dir = ensure_within_repo(log_dir / "step1_product_export", "step1_product_export_log")
    build_log_dir = ensure_within_repo(log_dir / "step1_product_build", "step1_product_build_log")
    export_summary_path = export_log_dir / "latest_product_research_run.json"
    build_summary_path = build_log_dir / "latest_product_build_run.json"
    attempts: list[list[str]] = []
    return_codes: list[int] = []
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    export_summary: dict[str, Any] = {}
    build_summary: dict[str, Any] = {}
    status = "BLOCKED"

    for _attempt in range(1, 3):
        export_cmd = [
            sys.executable,
            "scripts/export_product_research.py",
            "--context-row-index",
            str(context.context_row_index),
            "--output-dir",
            str(output_dir),
            "--log-dir",
            str(export_log_dir),
            "--execution-mode",
            execution_mode,
        ]
        build_cmd = [
            sys.executable,
            "scripts/build_product_seed_pool.py",
            "--context-row-index",
            str(context.context_row_index),
            "--output-dir",
            str(output_dir),
            "--log-dir",
            str(build_log_dir),
            "--product-run",
            str(export_summary_path),
        ]
        export_result = run_command(export_cmd, ROOT)
        build_result = run_command(build_cmd, ROOT)
        attempts.extend([export_cmd, build_cmd])
        return_codes.extend([export_result.returncode, build_result.returncode])
        stdout_parts.extend([export_result.stdout, build_result.stdout])
        stderr_parts.extend([export_result.stderr, build_result.stderr])
        export_summary = read_json(export_summary_path) if export_summary_path.exists() else {}
        build_summary = read_json(build_summary_path) if build_summary_path.exists() else {}
        if build_summary.get("status") == "PASS":
            status = "PASS"
            break

    return {
        "timestamp": iso_now(),
        "status": status,
        "reason_code": str(build_summary.get("reason_code", export_summary.get("reason_code", "STEP1_PRODUCT_BLOCKED"))).strip() or "STEP1_PRODUCT_BLOCKED",
        "message": str(build_summary.get("message", export_summary.get("message", ""))).strip(),
        "commands": attempts,
        "return_codes": return_codes,
        "stdout_tail": summarize_output("\n".join(stdout_parts)),
        "stderr_tail": summarize_output("\n".join(stderr_parts)),
        "summary_path": str(build_summary_path),
        "export_summary_path": str(export_summary_path),
        "raw_csv_path": str(output_dir / "10_产品样本原始结果.csv"),
        "seed_csv_path": str(output_dir / "11_产品样本种子池.csv"),
        "gate_csv_path": str(output_dir / "12_产品样本下推结果.csv"),
        "batch_id": str(build_summary.get("batch_id", "")),
        **auth_meta_from_summary(export_summary),
    }


def step4_benchmark(context: BenchmarkContext, output_dir: Path, log_dir: Path, download_root: Path, execution_mode: str, product_step: dict[str, Any]) -> dict[str, Any]:
    export_log_dir = ensure_within_repo(log_dir / "step4_benchmark_export", "step4_benchmark_export_log")
    build_log_dir = ensure_within_repo(log_dir / "step4_benchmark_build", "step4_benchmark_build_log")
    download_dir = ensure_within_repo(download_root / f"{context.keyword.replace(' ', '_')}_step4", "step4_download_dir")
    export_cmd = [
        sys.executable,
        "scripts/export_benchmark_competitors.py",
        "--context-row-index",
        str(context.context_row_index),
        "--output-dir",
        str(output_dir),
        "--log-dir",
        str(export_log_dir),
        "--download-dir",
        str(download_dir),
        "--execution-mode",
        execution_mode,
        "--product-gate-csv",
        str(product_step.get("gate_csv_path", "")),
        "--product-seed-csv",
        str(product_step.get("seed_csv_path", "")),
    ]
    build_cmd = [
        sys.executable,
        "scripts/build_benchmark_seed_pool.py",
        "--context-row-index",
        str(context.context_row_index),
        "--output-dir",
        str(output_dir),
        "--log-dir",
        str(build_log_dir),
        "--benchmark-run",
        str(export_log_dir / "latest_benchmark_export_run.json"),
    ]
    export_result = run_command(export_cmd, ROOT)
    build_result = run_command(build_cmd, ROOT)
    export_summary_path = export_log_dir / "latest_benchmark_export_run.json"
    build_summary_path = build_log_dir / "latest_benchmark_build_run.json"
    export_summary = read_json(export_summary_path) if export_summary_path.exists() else {}
    build_summary = read_json(build_summary_path) if build_summary_path.exists() else {}
    export_reason = str(export_summary.get("reason_code", "")).strip()
    if build_summary.get("status") == "PASS":
        status = "PASS"
    elif export_reason in {"BENCHMARK_RESULT_TABLE_NOT_VISIBLE", "BENCHMARK_RESULT_ROW_NOT_FOUND"} and str(product_step.get("status", "")) == "PASS":
        status = "FALLBACK_NEXT"
    else:
        status = "BLOCKED"
    return {
        "timestamp": iso_now(),
        "status": status,
        "reason_code": str(build_summary.get("reason_code", export_reason or "STEP4_BENCHMARK_BLOCKED")).strip() or "STEP4_BENCHMARK_BLOCKED",
        "message": str(build_summary.get("message", export_summary.get("message", ""))).strip(),
        "commands": [export_cmd, build_cmd],
        "return_codes": [export_result.returncode, build_result.returncode],
        "stdout_tail": summarize_output("\n".join([export_result.stdout, build_result.stdout])),
        "stderr_tail": summarize_output("\n".join([export_result.stderr, build_result.stderr])),
        "summary_path": str(build_summary_path),
        "export_summary_path": str(export_summary_path),
        "raw_csv_path": str(output_dir / "40_竞品基准结果.csv"),
        "seed_csv_path": str(output_dir / "41_候选产品种子池.csv"),
        "gate_csv_path": str(output_dir / "42_竞品基准下推结果.csv"),
        "batch_id": str(build_summary.get("batch_id", "")),
        **auth_meta_from_summary(export_summary),
    }


def step2_keyword(context: BenchmarkContext, output_dir: Path, log_dir: Path) -> dict[str, Any]:
    research_log_dir = ensure_within_repo(log_dir / "step2_keyword_research", "step2_keyword_research_log")
    trend_log_dir = ensure_within_repo(log_dir / "step2_keyword_trend", "step2_keyword_trend_log")
    build_log_dir = ensure_within_repo(log_dir / "step2_keyword_build", "step2_keyword_build_log")
    research_cmd = [
        sys.executable,
        "scripts/export_keyword_research.py",
        "--context-row-index",
        str(context.context_row_index),
        "--output-dir",
        str(output_dir),
        "--log-dir",
        str(research_log_dir),
        "--execution-mode",
        "storage_state",
    ]
    trend_cmd = [
        sys.executable,
        "scripts/export_keyword_trend.py",
        "--context-row-index",
        str(context.context_row_index),
        "--output-dir",
        str(output_dir),
        "--log-dir",
        str(trend_log_dir),
        "--execution-mode",
        "persistent",
    ]
    build_cmd = [
        sys.executable,
        "scripts/build_keyword_evidence_pool.py",
        "--context-row-index",
        str(context.context_row_index),
        "--output-dir",
        str(output_dir),
        "--log-dir",
        str(build_log_dir),
        "--keyword-research-run",
        str(research_log_dir / "latest_keyword_research_run.json"),
        "--keyword-trend-run",
        str(trend_log_dir / "latest_keyword_trend_run.json"),
    ]
    research_result = run_command(research_cmd, ROOT)
    trend_result = run_command(trend_cmd, ROOT)
    build_result = run_command(build_cmd, ROOT)
    research_summary_path = research_log_dir / "latest_keyword_research_run.json"
    trend_summary_path = trend_log_dir / "latest_keyword_trend_run.json"
    research_summary = read_json(research_summary_path) if research_summary_path.exists() else {}
    trend_summary = read_json(trend_summary_path) if trend_summary_path.exists() else {}
    build_summary_path = build_log_dir / "latest_keyword_build_run.json"
    build_summary = read_json(build_summary_path) if build_summary_path.exists() else {}
    gate_summary = build_summary.get("gate_summary", {}) if isinstance(build_summary.get("gate_summary", {}), dict) else {}
    if build_summary.get("status") != "PASS":
        status = "BLOCKED"
        reason_code = str(build_summary.get("reason_code", "STEP2_BUILD_BLOCKED")).strip() or "STEP2_BUILD_BLOCKED"
    elif int(gate_summary.get("PASS", 0) or 0) > 0:
        status = "PASS"
        reason_code = "PASS"
    else:
        status = "HOLD"
        reason_code = "STEP2_NO_PASS_GATE_ROWS"
    return {
        "timestamp": iso_now(),
        "status": status,
        "reason_code": reason_code,
        "message": str(build_summary.get("message", "")).strip(),
        "commands": [research_cmd, trend_cmd, build_cmd],
        "return_codes": [research_result.returncode, trend_result.returncode, build_result.returncode],
        "stdout_tail": summarize_output("\n".join([research_result.stdout, trend_result.stdout, build_result.stdout])),
        "stderr_tail": summarize_output("\n".join([research_result.stderr, trend_result.stderr, build_result.stderr])),
        "summary_path": str(build_summary_path),
        "raw_csv_path": str(output_dir / "20_关键词证据词池原始结果.csv"),
        "cleaned_csv_path": str(output_dir / "21_关键词证据词池清洗结果.csv"),
        "gate_csv_path": str(output_dir / "22_关键词证据词池下推结果.csv"),
        "gate_summary": gate_summary,
        "keyword_research_summary_path": str(research_summary_path),
        "keyword_trend_summary_path": str(trend_summary_path),
        **(auth_meta_from_summary(research_summary) or auth_meta_from_summary(trend_summary)),
    }


def step3_market(
    context: BenchmarkContext,
    output_dir: Path,
    log_dir: Path,
    purpose_type: str,
    step3_policy: str,
    product_step: dict[str, Any],
) -> dict[str, Any]:
    export_log_dir = ensure_within_repo(log_dir / "step3_market_export", "step3_market_export_log")
    export_cmd = [
        sys.executable,
        "scripts/export_market_report.py",
        "--context-row-index",
        str(context.context_row_index),
        "--output-dir",
        str(ROOT / "runs" / "manual" / "10_market"),
        "--log-dir",
        str(export_log_dir),
        "--max-attempts",
        "2",
    ]
    if purpose_type == PRODUCT_IDEA_VALIDATION:
        export_cmd.extend(["--entry-mode", "product_market_analysis"])
        product_seed_csv = str(product_step.get("seed_csv_path", "")).strip()
        if product_seed_csv:
            export_cmd.extend(["--product-seed-csv", product_seed_csv])
    else:
        export_cmd.extend(["--entry-mode", "keyword_search"])
    export_result = run_command(export_cmd, ROOT)
    export_summary_path = export_log_dir / "latest_run.json"
    export_summary = read_json(export_summary_path) if export_summary_path.exists() else {}
    failure_reason_code = str(export_summary.get("failure_reason_code", "")).strip()

    build_cmd: list[str] = []
    build_result: subprocess.CompletedProcess[str] | None = None
    if export_summary.get("status") == "SUCCESS":
        workbook_path = str(export_summary.get("raw_layer", {}).get("saved_workbook", "")).strip()
        build_cmd = [
            sys.executable,
            "scripts/build_market_workbook_index.py",
            "--context-row-index",
            str(context.context_row_index),
            "--output-dir",
            str(output_dir),
            "--market-workbook",
            workbook_path,
        ]
        build_result = run_command(build_cmd, ROOT)
        gate_path = output_dir / "32_市场调研下推结果.csv"
        if csv_has_pass_rows(gate_path):
            status = "PASS"
            reason_code = "PASS"
        else:
            status = "HOLD"
            reason_code = "STEP3_NO_PASS_GATE_ROWS"
    elif failure_reason_code == "MARKET_SOURCE_EMPTY":
        status = "SOURCE_EMPTY"
        reason_code = "MARKET_SOURCE_EMPTY"
    else:
        status = "BLOCKED"
        reason_code = failure_reason_code or "STEP3_MARKET_BLOCKED"

    stdout_parts = [export_result.stdout]
    stderr_parts = [export_result.stderr]
    return_codes = [export_result.returncode]
    if build_result is not None:
        stdout_parts.append(build_result.stdout)
        stderr_parts.append(build_result.stderr)
        return_codes.append(build_result.returncode)
    return {
        "timestamp": iso_now(),
        "status": status,
        "reason_code": reason_code,
        "message": str(export_summary.get("failure_reason", "") or "").strip(),
        "purpose_type": purpose_type,
        "step3_policy": step3_policy,
        "step3_required": step3_policy == "REQUIRED",
        "step3_optional_enrichment": step3_policy == "OPTIONAL",
        "entry_mode": "product_market_analysis" if purpose_type == PRODUCT_IDEA_VALIDATION else "keyword_search",
        "commands": [export_cmd] + ([build_cmd] if build_cmd else []),
        "return_codes": return_codes,
        "stdout_tail": summarize_output("\n".join(stdout_parts)),
        "stderr_tail": summarize_output("\n".join(stderr_parts)),
        "summary_path": str(export_summary_path),
        "raw_csv_path": str(output_dir / "30_市场调研原始索引.csv"),
        "cleaned_csv_path": str(output_dir / "31_市场调研清洗结果.csv"),
        "gate_csv_path": str(output_dir / "32_市场调研下推结果.csv"),
        "product_seed_csv": str(product_step.get("seed_csv_path", "")).strip(),
        **auth_meta_from_summary(export_summary),
    }


def step7_candidate_pool(output_dir: Path, log_dir: Path, state_path: Path) -> dict[str, Any]:
    candidate_log_dir = ensure_within_repo(log_dir / "step7_candidate_pool", "step7_candidate_pool_log")
    candidate_cmd = [
        sys.executable,
        "scripts/build_candidate_pool.py",
        "--nightly-state",
        str(state_path),
        "--output-dir",
        str(output_dir),
        "--log-dir",
        str(candidate_log_dir),
    ]
    result = run_command(candidate_cmd, ROOT)
    summary_path = candidate_log_dir / "latest_run.json"
    summary = read_json(summary_path) if summary_path.exists() else {}
    return {
        "timestamp": iso_now(),
        "status": str(summary.get("status", "BLOCKED")).strip() or "BLOCKED",
        "reason_code": str(summary.get("reason_code", "CANDIDATE_POOL_BLOCKED")).strip() or "CANDIDATE_POOL_BLOCKED",
        "message": "",
        "commands": [candidate_cmd],
        "return_codes": [result.returncode],
        "stdout_tail": summarize_output(result.stdout),
        "stderr_tail": summarize_output(result.stderr),
        "summary_path": str(summary_path),
        "final_csv_path": str(output_dir / "60_候选样品池.csv"),
        "intermediate_csv_path": str(output_dir / "03_候选市场与候选品初筛池.csv"),
    }


def main() -> int:
    args = parse_args()
    context = resolve_context_from_namespace(args, require_direction_id=False)
    output_dir = repo_path(args.output_dir, "nightly_output_dir")
    log_dir = repo_path(args.log_dir, "nightly_log_dir")
    download_root = repo_path(args.download_root, "nightly_download_root") if args.download_root else ensure_within_repo(ROOT / "runs" / "manual" / "nightly_downloads", "nightly_download_root")
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    download_root.mkdir(parents=True, exist_ok=True)

    existing_state = compatible_resume_state(load_existing_state(log_dir), context, output_dir) if args.resume else None
    state: dict[str, Any] = existing_state or {
        "timestamp": iso_now(),
        "module": "sellersprite_nightly_orchestrator",
        "status": "RUNNING",
        "reason_code": "",
        "message": "",
        "output_dir": str(output_dir),
        "log_dir": str(log_dir),
        "context": {
            "run_name": context.run_name,
            "direction_id": context.direction_id,
            "keyword": context.keyword,
            "site": context.site,
            "days": context.days,
            "context_row_index": context.context_row_index,
            "context_source": context.context_source,
        },
        "steps": {},
    }

    if not should_skip_step(state, "route"):
        route_payload = route_step(context, log_dir)
        update_step(state, log_dir, "route", route_payload)

    purpose_type = str(state["steps"]["route"].get("purpose_type", PRODUCT_IDEA_VALIDATION))
    step3_policy = str(state["steps"]["route"].get("step3_policy", "OPTIONAL"))
    sequence = route_sequence(purpose_type)
    state["route_sequence"] = sequence
    state["purpose_type"] = purpose_type
    state["step3_policy"] = step3_policy
    persist_state(log_dir, state, final=False)

    if "STEP1_PRODUCT" in sequence and not should_skip_step(state, "step1_product"):
        update_step(state, log_dir, "step1_product", step1_product(context, output_dir, log_dir, args.execution_mode))

    if "STEP4_BENCHMARK" in sequence and not should_skip_step(state, "step4_benchmark"):
        update_step(state, log_dir, "step4_benchmark", step4_benchmark(context, output_dir, log_dir, download_root, args.execution_mode, state["steps"].get("step1_product", {})))

    if "STEP2_KEYWORD" in sequence and not should_skip_step(state, "step2_keyword"):
        update_step(state, log_dir, "step2_keyword", step2_keyword(context, output_dir, log_dir))

    if "STEP3_MARKET" in sequence and not should_skip_step(state, "step3_market"):
        update_step(
            state,
            log_dir,
            "step3_market",
            step3_market(context, output_dir, log_dir, purpose_type, step3_policy, state["steps"].get("step1_product", {})),
        )

    state_path = ensure_within_repo(log_dir / LATEST_STATE, "latest_nightly_state")
    if not should_skip_step(state, "step7_candidate_pool"):
        update_step(state, log_dir, "step7_candidate_pool", step7_candidate_pool(output_dir, log_dir, state_path))

    candidate_step = state.get("steps", {}).get("step7_candidate_pool", {})
    candidate_status = str(candidate_step.get("status", "")).strip().upper()
    if candidate_status in {"PASS", "HOLD"}:
        state["status"] = "PASS"
        state["reason_code"] = str(candidate_step.get("reason_code", "PASS")).strip() or "PASS"
        state["message"] = "Nightly route completed end-to-end with resumable state and downstream candidate-pool handoff."
    else:
        state["status"] = "BLOCKED"
        state["reason_code"] = str(candidate_step.get("reason_code", "NIGHTLY_CHAIN_BLOCKED")).strip() or "NIGHTLY_CHAIN_BLOCKED"
        state["message"] = str(candidate_step.get("message", "")).strip() or "Nightly route did not reach a usable candidate-pool handoff."
    state["auth_incidents"] = [
        {
            "step_key": step_key,
            "auth_incident_path": str(payload.get("auth_incident_path", "")).strip(),
            "auth_surface_family": str(payload.get("auth_surface_family", "")).strip(),
            "auth_replay_available": bool(payload.get("auth_replay_available")),
            "auth_owner_recording_drop_path": str(payload.get("auth_owner_recording_drop_path", "")).strip(),
            "auth_replay_attempted": bool(payload.get("auth_replay_attempted")),
            "auth_replay_status": str(payload.get("auth_replay_status", "")).strip(),
            "auth_replay_reason_code": str(payload.get("auth_replay_reason_code", "")).strip(),
        }
        for step_key, payload in state.get("steps", {}).items()
        if isinstance(payload, dict) and (
            str(payload.get("auth_incident_path", "")).strip()
            or bool(payload.get("auth_replay_attempted"))
        )
    ]
    state["owner_login_replay_required"] = any(not item.get("auth_replay_available") for item in state["auth_incidents"])
    state["finished_at"] = iso_now()
    persist_state(log_dir, state, final=True)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0 if state["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
