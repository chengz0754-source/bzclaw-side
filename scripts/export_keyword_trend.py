from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from keyword_chain_common import (
    KeywordChainError,
    compact_text,
    ensure_within_repo,
    iso_now,
    log_dir_from_namespace,
    output_dir_from_namespace,
    persist_run_summary,
    resolve_context_from_namespace,
    traffic_cost_index_from_bid,
    write_json_atomic,
)
from run_sellersprite_keyword_export_flow import build_keyword_miner_url, launch_context, login_required
from sellersprite_auth_registry import register_auth_incident, replay_meta_from_incident
from sellersprite_auth_replay import perform_registered_login_replay, summary_requests_auth_replay
from sellersprite_overlay_guard import guard_page, page_identity


KEYWORD_TREND_URL = "https://www.sellersprite.com/v3/keyword-miner"
RAW_FILE_NAME = "keyword_trend_raw.json"
ROW_SELECTOR = ".el-table__body-wrapper tbody tr"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect SellerSprite keyword-trend research rows from the live v3 keyword-miner result table.",
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
    parser.add_argument("--headless", action="store_true", help="Use headless mode. Current verified live path prefers headed persistent-profile mode.")
    parser.add_argument("--execution-mode", choices=("auto", "persistent", "storage_state"), default="auto")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def page_snapshot(page) -> dict[str, Any]:
    snapshot = page_identity(page)
    body_text = page.locator("body").inner_text(timeout=15000)
    snapshot["body_excerpt"] = compact_text(body_text)[:1600]
    return snapshot


def first_number(text: Any) -> str:
    match = re.search(r"-?\d+(?:\.\d+)?", str(text or "").replace(",", ""))
    return match.group(0) if match else ""


def money_values(text: Any) -> list[str]:
    return re.findall(r"\$?\s*(-?\d+(?:\.\d+)?)", str(text or "").replace(",", ""))


def keyword_from_label(label: str) -> str:
    text = compact_text(label)
    text = re.sub(r"\bAC\b", "", text, flags=re.IGNORECASE)
    text = re.split(r"[\u4e00-\u9fff]", text)[0]
    return compact_text(text).strip(" -")


def extract_surface(page) -> dict[str, Any]:
    return page.evaluate(
        """
        () => {
          const headers = Array.from(document.querySelectorAll('table thead th')).map(
            (th) => (th.innerText || '').replace(/\\s+/g, ' ').trim()
          );
          const rows = Array.from(document.querySelectorAll('.el-table__body-wrapper tbody tr')).map((row, index) => ({
            row_index: index + 1,
            raw_cells: Array.from(row.querySelectorAll('td')).map(
              (td) => (td.innerText || '').replace(/\\s+/g, ' ').trim()
            ),
            row_text: (row.innerText || '').replace(/\\s+/g, ' ').trim(),
          }));
          return {
            headers,
            rows: rows.filter((row) => row.raw_cells.some((cell) => cell)),
          };
        }
        """
    )


def parse_rows(surface: dict[str, Any], context, raw_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in surface.get("rows", []):
        cells = list(row.get("raw_cells", []))
        if len(cells) < 15:
            continue
        keyword = keyword_from_label(cells[1])
        if not keyword:
            continue
        relatedness_rank = re.findall(r"\d+(?:\.\d+)?", cells[5])
        monthly_searches = first_number(cells[6])
        click_metrics = re.findall(r"-?\d+(?:\.\d+)?", cells[13])
        ppc_values = money_values(cells[14])
        ppc_bid = ppc_values[0] if ppc_values else ""
        rows.append(
            {
                "source_module": "KeywordTrendResearch",
                "keyword": keyword,
                "site": context.site,
                "main_category": context.category_hint,
                "monthly_searches": monthly_searches,
                "search_frequency_rank": relatedness_rank[1] if len(relatedness_rank) >= 2 else "",
                "growth_pct": "",
                "click_concentration_pct": click_metrics[0] if click_metrics else "",
                "ppc_bid_usd": ppc_bid,
                "traffic_cost_index": traffic_cost_index_from_bid(ppc_bid),
                "captured_at": iso_now(),
                "source_query": context.keyword,
                "source_file": str(raw_path),
                "trend_surface_present": "是",
                "page_row_index": str(row.get("row_index", "")),
                "raw_cells": cells,
                "raw_row_text": row.get("row_text", ""),
            }
        )
    return rows


def wait_for_visible_rows(page, timeout_seconds: int = 20) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_surface: dict[str, Any] = {"headers": [], "rows": []}
    while time.time() < deadline:
        guard_page(page, "keyword_trend_surface", preserve_texts=("导出", "前往查看", "我的导出"))
        surface = extract_surface(page)
        last_surface = surface
        if surface.get("rows"):
            return surface
        page.wait_for_timeout(1000)
    return last_surface


def run_once(args: argparse.Namespace, *, replay_attempted: bool = False, replay_result: dict[str, Any] | None = None) -> tuple[int, dict[str, Any], Path]:
    context = resolve_context_from_namespace(args, require_direction_id=False)
    output_dir = output_dir_from_namespace(args)
    log_dir = log_dir_from_namespace(args)
    raw_artifact_path = ensure_within_repo(output_dir / RAW_FILE_NAME, "raw_artifact_path")
    summary: dict[str, Any] = {
        "timestamp": iso_now(),
        "module": "keyword_trend",
        "status": "BLOCKED",
        "reason_code": "",
        "message": "",
        "context_source": context.context_source,
        "运行名称": context.run_name,
        "方向ID": context.direction_id,
        "方向词": context.keyword,
        "站点": context.site,
        "attempted_url": KEYWORD_TREND_URL,
        "final_url": "",
        "page_title": "",
        "guest_markers": [],
        "execution_mode": "",
        "surface_headers": [],
        "surface_row_count": 0,
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

    context_browser = None
    browser = None
    try:
        with sync_playwright() as playwright:
            context_browser, browser, execution_mode, warning = launch_context(playwright, args)
            summary["execution_mode"] = execution_mode
            if warning:
                summary["persistent_launch_warning"] = warning
            page = context_browser.pages[0] if context_browser.pages else context_browser.new_page()
            page.goto(build_keyword_miner_url(context), wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(2500)
            snapshot = page_snapshot(page)
            summary["final_url"] = snapshot["url"]
            summary["page_title"] = snapshot["title"]
            summary["guest_markers"] = snapshot["guest_markers"]

            if login_required(page):
                incident = register_auth_incident(
                    module_name="keyword_trend",
                    step_name="keyword_trend_open_surface",
                    source_script=__file__,
                    reason_code="KEYWORD_TREND_AUTH_REQUIRED",
                    current_url=snapshot["url"],
                    redirect_from_url=KEYWORD_TREND_URL,
                    page=page,
                    page_snapshot=snapshot,
                    run_context={
                        "context": context.__dict__,
                        "execution_mode": execution_mode,
                        "dry_run": bool(args.dry_run),
                    },
                )
                summary.update(replay_meta_from_incident(incident))
                raise KeywordChainError(
                    "Keyword trend surface resolved to a login/auth state instead of the live keyword-miner result table.",
                    "KEYWORD_TREND_AUTH_REQUIRED",
                )

            surface = wait_for_visible_rows(page)
            summary["surface_headers"] = surface.get("headers", [])
            summary["surface_row_count"] = len(surface.get("rows", []))

            if args.dry_run:
                if not surface.get("rows"):
                    raise KeywordChainError(
                        "Keyword trend dry-run reached the page, but no visible result rows were present on the live v3 table.",
                        "KEYWORD_TREND_RESULT_ROWS_MISSING",
                    )
                summary["status"] = "PASS"
                summary["reason_code"] = "DRY_RUN_ONLY"
                summary["message"] = "Dry-run validated the live v3 keyword-miner result surface and row extraction selectors."
                persist_run_summary(log_dir, "latest_keyword_trend_run.json", "keyword_trend_runs.jsonl", summary)
                return 0, summary, log_dir

            if not surface.get("rows"):
                raise KeywordChainError(
                    "Keyword trend page was reachable, but the live v3 result table did not expose any visible rows.",
                    "KEYWORD_TREND_RESULT_ROWS_MISSING",
                )

            rows = parse_rows(surface, context, raw_artifact_path)
            if not rows:
                raise KeywordChainError(
                    "Keyword trend page exposed visible rows, but no keyword rows were parsed from the current v3 DOM structure.",
                    "KEYWORD_TREND_NO_ROWS",
                )

            raw_artifact = {
                "module": "keyword_trend",
                "source_type": "SELLERSPRITE_V3_KEYWORD_TABLE",
                "status": "PASS",
                "timestamp": iso_now(),
                "url": page.url,
                "title": page.title(),
                "context": {
                    "run_name": context.run_name,
                    "direction_id": context.direction_id,
                    "keyword": context.keyword,
                    "site": context.site,
                    "category_hint": context.category_hint,
                },
                "surface_headers": surface.get("headers", []),
                "rows": rows,
            }
            output_dir.mkdir(parents=True, exist_ok=True)
            write_json_atomic(raw_artifact_path, raw_artifact)

            summary["status"] = "PASS"
            summary["reason_code"] = "PASS"
            summary["message"] = "Keyword trend raw rows collected successfully from the live v3 keyword-miner result table."
            summary["raw_artifact_path"] = str(raw_artifact_path)
            summary["raw_row_count"] = len(rows)
            summary["final_url"] = page.url
            summary["page_title"] = page.title()
    except KeywordChainError as exc:
        summary["status"] = "BLOCKED"
        summary["reason_code"] = exc.reason_code
        summary["message"] = str(exc)
    except Exception as exc:
        summary["status"] = "BLOCKED"
        summary["reason_code"] = "KEYWORD_TREND_UNHANDLED_ERROR"
        summary["message"] = str(exc)
    finally:
        if context_browser is not None:
            try:
                context_browser.close()
            except Exception:
                pass
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass

    persist_run_summary(log_dir, "latest_keyword_trend_run.json", "keyword_trend_runs.jsonl", summary)
    return (0 if summary["status"] == "PASS" else 2), summary, log_dir


def main() -> int:
    args = parse_args()
    exit_code, summary, log_dir = run_once(args)
    if exit_code != 0 and summary_requests_auth_replay(summary):
        replay_result = perform_registered_login_replay(
            surface_family=str(summary.get("auth_surface_family", "")).strip(),
            module_name="keyword_trend",
            trigger_reason_code=str(summary.get("reason_code", "")).strip(),
            trigger_summary=summary,
        )
        if replay_result.get("status") == "PASS":
            args.execution_mode = str(replay_result.get("execution_mode_override", "")).strip() or "storage_state"
            exit_code, summary, log_dir = run_once(args, replay_attempted=True, replay_result=replay_result)
        else:
            summary["auth_replay_attempted"] = True
            summary["auth_replay_result"] = replay_result
            persist_run_summary(log_dir, "latest_keyword_trend_run.json", "keyword_trend_runs.jsonl", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
