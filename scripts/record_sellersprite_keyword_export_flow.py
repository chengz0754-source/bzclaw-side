from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from keyword_chain_common import (
    STORAGE_STATE_PATH,
    KeywordChainError,
    ensure_within_repo,
    iso_now,
    resolve_context_from_namespace,
    write_json_atomic,
)
from sellersprite_overlay_guard import capture_screenshot, guard_page, page_identity


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[1]
KEYWORD_MINER_URL = "https://www.sellersprite.com/v3/keyword-miner"
EXPORT_LOG_URL = "https://www.sellersprite.com/v2/export-log"
LOG_DIR = ROOT / "logs" / "sellersprite_keyword_export_flow"
LATEST_LOG_FILE = LOG_DIR / "latest_recording_launcher.json"
RUN_HISTORY_FILE = LOG_DIR / "recording_launcher_runs.jsonl"
SCREENSHOT_DIR = ROOT / "playwright" / "screenshots" / "sellersprite_keyword_export_flow"
SITE_TO_MARKET_ID = {
    "US": 1,
    "JP": 2,
    "UK": 3,
    "DE": 4,
    "FR": 5,
    "IT": 6,
    "ES": 7,
    "CA": 8,
    "IN": 9,
    "MX": 10,
    "BR": 11,
    "AU": 12,
    "AE": 13,
    "SA": 14,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch a stabilized SellerSprite recording session after overlay governance instead of using raw codegen directly.",
    )
    parser.add_argument("--mode", choices=("keyword_result", "export_log"), required=True)
    parser.add_argument("--context-row-index", type=int, default=1)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--direction-id", default=None)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--category-hint", default=None)
    parser.add_argument("--site", default=None)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--sample-top-n", type=int, default=None)
    parser.add_argument("--month", default=None)
    parser.add_argument("--headless", action="store_true", help="Self-test only. Real recording should keep headed mode.")
    parser.add_argument("--no-pause", action="store_true", help="Exit after preparation instead of opening Playwright inspector.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare the target page and exit without pausing.")
    return parser.parse_args()


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    ensure_within_repo(path, "jsonl_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def login_required(page) -> bool:
    snapshot = page_identity(page)
    return "/w/user/login" in page.url or "登录" in snapshot.get("title", "") or bool(snapshot.get("guest_markers"))


def keyword_query_button(page):
    return page.locator("button[type='submit']").first


def prepare_keyword_result_surface(page, context, month: str | None) -> dict[str, Any]:
    page.goto(KEYWORD_RESEARCH_URL, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(2000)
    guard_before = guard_page(page, "keyword_result_entry")

    keyword_input = page.locator("input[name='includeKeywords']")
    if keyword_input.count() == 0:
        raise KeywordChainError("Keyword-result recorder could not find the SellerSprite keyword query form.", "KEYWORD_RESULT_FORM_NOT_VISIBLE")

    keyword_input.fill(context.keyword)
    applied_filters = fill_rule_filters(page, month)
    department_value = department_value_from_hint(context.category_hint)
    if department_value:
        department_locator = page.locator(f"input[value='{department_value}']")
        if department_locator.count():
            department_locator.first.check(force=True)
            page.wait_for_timeout(250)

    keyword_query_button(page).click(timeout=10000)
    page.wait_for_timeout(5000)
    guard_after = guard_page(page, "keyword_result_after_submit", preserve_texts=["导出", "前往查看", "我的导出"])
    snapshot = page_identity(page)
    return {
        "entry_guard": guard_before,
        "after_submit_guard": guard_after,
        "snapshot": snapshot,
        "applied_filters": applied_filters,
    }


def prepare_export_log_surface(page) -> dict[str, Any]:
    page.goto(EXPORT_LOG_URL, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(2500)
    guard_result = guard_page(page, "export_log_entry", preserve_texts=["下载", "前往查看"])
    return {
        "guard": guard_result,
        "snapshot": page_identity(page),
    }


def login_required(page) -> bool:
    if "/w/user/login" in page.url:
        return True
    try:
        title = str(page.title())
    except Exception:
        title = ""
    if "登录" in title:
        return True
    login_surface_selectors = (
        "input[type='password']",
        "button:has-text('立即登录')",
        "text=扫码登录",
        "text=验证码登录",
        "text=账号登录",
    )
    for selector in login_surface_selectors:
        locator = page.locator(selector)
        if locator.count():
            try:
                if locator.first.is_visible(timeout=500):
                    return True
            except Exception:
                continue
    return False


def keyword_result_url(context) -> str:
    normalized_site = str(context.site or "US").strip().upper()
    market_id = SITE_TO_MARKET_ID.get(normalized_site, 1)
    return f"{KEYWORD_MINER_URL}/?q={quote(str(context.keyword or '').strip())}&marketId={market_id}&batch=0"


def prepare_keyword_result_surface(page, context, month: str | None) -> dict[str, Any]:
    del month
    target_url = keyword_result_url(context)
    page.goto(target_url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(2200)
    guard_before = guard_page(page, "keyword_result_entry", preserve_texts=["导出", "前往查看", "我的导出"])
    export_button = page.locator("button").filter(has_text="导出明细")
    checkbox_locator = page.locator("input[type='checkbox']")
    if export_button.count() == 0 or checkbox_locator.count() == 0:
        raise KeywordChainError("Keyword-result recorder could not reach the stabilized v3 result surface.", "KEYWORD_RESULT_ROUTE_UNAVAILABLE")
    guard_after = guard_page(page, "keyword_result_ready", preserve_texts=["导出", "前往查看", "我的导出"])
    snapshot = page_identity(page)
    return {
        "target_url": target_url,
        "entry_guard": guard_before,
        "ready_guard": guard_after,
        "snapshot": snapshot,
        "checkbox_count": checkbox_locator.count(),
        "export_button_count": export_button.count(),
    }


def prepare_export_log_surface(page) -> dict[str, Any]:
    page.goto(EXPORT_LOG_URL, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(2500)
    guard_result = guard_page(page, "export_log_entry", preserve_texts=["下载", "前往查看"])
    return {
        "guard": guard_result,
        "snapshot": page_identity(page),
    }


def main() -> int:
    args = parse_args()
    context = resolve_context_from_namespace(args, require_direction_id=False)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "timestamp": iso_now(),
        "module": "sellersprite_keyword_export_recording",
        "mode": args.mode,
        "status": "HOLD",
        "reason_code": "",
        "message": "",
        "context": {
            "run_name": context.run_name,
            "direction_id": context.direction_id,
            "keyword": context.keyword,
            "category_hint": context.category_hint,
            "site": context.site,
            "days": context.days,
            "context_source": context.context_source,
        },
        "storage_state_path": str(STORAGE_STATE_PATH),
        "headless": bool(args.headless),
        "pause_opened": False,
        "screenshots": [],
    }

    try:
        if not STORAGE_STATE_PATH.exists():
            raise KeywordChainError(f"Storage state file is missing: {STORAGE_STATE_PATH}", "AUTH_STATE_MISSING")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=bool(args.headless))
            context_browser = browser.new_context(
                storage_state=str(STORAGE_STATE_PATH),
                viewport={"width": 1600, "height": 1400},
                accept_downloads=False,
            )
            page = context_browser.new_page()

            if args.mode == "keyword_result":
                preparation = prepare_keyword_result_surface(page, context, args.month)
            else:
                preparation = prepare_export_log_surface(page)

            summary["preparation"] = preparation
            summary["final_page"] = page_identity(page)
            summary["screenshots"].append(capture_screenshot(page, f"record-{args.mode}-prepared", SCREENSHOT_DIR))

            if login_required(page):
                summary["status"] = "HOLD"
                summary["reason_code"] = "SELLERSPRITE_AUTH_REQUIRED"
                summary["message"] = "The recording launcher reached the target route preparation step, but the current storage state still lands on guest/login state."
            else:
                summary["status"] = "PASS"
                summary["reason_code"] = "RECORDING_READY"
                summary["message"] = "The recording launcher prepared the SellerSprite surface, ran overlay governance, and is ready for segmented recording."

            if not args.no_pause and not args.dry_run:
                summary["pause_opened"] = True
                page.pause()
                summary["final_page_after_pause"] = page_identity(page)
                summary["screenshots"].append(capture_screenshot(page, f"record-{args.mode}-after-pause", SCREENSHOT_DIR))

            context_browser.close()
            browser.close()
    except KeywordChainError as exc:
        summary["status"] = "HOLD"
        summary["reason_code"] = exc.reason_code
        summary["message"] = str(exc)
    except Exception as exc:
        summary["status"] = "HOLD"
        summary["reason_code"] = "RECORDING_LAUNCHER_UNHANDLED_ERROR"
        summary["message"] = str(exc)

    write_json_atomic(LATEST_LOG_FILE, summary)
    append_jsonl(RUN_HISTORY_FILE, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
