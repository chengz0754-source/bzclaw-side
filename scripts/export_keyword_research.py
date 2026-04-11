from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from keyword_chain_common import (
    KeywordChainError,
    ensure_within_repo,
    iso_now,
    log_dir_from_namespace,
    output_dir_from_namespace,
    persist_run_summary,
    resolve_context_from_namespace,
    write_json_atomic,
)
from parse_keyword_history_workbook import build_raw_artifact
from sellersprite_auth_registry import is_auth_reason, register_auth_incident, replay_meta_from_incident
from sellersprite_auth_replay import perform_registered_login_replay, summary_requests_auth_replay


ROOT = Path(__file__).resolve().parents[1]
KEYWORD_RESEARCH_URL = "https://www.sellersprite.com/v3/keyword-miner"
RAW_FILE_NAME = "keyword_research_raw.json"
KEYWORD_EXPORT_RUNNER = ROOT / "scripts" / "run_sellersprite_keyword_export_flow.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect SellerSprite keyword research evidence by reusing the stabilized keyword export flow and parsing the downloaded KeywordHistory workbook.",
    )
    parser.add_argument("--context-row-index", type=int, default=1)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--direction-id", default=None)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--category-hint", default=None)
    parser.add_argument("--site", default=None)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--sample-top-n", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--log-dir", default=None)
    parser.add_argument("--download-dir", default=None)
    parser.add_argument("--task-name", default=None)
    parser.add_argument("--result-row-index", type=int, default=1)
    parser.add_argument("--max-wait-seconds", type=int, default=300)
    parser.add_argument("--poll-interval-seconds", type=int, default=10)
    parser.add_argument("--download-timeout-seconds", type=int, default=90)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--execution-mode", choices=("auto", "persistent", "storage_state"), default="auto")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def parse_flow_summary(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        raise KeywordChainError("Keyword export runner returned empty stdout.", "KEYWORD_EXPORT_RUNNER_NO_STDOUT")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise KeywordChainError(
            "Keyword export runner stdout was not valid JSON.",
            "KEYWORD_EXPORT_RUNNER_BAD_STDOUT",
        ) from exc


def flow_page_snapshot(flow_summary: dict[str, Any]) -> dict[str, Any]:
    final_page = flow_summary.get("final_page", {})
    if isinstance(final_page, dict) and (final_page.get("url") or final_page.get("title")):
        return final_page
    steps = flow_summary.get("steps", [])
    if isinstance(steps, list):
        for step in reversed(steps):
            if not isinstance(step, dict):
                continue
            page_url = str(step.get("page_url", "")).strip()
            page_title = str(step.get("page_title", "")).strip()
            if page_url or page_title:
                return {
                    "url": page_url,
                    "title": page_title,
                    "guest_markers": list(step.get("guest_markers", [])) if isinstance(step.get("guest_markers"), list) else [],
                    "body_excerpt": "",
                }
    return {}


def build_flow_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(KEYWORD_EXPORT_RUNNER),
        "--context-row-index",
        str(args.context_row_index),
        "--result-row-index",
        str(args.result_row_index),
        "--max-wait-seconds",
        str(args.max_wait_seconds),
        "--poll-interval-seconds",
        str(args.poll_interval_seconds),
        "--download-timeout-seconds",
        str(args.download_timeout_seconds),
        "--execution-mode",
        str(args.execution_mode),
    ]
    if args.run_name:
        command.extend(["--run-name", str(args.run_name)])
    if args.direction_id:
        command.extend(["--direction-id", str(args.direction_id)])
    if args.keyword:
        command.extend(["--keyword", str(args.keyword)])
    if args.category_hint:
        command.extend(["--category-hint", str(args.category_hint)])
    if args.site:
        command.extend(["--site", str(args.site)])
    if args.days is not None:
        command.extend(["--days", str(args.days)])
    if args.sample_top_n is not None:
        command.extend(["--sample-top-n", str(args.sample_top_n)])
    if args.task_name:
        command.extend(["--task-name", str(args.task_name)])
    if args.download_dir:
        command.extend(["--download-dir", str(args.download_dir)])
    if args.headless:
        command.append("--headless")
    if args.dry_run:
        command.append("--dry-run")
    return command


def run_keyword_export_flow(args: argparse.Namespace) -> dict[str, Any]:
    completed = subprocess.run(
        build_flow_command(args),
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    flow_summary = parse_flow_summary(completed.stdout)
    flow_summary["runner_return_code"] = completed.returncode
    flow_summary["runner_stderr"] = completed.stderr.strip()
    return flow_summary


def run_once(args: argparse.Namespace, *, replay_attempted: bool = False, replay_result: dict[str, Any] | None = None) -> tuple[int, dict[str, Any], Path]:
    context = resolve_context_from_namespace(args, require_direction_id=False)
    output_dir = output_dir_from_namespace(args)
    log_dir = log_dir_from_namespace(args)
    raw_artifact_path = ensure_within_repo(output_dir / RAW_FILE_NAME, "raw_artifact_path")
    summary: dict[str, Any] = {
        "timestamp": iso_now(),
        "module": "keyword_research",
        "status": "BLOCKED",
        "reason_code": "",
        "message": "",
        "context_source": context.context_source,
        "运行名称": context.run_name,
        "方向ID": context.direction_id,
        "方向词": context.keyword,
        "站点": context.site,
        "类目提示": context.category_hint,
        "attempted_url": KEYWORD_RESEARCH_URL,
        "final_url": "",
        "page_title": "",
        "guest_markers": [],
        "flow_summary": {},
        "downloaded_workbook_path": "",
        "raw_artifact_path": "",
        "raw_row_count": 0,
        "auth_incident_path": "",
        "auth_surface_family": "",
        "auth_replay_available": False,
        "auth_replay_snippet_path": "",
        "auth_owner_recording_drop_path": "",
        "auth_replay_attempted": replay_attempted,
        "auth_replay_result": replay_result or {},
        "dry_run": bool(args.dry_run),
    }

    try:
        if not KEYWORD_EXPORT_RUNNER.exists():
            raise KeywordChainError(
                f"Keyword export runner is missing: {KEYWORD_EXPORT_RUNNER}",
                "KEYWORD_EXPORT_RUNNER_MISSING",
            )

        flow_summary = run_keyword_export_flow(args)
        summary["flow_summary"] = {
            "status": flow_summary.get("status", ""),
            "reason_code": flow_summary.get("reason_code", ""),
            "message": flow_summary.get("message", ""),
            "execution_mode": flow_summary.get("execution_mode", ""),
            "runner_return_code": flow_summary.get("runner_return_code", ""),
        }
        page_snapshot = flow_page_snapshot(flow_summary)
        summary["final_url"] = str(page_snapshot.get("url", ""))
        summary["page_title"] = str(page_snapshot.get("title", ""))
        summary["guest_markers"] = list(page_snapshot.get("guest_markers", []))

        if flow_summary.get("status") != "PASS" and (
            is_auth_reason(flow_summary.get("reason_code"))
            or summary["guest_markers"]
            or "/w/user/login" in summary["final_url"]
        ):
            incident = register_auth_incident(
                module_name="keyword_research",
                step_name=str(flow_summary.get("current_step", "keyword_research_flow")).strip() or "keyword_research_flow",
                source_script=__file__,
                reason_code=str(flow_summary.get("reason_code") or "KEYWORD_EXPORT_FLOW_AUTH_REQUIRED"),
                current_url=summary["final_url"],
                redirect_from_url=KEYWORD_RESEARCH_URL,
                page_snapshot=page_snapshot,
                run_context={
                    "context": context.__dict__,
                    "flow_status": flow_summary.get("status", ""),
                    "flow_reason_code": flow_summary.get("reason_code", ""),
                    "execution_mode": flow_summary.get("execution_mode", ""),
                },
                screenshot_path=str((flow_summary.get("screenshots") or [""])[-1] or ""),
                extra={"runner_return_code": flow_summary.get("runner_return_code", "")},
            )
            summary.update(replay_meta_from_incident(incident))

        if flow_summary.get("status") != "PASS":
            raise KeywordChainError(
                str(flow_summary.get("message") or "Keyword export flow did not complete successfully."),
                str(flow_summary.get("reason_code") or "KEYWORD_EXPORT_FLOW_BLOCKED"),
            )

        if args.dry_run:
            summary["status"] = "PASS"
            summary["reason_code"] = "DRY_RUN_ONLY"
            summary["message"] = "Dry-run validated the stabilized keyword export flow without requiring workbook parsing."
            persist_run_summary(log_dir, "latest_keyword_research_run.json", "keyword_research_runs.jsonl", summary)
            return 0, summary, log_dir

        workbook_path_raw = flow_summary.get("download", {}).get("path", "")
        if not workbook_path_raw:
            raise KeywordChainError(
                "Keyword export flow completed but no downloaded workbook path was reported.",
                "KEYWORD_RESEARCH_WORKBOOK_MISSING",
            )
        workbook_path = ensure_within_repo(Path(workbook_path_raw), "keyword_history_workbook")
        summary["downloaded_workbook_path"] = str(workbook_path)

        raw_artifact = build_raw_artifact(workbook_path, context, raw_artifact_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(raw_artifact_path, raw_artifact)

        summary["status"] = "PASS"
        summary["reason_code"] = "PASS"
        summary["message"] = "Keyword research raw rows collected successfully from the stabilized SellerSprite KeywordHistory workbook export."
        summary["raw_artifact_path"] = str(raw_artifact_path)
        summary["raw_row_count"] = len(raw_artifact.get("rows", []))
        summary["final_url"] = str(flow_summary.get("final_page", {}).get("url", summary["final_url"]))
        summary["page_title"] = str(flow_summary.get("final_page", {}).get("title", summary["page_title"]))
    except KeywordChainError as exc:
        summary["status"] = "BLOCKED"
        summary["reason_code"] = exc.reason_code
        summary["message"] = str(exc)
    except Exception as exc:
        summary["status"] = "BLOCKED"
        summary["reason_code"] = "KEYWORD_RESEARCH_UNHANDLED_ERROR"
        summary["message"] = str(exc)

    persist_run_summary(log_dir, "latest_keyword_research_run.json", "keyword_research_runs.jsonl", summary)
    return (0 if summary["status"] == "PASS" else 2), summary, log_dir


def main() -> int:
    args = parse_args()
    exit_code, summary, _log_dir = run_once(args)
    if exit_code != 0 and summary_requests_auth_replay(summary):
        replay_result = perform_registered_login_replay(
            surface_family=str(summary.get("auth_surface_family", "")).strip(),
            module_name="keyword_research",
            trigger_reason_code=str(summary.get("reason_code", "")).strip(),
            trigger_summary=summary,
        )
        if replay_result.get("status") == "PASS":
            args.execution_mode = str(replay_result.get("execution_mode_override", "")).strip() or "storage_state"
            exit_code, summary, _log_dir = run_once(args, replay_attempted=True, replay_result=replay_result)
        else:
            summary["auth_replay_attempted"] = True
            summary["auth_replay_result"] = replay_result
            persist_run_summary(_log_dir, "latest_keyword_research_run.json", "keyword_research_runs.jsonl", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
