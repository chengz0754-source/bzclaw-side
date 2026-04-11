from __future__ import annotations

import argparse
import json
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from keyword_chain_common import (
    PROFILE_DIR,
    STORAGE_STATE_PATH,
    KeywordChainError,
    compact_text,
    ensure_within_repo,
    iso_now,
    resolve_context_from_namespace,
    write_json_atomic,
)
from sellersprite_overlay_guard import (
    capture_screenshot,
    find_first_visible,
    guard_page,
    locator_probe,
    page_identity,
)


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[1]
KEYWORD_MINER_URL = "https://www.sellersprite.com/v3/keyword-miner"
EXPORT_LOG_URL = "https://www.sellersprite.com/v2/export-log"
LOG_DIR = ROOT / "logs" / "sellersprite_keyword_export_flow"
SCREENSHOT_DIR = ROOT / "playwright" / "screenshots" / "sellersprite_keyword_export_flow"
DOWNLOADS_ROOT = ROOT / "runs" / "manual" / "20_keyword_exports"
LATEST_LOG_FILE = LOG_DIR / "latest_keyword_export_flow_run.json"
RUN_HISTORY_FILE = LOG_DIR / "keyword_export_flow_runs.jsonl"
RUN_FAILURE_FILE = LOG_DIR / "keyword_export_flow_failures.jsonl"

RESULT_ROW_CHECKBOX_NOT_VISIBLE = "RESULT_ROW_CHECKBOX_NOT_VISIBLE"
EXPORT_TRIGGER_BUTTON_NOT_VISIBLE = "EXPORT_TRIGGER_BUTTON_NOT_VISIBLE"
KEYWORD_RESULT_TABLE_NOT_VISIBLE = "KEYWORD_RESULT_TABLE_NOT_VISIBLE"
SELLERSPRITE_AUTH_REQUIRED = "SELLERSPRITE_AUTH_REQUIRED"
EXPORT_LOG_REDIRECTED_TO_LOGIN = "EXPORT_LOG_REDIRECTED_TO_LOGIN"
EXPORT_LOG_STATUS_FAILED = "EXPORT_LOG_STATUS_FAILED"
KEYWORD_RESULT_ROUTE_UNAVAILABLE = "KEYWORD_RESULT_ROUTE_UNAVAILABLE"
KEYWORD_RESULT_ROW_NOT_FOUND = "KEYWORD_RESULT_ROW_NOT_FOUND"

REQUIRED_REASON_CODES = {
    "RESULT_PAGE_BLOCKED_BY_OVERLAY",
    "EXPORT_DIALOG_NOT_VISIBLE",
    "EXPORT_CONFIRM_BUTTON_NOT_VISIBLE",
    "EXPORT_LOG_TASK_NOT_FOUND",
    "EXPORT_LOG_STATUS_TIMEOUT",
    "EXPORT_DOWNLOAD_BUTTON_NOT_VISIBLE",
    "EXPORT_FILE_NOT_DOWNLOADED",
    "UNEXPECTED_MODAL_BLOCKING_ACTION",
}

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

PAGE_OPEN_WAIT_MS = 2200
PRE_CLICK_WAIT_MS = 700
AFTER_CONFIRM_WAIT_MS = 1500
AFTER_EXPORT_LOG_WAIT_MS = 3000
CLICK_RETRY_WAIT_MS = 1200

EXPORT_DIALOG_CONFIRM_SELECTORS = (
    "button:has-text('前往查看')",
    "a:has-text('前往查看')",
    "button:has-text('去查看')",
    "a:has-text('去查看')",
    "button:has-text('查看')",
    "a:has-text('查看')",
    "button:has-text('我的导出')",
    "a:has-text('我的导出')",
)

EXPORT_DIALOG_SELECTORS = (
    ".el-message-box",
    ".modal.show",
    ".el-dialog",
    "div[role='dialog']",
)

RESULT_EXPORT_BUTTON_SELECTORS = (
    "#list-export",
    "#client-export-monthly",
    "#list-export-dynamic",
    "#list-export-reversing",
    "button:has-text('导出明细')",
    "a:has-text('导出明细')",
    "button:has-text('导出')",
    "a:has-text('导出')",
    "[title*='导出']",
    "[data-tips*='导出']",
)

EXPORT_DOWNLOAD_BUTTON_SELECTORS = (
    "a:has-text('下载')",
    "button:has-text('下载')",
    "a[download]",
    "a[href*='download']",
    "a[href*='export']",
)

STATUS_DONE_MARKERS = ("已完成", "完成", "success", "done")
STATUS_PROGRESS_MARKERS = ("导出中", "处理中", "生成中", "等待", "排队", "pending", "processing")
STATUS_FAIL_MARKERS = ("失败", "过期", "取消", "error", "failed")


EXPORT_DIALOG_CONFIRM_SELECTORS = (
    "button:has-text('前往查看')",
    "a:has-text('前往查看')",
    "button:has-text('去查看')",
    "a:has-text('去查看')",
    "button:has-text('查看')",
    "a:has-text('查看')",
    "button:has-text('我的导出')",
    "a:has-text('我的导出')",
)

RESULT_EXPORT_BUTTON_SELECTORS = (
    "#list-export",
    "#client-export-monthly",
    "#list-export-dynamic",
    "#list-export-reversing",
    "button:has-text('导出明细')",
    "a:has-text('导出明细')",
    "button:has-text('导出')",
    "a:has-text('导出')",
    "[title*='导出']",
    "[data-tips*='导出']",
)

EXPORT_DOWNLOAD_BUTTON_SELECTORS = (
    "a:has-text('下载')",
    "button:has-text('下载')",
    "a[title*='下载']",
    "button[title*='下载']",
    "a[download]",
    "a[href*='download']",
    "a[href*='export']",
    ".icon-download",
    ".el-icon-download",
)

STATUS_DONE_MARKERS = ("已完成", "完成", "success", "done")
STATUS_PROGRESS_MARKERS = ("导出中", "处理中", "生成中", "等待", "排队", "pending", "processing")
STATUS_FAIL_MARKERS = ("失败", "过期", "取消", "error", "failed")


class ExportFlowError(RuntimeError):
    def __init__(self, message: str, reason_code: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a stabilized SellerSprite keyword-export flow with overlay governance, export-log polling, and download validation.",
    )
    parser.add_argument("--context-row-index", type=int, default=1)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--direction-id", default=None)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--category-hint", default=None)
    parser.add_argument("--site", default=None)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--sample-top-n", type=int, default=None)
    parser.add_argument("--task-name", default=None, help="Optional stronger task-name hint for export-log matching.")
    parser.add_argument("--month", default=None)
    parser.add_argument("--result-row-index", type=int, default=1)
    parser.add_argument("--max-wait-seconds", type=int, default=300)
    parser.add_argument("--poll-interval-seconds", type=int, default=10)
    parser.add_argument("--download-timeout-seconds", type=int, default=90)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Validate result-page preparation only.")
    parser.add_argument("--execution-mode", choices=("auto", "persistent", "storage_state"), default="auto")
    parser.add_argument("--log-dir", default=str(LOG_DIR))
    parser.add_argument("--download-dir", default=None)
    return parser.parse_args()


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    ensure_within_repo(path, "jsonl_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return slug or "keyword"


def profile_has_content(profile_dir: Path = PROFILE_DIR) -> bool:
    return profile_dir.exists() and any(profile_dir.iterdir())


def login_required(page) -> bool:
    snapshot = page_identity(page)
    return "/w/user/login" in page.url or "登录" in str(snapshot.get("title", "")) or bool(snapshot.get("guest_markers"))


def result_query_button(page):
    return page.locator("button[type='submit']").first


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


def ensure_min_poll_interval(seconds: int) -> int:
    return max(5, int(seconds))


def wait_for_page_open(page) -> None:
    page.wait_for_timeout(PAGE_OPEN_WAIT_MS)


def wait_before_click(page) -> None:
    page.wait_for_timeout(PRE_CLICK_WAIT_MS)


def wait_after_confirm(page) -> None:
    page.wait_for_timeout(AFTER_CONFIRM_WAIT_MS)


def wait_after_export_log_jump(page) -> None:
    page.wait_for_timeout(AFTER_EXPORT_LOG_WAIT_MS)


def site_market_id(site: str | None) -> int:
    normalized = str(site or "US").strip().upper()
    market_id = SITE_TO_MARKET_ID.get(normalized)
    if market_id is None:
        raise ExportFlowError(
            f"SellerSprite keyword-miner marketId is not configured for site `{normalized}`.",
            KEYWORD_RESULT_ROUTE_UNAVAILABLE,
        )
    return market_id


def build_keyword_miner_url(context) -> str:
    return f"{KEYWORD_MINER_URL}/?q={quote(str(context.keyword or '').strip())}&marketId={site_market_id(context.site)}&batch=0"


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def clean_visible_text(value: str) -> str:
    return compact_text(str(value or "").replace("\u200b", " ")).strip()


def record_step(summary: dict[str, Any], step_name: str, status: str, page=None, reason_code: str = "", screenshot_path: str = "", extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {
        "timestamp": iso_now(),
        "step_name": step_name,
        "status": status,
        "reason_code": reason_code,
    }
    if page is not None:
        snapshot = page_identity(page)
        payload["page_url"] = snapshot.get("url", "")
        payload["page_title"] = snapshot.get("title", "")
    if screenshot_path:
        payload["screenshot_path"] = screenshot_path
    if extra:
        payload.update(extra)
    summary.setdefault("steps", []).append(payload)
    summary["current_step"] = step_name


def launch_context(playwright, args: argparse.Namespace) -> tuple[Any, Any, str, str]:
    warning = ""
    browser = None
    if args.execution_mode in {"auto", "persistent"} and profile_has_content(PROFILE_DIR):
        try:
            context_browser = playwright.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                channel="msedge",
                headless=bool(args.headless),
                viewport={"width": 1600, "height": 1400},
                accept_downloads=True,
            )
            return context_browser, browser, "persistent_profile", warning
        except Exception as exc:
            if args.execution_mode == "persistent":
                raise
            warning = str(exc)

    browser = playwright.chromium.launch(channel="msedge", headless=bool(args.headless))
    if STORAGE_STATE_PATH.exists():
        context_browser = browser.new_context(
            storage_state=str(STORAGE_STATE_PATH),
            viewport={"width": 1600, "height": 1400},
            accept_downloads=True,
        )
        return context_browser, browser, "storage_state", warning
    context_browser = browser.new_context(viewport={"width": 1600, "height": 1400}, accept_downloads=True)
    return context_browser, browser, "guest_context", warning


def validate_downloaded_file(path: Path, required_name_tokens: list[str], suggested_filename: str = "") -> dict[str, Any]:
    if not path.exists():
        raise ExportFlowError(f"Downloaded file was not saved: {path}", "EXPORT_FILE_NOT_DOWNLOADED")
    if path.stat().st_size <= 0:
        raise ExportFlowError(f"Downloaded file is empty: {path}", "EXPORT_FILE_NOT_DOWNLOADED")
    suffix = path.suffix.lower()
    if suffix not in {".xlsx", ".xls", ".csv", ".zip"}:
        raise ExportFlowError(f"Downloaded file extension is not recognized: {path.name}", "EXPORT_FILE_NOT_DOWNLOADED")
    if suffix == ".zip":
        try:
            with zipfile.ZipFile(path):
                pass
        except zipfile.BadZipFile as exc:
            raise ExportFlowError(f"Downloaded zip archive is invalid: {path.name}", "EXPORT_FILE_NOT_DOWNLOADED") from exc
    normalized_name = normalize_text(path.stem.replace("-", " "))
    normalized_suggested = normalize_text(Path(suggested_filename or "").stem.replace("-", " "))
    missing_tokens: list[str] = []
    for token in required_name_tokens:
        normalized_token = normalize_text(str(token).replace("-", " "))
        if not normalized_token:
            continue
        if normalized_token not in normalized_name and normalized_token not in normalized_suggested:
            missing_tokens.append(token)
    if missing_tokens:
        raise ExportFlowError(
            f"Downloaded file name is missing expected task tokens {missing_tokens}: {path.name}",
            "EXPORT_FILE_NOT_DOWNLOADED",
        )
    return {
        "path": str(path),
        "name": path.name,
        "size_bytes": path.stat().st_size,
        "suffix": suffix,
    }


def safe_download_filename(suggested_filename: str, fallback_stem: str) -> str:
    suffix = Path(suggested_filename or "").suffix.lower() or ".xlsx"
    source_stem = Path(suggested_filename or "").stem or fallback_stem
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "-", source_stem).strip("-") or fallback_stem
    return f"{safe_stem}{suffix}"


def locator_is_disabled(locator) -> bool:
    try:
        return bool(
            locator.evaluate(
                "(el) => !!el.disabled || el.getAttribute('aria-disabled') === 'true' || el.classList.contains('is-disabled')"
            )
        )
    except Exception:
        return False


def require_visible(page, locator, step_name: str, summary: dict[str, Any], not_visible_reason: str, preserve_texts: tuple[str, ...] = ()) -> Any:
    guard = guard_page(page, f"{step_name}-guard", preserve_texts=preserve_texts)
    try:
        locator.first.wait_for(state="visible", timeout=10000)
        return locator.first
    except Exception as exc:
        screenshot_path = capture_screenshot(page, f"{step_name}-not-visible", SCREENSHOT_DIR)
        record_step(
            summary,
            step_name,
            "FAIL",
            page=page,
            reason_code=not_visible_reason,
            screenshot_path=screenshot_path,
            extra={"error": str(exc), "guard": guard},
        )
        raise ExportFlowError(str(exc), not_visible_reason) from exc


def guarded_click(page, locator, step_name: str, summary: dict[str, Any], not_visible_reason: str, click_failure_reason: str, preserve_texts: tuple[str, ...] = ()) -> None:
    target = require_visible(page, locator, step_name, summary, not_visible_reason, preserve_texts=preserve_texts)
    for attempt in (1, 2):
        guard = guard_page(page, f"{step_name}-attempt-{attempt}", preserve_texts=preserve_texts)
        try:
            target.scroll_into_view_if_needed(timeout=10000)
        except Exception:
            pass
        try:
            wait_before_click(page)
            target.click(timeout=10000)
            record_step(
                summary,
                step_name,
                "PASS",
                page=page,
                extra={"attempt": attempt, "guard": guard},
            )
            return
        except Exception as exc:
            screenshot_path = capture_screenshot(page, f"{step_name}-attempt-{attempt}", SCREENSHOT_DIR)
            blockers = locator_probe(page, target)
            final_reason = click_failure_reason if blockers else "UNEXPECTED_MODAL_BLOCKING_ACTION"
            record_step(
                summary,
                step_name,
                "RETRY" if attempt == 1 else "FAIL",
                page=page,
                reason_code="" if attempt == 1 else final_reason,
                screenshot_path=screenshot_path,
                extra={"attempt": attempt, "error": str(exc), "guard": guard, "blockers": blockers},
            )
            if attempt == 2:
                raise ExportFlowError(str(exc), final_reason) from exc
            page.wait_for_timeout(CLICK_RETRY_WAIT_MS)


def prepare_keyword_result_page(page, context, month: str | None, summary: dict[str, Any]) -> list[dict[str, Any]]:
    page.goto(KEYWORD_RESEARCH_URL, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(2000)
    record_step(summary, "stage_a_open_keyword_page", "PASS", page=page)
    keyword_input = page.locator("input[name='includeKeywords']")
    if keyword_input.count() == 0:
        raise ExportFlowError("Keyword result form is not visible on SellerSprite keyword page.", "KEYWORD_RESULT_FORM_NOT_VISIBLE")

    guard_page(page, "stage_a_initial_governance")
    keyword_input.fill(context.keyword)
    applied_filters = fill_rule_filters(page, month)
    department_value = department_value_from_hint(context.category_hint)
    if department_value:
        department_locator = page.locator(f"input[value='{department_value}']")
        if department_locator.count():
            department_locator.first.check(force=True)
            page.wait_for_timeout(200)
    summary["applied_filters"] = applied_filters
    guarded_click(
        page,
        result_query_button(page),
        "stage_a_submit_keyword_query",
        summary,
        not_visible_reason="KEYWORD_RESULT_SUBMIT_NOT_VISIBLE",
        click_failure_reason="RESULT_PAGE_BLOCKED_BY_OVERLAY",
    )
    page.wait_for_timeout(5000)
    if "/w/user/login" in page.url:
        raise ExportFlowError(
            "SellerSprite redirected the keyword query to login, so the export flow cannot continue automatically.",
            SELLERSPRITE_AUTH_REQUIRED,
        )
    return extract_tables(page)


def locate_result_table(page, summary: dict[str, Any]):
    tables = extract_tables(page)
    table = choose_result_table(tables)
    if table is None:
        screenshot_path = capture_screenshot(page, "stage_a-result-table-missing", SCREENSHOT_DIR)
        record_step(summary, "stage_a_find_result_table", "FAIL", page=page, reason_code=KEYWORD_RESULT_TABLE_NOT_VISIBLE, screenshot_path=screenshot_path)
        raise ExportFlowError("Keyword result table is not visible after query submission.", KEYWORD_RESULT_TABLE_NOT_VISIBLE)
    record_step(summary, "stage_a_find_result_table", "PASS", page=page, extra={"table_index": table.get("tableIndex"), "headers": table.get("headers", [])})
    return page.locator("table").nth(int(table["tableIndex"])), table


def locate_result_row_checkbox(result_table_locator, row_index: int):
    row = result_table_locator.locator("tbody tr").nth(max(row_index - 1, 0))
    selectors = (
        "input[type='checkbox']",
        ".el-checkbox__inner",
        ".custom-control-label",
        "label",
    )
    for selector in selectors:
        locator = row.locator(selector)
        if locator.count():
            return row, locator.first
    return row, row.locator("input[type='checkbox']").first


def locate_export_trigger(page):
    return find_first_visible(page, RESULT_EXPORT_BUTTON_SELECTORS, timeout_ms=1500)


def dialog_snapshot(page) -> dict[str, Any] | None:
    for selector in EXPORT_DIALOG_SELECTORS:
        locator = page.locator(selector)
        if locator.count() and locator.first.is_visible():
            try:
                text = compact_text(locator.first.inner_text(timeout=1000))
            except Exception:
                text = ""
            return {"selector": selector, "text": text}
    return None


def handle_export_confirmation(page, summary: dict[str, Any], dialog_events: list[dict[str, Any]]) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        if "/v2/export-log" in page.url:
            record_step(summary, "stage_a_enter_export_log", "PASS", page=page, extra={"route": page.url, "via": "direct_navigation"})
            return
        dialog_info = dialog_snapshot(page)
        if dialog_info:
            confirm_button = find_first_visible(page, EXPORT_DIALOG_CONFIRM_SELECTORS, timeout_ms=1000)
            if confirm_button is None:
                screenshot_path = capture_screenshot(page, "stage_a-export-dialog-no-confirm", SCREENSHOT_DIR)
                record_step(
                    summary,
                    "stage_a_handle_export_dialog",
                    "FAIL",
                    page=page,
                    reason_code="EXPORT_CONFIRM_BUTTON_NOT_VISIBLE",
                    screenshot_path=screenshot_path,
                    extra={"dialog": dialog_info},
                )
                raise ExportFlowError("Export dialog became visible but no stable confirm button was found.", "EXPORT_CONFIRM_BUTTON_NOT_VISIBLE")
            guarded_click(
                page,
                confirm_button,
                "stage_a_confirm_export_dialog",
                summary,
                not_visible_reason="EXPORT_CONFIRM_BUTTON_NOT_VISIBLE",
                click_failure_reason="UNEXPECTED_MODAL_BLOCKING_ACTION",
                preserve_texts=("前往查看", "我的导出", "查看"),
            )
            page.wait_for_timeout(3000)
            if "/v2/export-log" not in page.url:
                page.goto(EXPORT_LOG_URL, wait_until="domcontentloaded", timeout=90000)
                page.wait_for_timeout(2000)
            record_step(summary, "stage_a_enter_export_log", "PASS", page=page, extra={"route": page.url, "via": "dialog_confirm"})
            return
        if dialog_events:
            last_dialog = dialog_events[-1]
            screenshot_path = capture_screenshot(page, "stage_a-unexpected-dialog", SCREENSHOT_DIR)
            record_step(
                summary,
                "stage_a_handle_export_dialog",
                "FAIL",
                page=page,
                reason_code="UNEXPECTED_MODAL_BLOCKING_ACTION",
                screenshot_path=screenshot_path,
                extra={"dialog_event": last_dialog},
            )
            raise ExportFlowError(f"Unexpected blocking dialog: {last_dialog.get('message', '')}", "UNEXPECTED_MODAL_BLOCKING_ACTION")
        guard_page(page, "stage_a_wait_export_dialog", preserve_texts=("前往查看", "我的导出"))
        page.wait_for_timeout(1000)

    screenshot_path = capture_screenshot(page, "stage_a-export-dialog-timeout", SCREENSHOT_DIR)
    record_step(summary, "stage_a_handle_export_dialog", "FAIL", page=page, reason_code="EXPORT_DIALOG_NOT_VISIBLE", screenshot_path=screenshot_path)
    raise ExportFlowError("SellerSprite export confirmation dialog did not become visible in time.", "EXPORT_DIALOG_NOT_VISIBLE")


def extract_export_log_tables(page) -> list[dict[str, Any]]:
    return page.evaluate(
        """
        () => Array.from(document.querySelectorAll('table')).map((table, tableIndex) => ({
          tableIndex,
          headers: Array.from(table.querySelectorAll('thead th, th')).map(
            (cell) => (cell.innerText || '').replace(/\\s+/g, ' ').trim()
          ),
          rows: Array.from(table.querySelectorAll('tbody tr')).map((row, rowIndex) => ({
            rowIndex,
            cells: Array.from(row.querySelectorAll('td')).map(
              (cell) => (cell.innerText || '').replace(/\\s+/g, ' ').trim()
            ),
            rowText: (row.innerText || '').replace(/\\s+/g, ' ').trim(),
          })).filter((row) => row.cells.length > 0 || row.rowText.length > 0)
        })).filter((table) => table.headers.length > 0 || table.rows.length > 0)
        """
    )


def choose_export_log_table(tables: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score = -1
    for table in tables:
        headers_text = " | ".join(str(item) for item in table.get("headers", []))
        rows = table.get("rows", [])
        score = 0
        if "任务" in headers_text or "名称" in headers_text:
            score += 3
        if "状态" in headers_text:
            score += 3
        if "操作" in headers_text or "下载" in headers_text:
            score += 2
        if rows:
            score += 1
        row_text = " ".join(str(row.get("rowText", "")) for row in rows[:3])
        if "下载" in row_text or "导出" in row_text:
            score += 2
        if score > best_score:
            best = table
            best_score = score
    return best


def header_index(headers: list[str], markers: tuple[str, ...]) -> int | None:
    for index, header in enumerate(headers):
        if any(marker in header for marker in markers):
            return index
    return None


def row_score(row_text: str, tokens: list[str]) -> int:
    normalized = normalize_text(row_text)
    score = 0
    for token in tokens:
        current = normalize_text(token)
        if not current:
            continue
        if current in normalized:
            score += 5 if len(current) >= 6 else 2
    return score


def find_export_task(page, target_tokens: list[str]) -> dict[str, Any] | None:
    tables = extract_export_log_tables(page)
    table = choose_export_log_table(tables)
    if table is None:
        return None

    headers = [str(item) for item in table.get("headers", [])]
    task_idx = header_index(headers, ("任务", "名称", "关键词"))
    status_idx = header_index(headers, ("状态", "进度"))

    selected: dict[str, Any] | None = None
    best_score = -1
    for row in table.get("rows", []):
        cells = [str(item) for item in row.get("cells", [])]
        row_text = str(row.get("rowText", "")).strip()
        task_name = cells[task_idx].strip() if task_idx is not None and task_idx < len(cells) else row_text[:120]
        status_value = cells[status_idx].strip() if status_idx is not None and status_idx < len(cells) else next(
            (cell for cell in cells if any(marker in cell for marker in STATUS_DONE_MARKERS + STATUS_PROGRESS_MARKERS + STATUS_FAIL_MARKERS)),
            "",
        )
        current_score = row_score(task_name + " " + row_text, target_tokens)
        if current_score == 0 and row.get("rowIndex", 999) == 0:
            current_score = 1
        if current_score > best_score:
            selected = {
                "table_index": int(table["tableIndex"]),
                "row_index": int(row.get("rowIndex", 0)),
                "task_name": task_name,
                "status_value": status_value,
                "row_text": row_text,
                "headers": headers,
            }
            best_score = current_score
    if selected and best_score > 0:
        return selected
    if selected and len(table.get("rows", [])) == 1:
        return selected
    return None


def status_kind(status_value: str) -> str:
    lowered = normalize_text(status_value)
    if any(normalize_text(marker) in lowered for marker in STATUS_DONE_MARKERS):
        return "done"
    if any(normalize_text(marker) in lowered for marker in STATUS_FAIL_MARKERS):
        return "fail"
    if any(normalize_text(marker) in lowered for marker in STATUS_PROGRESS_MARKERS):
        return "progress"
    return "unknown"


def poll_until_export_ready(page, summary: dict[str, Any], target_tokens: list[str], max_wait_seconds: int, poll_interval_seconds: int) -> dict[str, Any]:
    deadline = time.time() + max_wait_seconds
    seen_task = False
    last_task: dict[str, Any] | None = None
    while time.time() < deadline:
        guard_page(page, "stage_b_export_log_poll", preserve_texts=("下载", "前往查看"))
        if "/w/user/login" in page.url:
            raise ExportFlowError("SellerSprite redirected export-log to login.", EXPORT_LOG_REDIRECTED_TO_LOGIN)

        task = find_export_task(page, target_tokens)
        if task is None:
            record_step(summary, "stage_b_poll_export_log", "WAIT", page=page, extra={"matched_task_name": "", "status_value": ""})
        else:
            seen_task = True
            last_task = task
            summary["matched_task_name"] = task["task_name"]
            summary["matched_status_value"] = task["status_value"]
            record_step(
                summary,
                "stage_b_poll_export_log",
                "WAIT",
                page=page,
                extra={"matched_task_name": task["task_name"], "status_value": task["status_value"]},
            )
            kind = status_kind(task["status_value"])
            if kind == "done":
                return task
            if kind == "fail":
                raise ExportFlowError(
                    f"Export-log task entered a failed state: {task['status_value']}",
                    EXPORT_LOG_STATUS_FAILED,
                )

        if time.time() + poll_interval_seconds >= deadline:
            break
        page.reload(wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(max(1, poll_interval_seconds) * 1000)

    screenshot_path = capture_screenshot(page, "stage_b-export-log-timeout", SCREENSHOT_DIR)
    if seen_task and last_task is not None:
        record_step(
            summary,
            "stage_b_poll_export_log",
            "FAIL",
            page=page,
            reason_code="EXPORT_LOG_STATUS_TIMEOUT",
            screenshot_path=screenshot_path,
            extra={"matched_task_name": last_task["task_name"], "status_value": last_task["status_value"]},
        )
        raise ExportFlowError("Export-log task did not reach completed state before timeout.", "EXPORT_LOG_STATUS_TIMEOUT")
    record_step(summary, "stage_b_poll_export_log", "FAIL", page=page, reason_code="EXPORT_LOG_TASK_NOT_FOUND", screenshot_path=screenshot_path)
    raise ExportFlowError("No matching export-log task could be found for the current keyword export.", "EXPORT_LOG_TASK_NOT_FOUND")


def download_from_export_log(page, task: dict[str, Any], download_dir: Path, summary: dict[str, Any]) -> dict[str, Any]:
    row_locator = page.locator("table").nth(int(task["table_index"])).locator("tbody tr").nth(int(task["row_index"]))
    download_button = find_first_visible(row_locator, EXPORT_DOWNLOAD_BUTTON_SELECTORS, timeout_ms=1500)
    if download_button is None:
        screenshot_path = capture_screenshot(page, "stage_b-download-button-missing", SCREENSHOT_DIR)
        record_step(
            summary,
            "stage_b_download_export",
            "FAIL",
            page=page,
            reason_code="EXPORT_DOWNLOAD_BUTTON_NOT_VISIBLE",
            screenshot_path=screenshot_path,
            extra={"matched_task_name": task.get("task_name", ""), "status_value": task.get("status_value", "")},
        )
        raise ExportFlowError("Download button is not visible for the completed export-log task.", "EXPORT_DOWNLOAD_BUTTON_NOT_VISIBLE")

    expected_prefix = f"keyword-export-{slugify(task.get('task_name') or summary['context']['keyword'])}-{time.strftime('%Y%m%d_%H%M%S')}"
    try:
        with page.expect_download(timeout=summary["download_timeout_ms"]) as download_info:
            guarded_click(
                page,
                download_button,
                "stage_b_click_download",
                summary,
                not_visible_reason="EXPORT_DOWNLOAD_BUTTON_NOT_VISIBLE",
                click_failure_reason="UNEXPECTED_MODAL_BLOCKING_ACTION",
                preserve_texts=("下载",),
            )
        download = download_info.value
        suffix = Path(download.suggested_filename or "").suffix or ".xlsx"
        download_dir.mkdir(parents=True, exist_ok=True)
        target_path = ensure_within_repo(download_dir / f"{expected_prefix}{suffix}", "download_target_path")
        download.save_as(str(target_path))
        validation = validate_downloaded_file(target_path, expected_prefix)
        validation["suggested_filename"] = download.suggested_filename
        record_step(summary, "stage_b_download_export", "PASS", page=page, extra=validation)
        return validation
    except PlaywrightTimeoutError as exc:
        screenshot_path = capture_screenshot(page, "stage_b-download-timeout", SCREENSHOT_DIR)
        record_step(
            summary,
            "stage_b_download_export",
            "FAIL",
            page=page,
            reason_code="EXPORT_FILE_NOT_DOWNLOADED",
            screenshot_path=screenshot_path,
            extra={"error": str(exc), "matched_task_name": task.get("task_name", "")},
        )
        raise ExportFlowError("Download event was not triggered before timeout.", "EXPORT_FILE_NOT_DOWNLOADED") from exc


def build_target_tokens(context, args: argparse.Namespace, selected_row_text: str) -> list[str]:
    tokens = [
        str(args.task_name or "").strip(),
        str(context.keyword or "").strip(),
        str(context.site or "").strip(),
        str(context.days or "").strip(),
        str(selected_row_text or "").strip(),
    ]
    return [token for token in tokens if token]


def keyword_result_surface_ready(page) -> bool:
    export_button = page.locator("button").filter(has_text="导出明细")
    checkbox_locator = page.locator("input[type='checkbox']")
    return export_button.count() > 0 and checkbox_locator.count() > 0 and not login_required(page)


def prepare_keyword_result_page(page, context, month: str | None, summary: dict[str, Any]) -> dict[str, Any]:
    del month
    target_url = build_keyword_miner_url(context)
    page.goto(target_url, wait_until="domcontentloaded", timeout=90000)
    wait_for_page_open(page)
    guard = guard_page(page, "stage_a_open_keyword_result", preserve_texts=("导出", "前往查看", "我的导出"))
    record_step(summary, "stage_a_open_keyword_result", "PASS", page=page, extra={"target_url": target_url, "guard": guard})
    if login_required(page):
        raise ExportFlowError(
            "SellerSprite keyword result route redirected to login/auth surface before export could be triggered.",
            SELLERSPRITE_AUTH_REQUIRED,
        )
    deadline = time.time() + 20
    while time.time() < deadline:
        if keyword_result_surface_ready(page):
            record_step(summary, "stage_a_validate_keyword_result_surface", "PASS", page=page)
            return {"target_url": target_url, "guard": guard}
        guard_page(page, "stage_a_wait_keyword_result_surface", preserve_texts=("导出", "前往查看", "我的导出"))
        page.wait_for_timeout(1000)

    screenshot_path = capture_screenshot(page, "stage_a-keyword-result-unavailable", SCREENSHOT_DIR)
    record_step(
        summary,
        "stage_a_validate_keyword_result_surface",
        "FAIL",
        page=page,
        reason_code=KEYWORD_RESULT_ROUTE_UNAVAILABLE,
        screenshot_path=screenshot_path,
        extra={"target_url": target_url},
    )
    raise ExportFlowError("SellerSprite v3 keyword result surface was not ready for export actions.", KEYWORD_RESULT_ROUTE_UNAVAILABLE)


def locate_result_row_checkbox(page, row_index: int, summary: dict[str, Any]):
    row_checkboxes = page.locator(".cell .el-checkbox")
    checkbox_count = row_checkboxes.count()
    if checkbox_count <= 1:
        screenshot_path = capture_screenshot(page, "stage_a-result-checkbox-missing", SCREENSHOT_DIR)
        record_step(
            summary,
            "stage_a_locate_result_row",
            "FAIL",
            page=page,
            reason_code=KEYWORD_RESULT_ROW_NOT_FOUND,
            screenshot_path=screenshot_path,
        )
        raise ExportFlowError("No checkbox is visible on the keyword result surface.", KEYWORD_RESULT_ROW_NOT_FOUND)
    target_index = min(max(int(row_index), 1), checkbox_count - 1)
    target = row_checkboxes.nth(target_index)
    try:
        target.wait_for(state="visible", timeout=10000)
    except Exception as exc:
        screenshot_path = capture_screenshot(page, "stage_a-result-checkbox-timeout", SCREENSHOT_DIR)
        record_step(
            summary,
            "stage_a_locate_result_row",
            "FAIL",
            page=page,
            reason_code=RESULT_ROW_CHECKBOX_NOT_VISIBLE,
            screenshot_path=screenshot_path,
            extra={"checkbox_count": checkbox_count, "target_index": target_index, "error": str(exc)},
        )
        raise ExportFlowError("Result-row checkbox did not become available in time.", RESULT_ROW_CHECKBOX_NOT_VISIBLE) from exc
    return target, {"checkbox_count": checkbox_count, "target_checkbox_index": target_index}


def locate_export_trigger(page):
    locator = page.locator("button").filter(has_text="导出明细")
    if locator.count():
        return locator.first
    return find_first_visible(page, RESULT_EXPORT_BUTTON_SELECTORS, timeout_ms=1500)


def locate_export_trigger(page):
    locator = page.locator("button").filter(has_text="\u5bfc\u51fa\u660e\u7ec6")
    if locator.count():
        for index in range(locator.count()):
            candidate = locator.nth(index)
            if not locator_is_disabled(candidate):
                return candidate
        return locator.first
    return find_first_visible(page, RESULT_EXPORT_BUTTON_SELECTORS, timeout_ms=1500)


def handle_export_confirmation(page, summary: dict[str, Any], dialog_events: list[dict[str, Any]]):
    deadline = time.time() + 20
    while time.time() < deadline:
        if "/v2/export-log" in page.url:
            wait_after_export_log_jump(page)
            record_step(summary, "stage_a_enter_export_log", "PASS", page=page, extra={"route": page.url, "via": "direct_navigation"})
            return page

        dialog_info = dialog_snapshot(page)
        confirm_button = find_first_visible(page, EXPORT_DIALOG_CONFIRM_SELECTORS, timeout_ms=1000)
        if dialog_info or confirm_button is not None:
            if confirm_button is None:
                screenshot_path = capture_screenshot(page, "stage_a-export-dialog-no-confirm", SCREENSHOT_DIR)
                record_step(
                    summary,
                    "stage_a_handle_export_dialog",
                    "FAIL",
                    page=page,
                    reason_code="EXPORT_CONFIRM_BUTTON_NOT_VISIBLE",
                    screenshot_path=screenshot_path,
                    extra={"dialog": dialog_info},
                )
                raise ExportFlowError("Export confirmation dialog is visible but no stable forward-view button was found.", "EXPORT_CONFIRM_BUTTON_NOT_VISIBLE")

            popup_page = None
            try:
                wait_before_click(page)
                with page.expect_popup(timeout=5000) as popup_info:
                    confirm_button.click(timeout=10000)
                popup_page = popup_info.value
            except PlaywrightTimeoutError:
                wait_before_click(page)
                confirm_button.click(timeout=10000)
            except Exception as exc:
                screenshot_path = capture_screenshot(page, "stage_a-export-dialog-click-failed", SCREENSHOT_DIR)
                record_step(
                    summary,
                    "stage_a_handle_export_dialog",
                    "FAIL",
                    page=page,
                    reason_code="UNEXPECTED_MODAL_BLOCKING_ACTION",
                    screenshot_path=screenshot_path,
                    extra={"dialog": dialog_info, "error": str(exc)},
                )
                raise ExportFlowError("Export confirmation dialog could not be completed.", "UNEXPECTED_MODAL_BLOCKING_ACTION") from exc

            if popup_page is not None:
                popup_page.wait_for_load_state("domcontentloaded", timeout=90000)
                wait_after_export_log_jump(popup_page)
                record_step(summary, "stage_a_enter_export_log", "PASS", page=popup_page, extra={"route": popup_page.url, "via": "popup"})
                return popup_page

            wait_after_confirm(page)
            if "/v2/export-log" in page.url:
                wait_after_export_log_jump(page)
                record_step(summary, "stage_a_enter_export_log", "PASS", page=page, extra={"route": page.url, "via": "same_tab"})
                return page

            page.goto(EXPORT_LOG_URL, wait_until="domcontentloaded", timeout=90000)
            wait_after_export_log_jump(page)
            record_step(summary, "stage_a_enter_export_log", "PASS", page=page, extra={"route": page.url, "via": "forced_navigation"})
            return page

        if dialog_events:
            screenshot_path = capture_screenshot(page, "stage_a-unexpected-dialog", SCREENSHOT_DIR)
            record_step(
                summary,
                "stage_a_handle_export_dialog",
                "FAIL",
                page=page,
                reason_code="UNEXPECTED_MODAL_BLOCKING_ACTION",
                screenshot_path=screenshot_path,
                extra={"dialog_event": dialog_events[-1]},
            )
            raise ExportFlowError("Unexpected modal blocked the export action.", "UNEXPECTED_MODAL_BLOCKING_ACTION")

        guard_page(page, "stage_a_wait_export_dialog", preserve_texts=("前往查看", "我的导出"))
        page.wait_for_timeout(1000)

    screenshot_path = capture_screenshot(page, "stage_a-export-dialog-timeout", SCREENSHOT_DIR)
    record_step(summary, "stage_a_handle_export_dialog", "FAIL", page=page, reason_code="EXPORT_DIALOG_NOT_VISIBLE", screenshot_path=screenshot_path)
    raise ExportFlowError("SellerSprite export confirmation dialog did not appear in time.", "EXPORT_DIALOG_NOT_VISIBLE")


def task_recency_key(value: str) -> int:
    text = str(value or "")
    compact_matches = re.findall(r"(20\d{6})-(\d{6})", text)
    if compact_matches:
        date_part, time_part = compact_matches[-1]
        return int(f"{date_part}{time_part}")
    datetime_matches = re.findall(r"(20\d{2})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?", text)
    if datetime_matches:
        year, month, day, hour, minute, second = datetime_matches[-1]
        return int(f"{year}{month}{day}{hour}{minute}{second or '00'}")
    return 0


def find_export_task(page, target_tokens: list[str]) -> dict[str, Any] | None:
    tables = extract_export_log_tables(page)
    selected: dict[str, Any] | None = None
    best_rank: tuple[int, int] = (-1, -1)
    for table in tables:
        rows = table.get("rows", [])
        for row in rows:
            cells = [clean_visible_text(str(item)) for item in row.get("cells", [])]
            row_text = clean_visible_text(str(row.get("rowText", "")))
            if not row_text:
                continue
            task_name_match = re.search(r"((?:KeywordHistory|Competitor)-[A-Za-z0-9()._-]+)", row_text, re.IGNORECASE)
            task_name = task_name_match.group(1) if task_name_match else next(
                (
                    cell
                    for cell in cells
                    if cell and cell not in {"最新", "-"} and re.search(r"[A-Za-z0-9]{4,}", cell)
                ),
                row_text[:160],
            )
            status_value = next(
                (
                    cell
                    for cell in cells
                    if any(
                        normalize_text(marker) in normalize_text(cell)
                        for marker in STATUS_DONE_MARKERS + STATUS_PROGRESS_MARKERS + STATUS_FAIL_MARKERS
                    )
                ),
                "",
            )
            current_score = row_score(task_name + " " + row_text, target_tokens)
            if "keywordhistory" in normalize_text(task_name):
                current_score += 5
            recency = task_recency_key(task_name + " " + row_text)
            current_rank = (current_score, recency)
            if current_score <= 0:
                continue
            if current_rank > best_rank:
                selected = {
                    "table_index": int(table.get("tableIndex", 0)),
                    "row_index": int(row.get("rowIndex", 0)),
                    "task_name": task_name,
                    "status_value": status_value,
                    "row_text": row_text,
                }
                best_rank = current_rank
    return selected


def poll_until_export_ready(page, summary: dict[str, Any], target_tokens: list[str], max_wait_seconds: int, poll_interval_seconds: int) -> dict[str, Any]:
    deadline = time.time() + int(max_wait_seconds)
    poll_interval_seconds = ensure_min_poll_interval(poll_interval_seconds)
    seen_task = False
    last_task: dict[str, Any] | None = None
    while time.time() < deadline:
        guard_page(page, "stage_b_export_log_poll", preserve_texts=("下载", "前往查看"))
        if login_required(page):
            raise ExportFlowError("SellerSprite redirected export-log to login/auth surface.", EXPORT_LOG_REDIRECTED_TO_LOGIN)

        task = find_export_task(page, target_tokens)
        if task is None:
            record_step(summary, "stage_b_poll_export_log", "WAIT", page=page, extra={"matched_task_name": "", "status_value": ""})
        else:
            seen_task = True
            last_task = task
            summary["matched_task_name"] = task["task_name"]
            summary["matched_status_value"] = task["status_value"]
            record_step(
                summary,
                "stage_b_poll_export_log",
                "WAIT",
                page=page,
                extra={"matched_task_name": task["task_name"], "status_value": task["status_value"]},
            )
            kind = status_kind(task["status_value"])
            if kind == "done":
                return task
            if kind == "fail":
                raise ExportFlowError(f"Export-log task entered a failed state: {task['status_value']}", EXPORT_LOG_STATUS_FAILED)

        if time.time() + poll_interval_seconds >= deadline:
            break
        page.reload(wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(poll_interval_seconds * 1000)

    screenshot_path = capture_screenshot(page, "stage_b-export-log-timeout", SCREENSHOT_DIR)
    if seen_task and last_task is not None:
        record_step(
            summary,
            "stage_b_poll_export_log",
            "FAIL",
            page=page,
            reason_code="EXPORT_LOG_STATUS_TIMEOUT",
            screenshot_path=screenshot_path,
            extra={"matched_task_name": last_task["task_name"], "status_value": last_task["status_value"]},
        )
        raise ExportFlowError("Export-log task did not reach completed state before timeout.", "EXPORT_LOG_STATUS_TIMEOUT")
    record_step(summary, "stage_b_poll_export_log", "FAIL", page=page, reason_code="EXPORT_LOG_TASK_NOT_FOUND", screenshot_path=screenshot_path)
    raise ExportFlowError("No matching export-log task could be found for the current keyword export.", "EXPORT_LOG_TASK_NOT_FOUND")


def download_from_export_log(page, task: dict[str, Any], download_dir: Path, summary: dict[str, Any]) -> dict[str, Any]:
    row_locator = page.locator("table").nth(int(task["table_index"])).locator("tbody tr").nth(int(task["row_index"]))
    download_button = find_first_visible(row_locator, EXPORT_DOWNLOAD_BUTTON_SELECTORS, timeout_ms=1500)
    if download_button is None:
        screenshot_path = capture_screenshot(page, "stage_b-download-button-missing", SCREENSHOT_DIR)
        record_step(
            summary,
            "stage_b_download_export",
            "FAIL",
            page=page,
            reason_code="EXPORT_DOWNLOAD_BUTTON_NOT_VISIBLE",
            screenshot_path=screenshot_path,
            extra={"matched_task_name": task.get("task_name", ""), "status_value": task.get("status_value", "")},
        )
        raise ExportFlowError("Download button is not visible for the matched export-log task.", "EXPORT_DOWNLOAD_BUTTON_NOT_VISIBLE")

    fallback_stem = f"keywordhistory-{slugify(task.get('task_name') or summary['context']['keyword'])}"
    required_name_tokens = [
        "KeywordHistory",
        slugify(summary["context"]["keyword"]),
        str(summary["context"]["site"] or "").upper(),
    ]
    try:
        with page.expect_download(timeout=summary["download_timeout_ms"]) as download_info:
            guarded_click(
                page,
                download_button,
                "stage_b_click_download",
                summary,
                not_visible_reason="EXPORT_DOWNLOAD_BUTTON_NOT_VISIBLE",
                click_failure_reason="UNEXPECTED_MODAL_BLOCKING_ACTION",
                preserve_texts=("下载",),
            )
        download = download_info.value
        download_dir.mkdir(parents=True, exist_ok=True)
        target_name = safe_download_filename(download.suggested_filename or "", fallback_stem)
        target_path = ensure_within_repo(download_dir / target_name, "download_target_path")
        download.save_as(str(target_path))
        validation = validate_downloaded_file(target_path, required_name_tokens, download.suggested_filename or "")
        validation["suggested_filename"] = download.suggested_filename
        record_step(summary, "stage_b_download_export", "PASS", page=page, extra=validation)
        return validation
    except PlaywrightTimeoutError as exc:
        screenshot_path = capture_screenshot(page, "stage_b-download-timeout", SCREENSHOT_DIR)
        record_step(
            summary,
            "stage_b_download_export",
            "FAIL",
            page=page,
            reason_code="EXPORT_FILE_NOT_DOWNLOADED",
            screenshot_path=screenshot_path,
            extra={"error": str(exc), "matched_task_name": task.get("task_name", "")},
        )
        raise ExportFlowError("Download event did not fire before timeout.", "EXPORT_FILE_NOT_DOWNLOADED") from exc


def build_target_tokens(context, args: argparse.Namespace, selected_row_text: str) -> list[str]:
    tokens = [
        "KeywordHistory",
        slugify(context.keyword),
        str(context.keyword or "").strip(),
        str(context.site or "").strip().upper(),
        str(args.task_name or "").strip(),
    ]
    if selected_row_text:
        tokens.append(slugify(selected_row_text)[:80])
    return [token for token in tokens if token]


def main() -> int:
    args = parse_args()
    context = resolve_context_from_namespace(args, require_direction_id=False)
    log_dir = Path(args.log_dir).expanduser()
    if not log_dir.is_absolute():
        log_dir = ROOT / log_dir
    log_dir = ensure_within_repo(log_dir, "log_dir")
    download_dir = Path(args.download_dir).expanduser() if args.download_dir else DOWNLOADS_ROOT / time.strftime("%Y%m%d_%H%M%S")
    if not download_dir.is_absolute():
        download_dir = ROOT / download_dir
    download_dir = ensure_within_repo(download_dir, "download_dir")
    log_dir.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "timestamp": iso_now(),
        "module": "sellersprite_keyword_export_flow",
        "status": "HOLD",
        "reason_code": "",
        "message": "",
        "current_step": "",
        "context": {
            "run_name": context.run_name,
            "direction_id": context.direction_id,
            "keyword": context.keyword,
            "category_hint": context.category_hint,
            "site": context.site,
            "days": context.days,
            "context_source": context.context_source,
        },
        "task_name_hint": str(args.task_name or "").strip(),
        "result_row_index": int(args.result_row_index),
        "download_timeout_ms": int(args.download_timeout_seconds) * 1000,
        "download_dir": str(download_dir),
        "steps": [],
        "dialog_events": [],
        "screenshots": [],
    }

    page = None
    context_browser = None
    browser = None
    playwright_instance = None
    try:
        playwright_instance = sync_playwright().start()
        context_browser, browser, execution_mode, warning = launch_context(playwright_instance, args)
        summary["execution_mode"] = execution_mode
        if warning:
            summary["persistent_launch_warning"] = warning

        page = context_browser.pages[0] if context_browser.pages else context_browser.new_page()
        current_step: dict[str, str] = {"name": "init"}

        def on_dialog(dialog) -> None:
            entry = {
                "timestamp": iso_now(),
                "step_name": current_step["name"],
                "type": dialog.type,
                "message": dialog.message,
                "page_url": page.url if page else "",
            }
            summary["dialog_events"].append(entry)
            try:
                dialog.accept()
            except Exception:
                try:
                    dialog.dismiss()
                except Exception:
                    pass

        page.on("dialog", on_dialog)

        current_step["name"] = "stage_a_prepare_keyword_result"
        prepare_keyword_result_page(page, context, args.month, summary)
        if login_required(page):
            raise ExportFlowError(
                "SellerSprite keyword result surface is still on login/auth state after direct v3 routing.",
                SELLERSPRITE_AUTH_REQUIRED,
            )

        row_checkbox, row_meta = locate_result_row_checkbox(page, args.result_row_index, summary)
        summary.update(row_meta)
        row_text = ""
        summary["selected_row_text"] = row_text
        current_step["name"] = "stage_a_select_result_row"
        guarded_click(
            page,
            row_checkbox,
            "stage_a_select_result_row",
            summary,
            not_visible_reason=RESULT_ROW_CHECKBOX_NOT_VISIBLE,
            click_failure_reason="RESULT_PAGE_BLOCKED_BY_OVERLAY",
        )

        export_trigger = locate_export_trigger(page)
        if export_trigger is None:
            screenshot_path = capture_screenshot(page, "stage_a-export-trigger-missing", SCREENSHOT_DIR)
            record_step(summary, "stage_a_trigger_export", "FAIL", page=page, reason_code=EXPORT_TRIGGER_BUTTON_NOT_VISIBLE, screenshot_path=screenshot_path)
            raise ExportFlowError("No stable export trigger button was visible on the keyword result page.", EXPORT_TRIGGER_BUTTON_NOT_VISIBLE)
        summary["export_trigger_disabled"] = locator_is_disabled(export_trigger)

        if args.dry_run:
            summary["status"] = "PASS"
            summary["reason_code"] = "DRY_RUN_ONLY"
            summary["message"] = "Dry-run validated the stabilized result-page preparation, row selection, and export trigger discovery."
            record_step(summary, "stage_a_trigger_export", "PASS", page=page, extra={"dry_run": True, **row_meta})
        else:
            if summary["export_trigger_disabled"]:
                snapshot = page_identity(page)
                screenshot_path = capture_screenshot(page, "stage_a-export-trigger-disabled", SCREENSHOT_DIR)
                reason_code = SELLERSPRITE_AUTH_REQUIRED if snapshot.get("guest_markers") else "RESULT_PAGE_BLOCKED_BY_OVERLAY"
                record_step(
                    summary,
                    "stage_a_trigger_export",
                    "FAIL",
                    page=page,
                    reason_code=reason_code,
                    screenshot_path=screenshot_path,
                    extra={"guest_markers": snapshot.get("guest_markers", []), **row_meta},
                )
                raise ExportFlowError(
                    "SellerSprite export control is still disabled after row selection; current session appears guest-gated or not export-enabled.",
                    reason_code,
                )
            current_step["name"] = "stage_a_trigger_export"
            guarded_click(
                page,
                export_trigger,
                "stage_a_trigger_export",
                summary,
                not_visible_reason=EXPORT_TRIGGER_BUTTON_NOT_VISIBLE,
                click_failure_reason="RESULT_PAGE_BLOCKED_BY_OVERLAY",
                preserve_texts=("导出", "前往查看"),
            )

            current_step["name"] = "stage_a_handle_export_dialog"
            page = handle_export_confirmation(page, summary, summary["dialog_events"])

            current_step["name"] = "stage_b_open_export_log"
            record_step(summary, "stage_b_open_export_log", "PASS", page=page)
            if login_required(page):
                raise ExportFlowError("SellerSprite export-log route redirected to login/auth surface.", EXPORT_LOG_REDIRECTED_TO_LOGIN)

            current_step["name"] = "stage_b_poll_export_log"
            target_tokens = build_target_tokens(context, args, row_text)
            task = poll_until_export_ready(
                page,
                summary,
                target_tokens=target_tokens,
                max_wait_seconds=int(args.max_wait_seconds),
                poll_interval_seconds=ensure_min_poll_interval(int(args.poll_interval_seconds)),
            )

            current_step["name"] = "stage_b_download_export"
            download_meta = download_from_export_log(page, task, download_dir, summary)
            summary["download"] = download_meta
            summary["matched_task_name"] = task.get("task_name", "")
            summary["matched_status_value"] = task.get("status_value", "")
            summary["status"] = "PASS"
            summary["reason_code"] = "PASS"
            summary["message"] = "Keyword export flow completed: result-page export triggered, export-log task completed, and file download was validated."

        summary["final_page"] = page_identity(page)
        summary["screenshots"].append(capture_screenshot(page, "keyword-export-flow-final", SCREENSHOT_DIR))
    except ExportFlowError as exc:
        summary["status"] = "HOLD"
        summary["reason_code"] = exc.reason_code
        summary["message"] = str(exc)
        if page is not None:
            summary["final_page"] = page_identity(page)
            screenshot_path = capture_screenshot(page, "keyword-export-flow-failure", SCREENSHOT_DIR)
            summary["screenshots"].append(screenshot_path)
            record_step(summary, summary.get("current_step", "flow_failure"), "FAIL", page=page, reason_code=exc.reason_code, screenshot_path=screenshot_path)
    except KeywordChainError as exc:
        summary["status"] = "HOLD"
        summary["reason_code"] = exc.reason_code
        summary["message"] = str(exc)
    except Exception as exc:
        summary["status"] = "HOLD"
        summary["reason_code"] = "KEYWORD_EXPORT_FLOW_UNHANDLED_ERROR"
        summary["message"] = str(exc)
        if page is not None:
            summary["final_page"] = page_identity(page)
            screenshot_path = capture_screenshot(page, "keyword-export-flow-unhandled", SCREENSHOT_DIR)
            summary["screenshots"].append(screenshot_path)
            record_step(summary, summary.get("current_step", "flow_failure"), "FAIL", page=page, reason_code=summary["reason_code"], screenshot_path=screenshot_path)
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
        if playwright_instance is not None:
            try:
                playwright_instance.stop()
            except Exception:
                pass

    if summary["reason_code"] in REQUIRED_REASON_CODES or summary["reason_code"] in {
        SELLERSPRITE_AUTH_REQUIRED,
        EXPORT_LOG_REDIRECTED_TO_LOGIN,
        EXPORT_LOG_STATUS_FAILED,
        RESULT_ROW_CHECKBOX_NOT_VISIBLE,
        EXPORT_TRIGGER_BUTTON_NOT_VISIBLE,
        KEYWORD_RESULT_TABLE_NOT_VISIBLE,
    }:
        append_jsonl(RUN_FAILURE_FILE, summary)
    write_json_atomic(LATEST_LOG_FILE, summary)
    append_jsonl(RUN_HISTORY_FILE, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
