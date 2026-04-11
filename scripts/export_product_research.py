from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from benchmark_chain_common import ensure_within_repo, iso_now, log_dir_from_namespace, output_dir_from_namespace, resolve_context_from_namespace
from export_benchmark_competitors import (
    EXPORT_DOWNLOAD_BUTTON_NOT_VISIBLE,
    EXPORT_LOG_STATUS_TIMEOUT,
    EXPORT_LOG_TASK_NOT_FOUND,
    SELLERSPRITE_AUTH_REQUIRED,
    BenchmarkExportFlowError,
    collect_export_tasks,
    export_status_kind,
    launch_context,
    login_required,
    record_step,
    wait_for_page_open,
)
from keyword_chain_common import append_jsonl, write_json_atomic
from parse_product_export_workbook import build_raw_artifact, parse_workbook_rows
from sellersprite_auth_registry import register_auth_incident, replay_meta_from_incident
from sellersprite_auth_replay import load_registry_entry, perform_registered_login_replay, summary_requests_auth_replay
from sellersprite_overlay_guard import capture_screenshot
from temp_product_export_log_record import (
    download_product_export_task,
    ensure_min_poll_interval,
    find_best_product_export_task,
    safe_download_dir,
)
from temp_product_export_trigger_record import (
    PRODUCT_EXPORT_BUTTON_NOT_VISIBLE,
    PRODUCT_QUERY_INPUT_NOT_VISIBLE,
    PRODUCT_QUERY_BUTTON_NOT_VISIBLE,
    PRODUCT_RESULT_CHECKBOX_NOT_VISIBLE,
    PRODUCT_RESULT_ROWS_MISSING,
    PRODUCT_RESEARCH_URL,
    build_product_research_url,
    ensure_product_rows,
    product_export_auth_blocked,
    prepare_product_query,
    select_product_results,
    trigger_product_export,
)


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[1]
RAW_ARTIFACT = "product_research_raw.json"
SCREENSHOT_DIR = ROOT / "playwright" / "screenshots" / "product_chain"
LOG_LATEST = "latest_product_research_run.json"
LOG_HISTORY = "product_research_runs.jsonl"
LOG_FAILURES = "product_research_failures.jsonl"
EXPORT_LOG_URL = "https://www.sellersprite.com/v2/export-log"
PRODUCT_EXPORT_STATUS_FAILED = "PRODUCT_EXPORT_STATUS_FAILED"
PRODUCT_EXPORT_WORKBOOK_PARSE_FAILED = "PRODUCT_EXPORT_WORKBOOK_PARSE_FAILED"
ASIN_PATTERN = re.compile(r"ASIN:\s*([A-Z0-9]{10})", re.IGNORECASE)
PROBE_COMPOSITE_STATE_FILE = "composite_probe_state.json"
PROBE_DIRECT_OWNER_STATE_MODE = "probe_direct_owner_state"


def product_surface_redirected_to_login(page) -> bool:
    current_url = str(getattr(page, "url", "") or "")
    try:
        title = page.title()
    except Exception:
        title = ""
    return "/w/user/signin" in current_url or "/w/user/login" in current_url or "卖家精灵登录" in title


def resolve_probe_owner_state() -> tuple[Path | None, str]:
    try:
        _registry, entry = load_registry_entry("SELLERSPRITE_PRODUCT_RESEARCH_AUTH")
    except Exception as exc:
        return None, f"probe_owner_state_registry_lookup_failed={exc}"
    manifest_raw = str(entry.get("owner_recording_manifest_path", "")).strip()
    if not manifest_raw:
        owner_drop = str(entry.get("owner_recording_drop_path", "")).strip()
        if owner_drop:
            manifest_raw = str(Path(owner_drop) / "recording_manifest.json")
    if not manifest_raw:
        return None, "probe_owner_state_manifest_missing"
    try:
        manifest_path = ensure_within_repo(Path(manifest_raw), "probe_owner_recording_manifest_path")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            return None, "probe_owner_state_manifest_invalid"
        owner_dir_raw = str(manifest.get("owner_recording_dir", manifest_path.parent)).strip()
        owner_dir = ensure_within_repo(Path(owner_dir_raw), "probe_owner_recording_dir")
        composite_path = ensure_within_repo(owner_dir / PROBE_COMPOSITE_STATE_FILE, "probe_composite_state_path")
        if composite_path.exists():
            return composite_path, "probe_state_source=composite_probe_state"
        storage_state_raw = str(manifest.get("storage_state_path", "")).strip()
        if not storage_state_raw:
            return None, "probe_owner_state_storage_state_missing"
        storage_state_path = ensure_within_repo(Path(storage_state_raw), "probe_owner_storage_state_path")
        if storage_state_path.exists():
            return storage_state_path, "probe_state_source=storage_state"
        return None, f"probe_owner_state_not_found={storage_state_path}"
    except Exception as exc:
        return None, f"probe_owner_state_resolution_failed={exc}"


def launch_probe_direct_context(playwright, args: argparse.Namespace) -> tuple[Any, Any, str, str]:
    browser = playwright.chromium.launch(channel="msedge", headless=bool(args.headless))
    warning_parts: list[str] = []
    state_path, warning = resolve_probe_owner_state()
    if warning:
        warning_parts.append(warning)
    if state_path is not None and state_path.exists():
        context_browser = browser.new_context(
            storage_state=str(state_path),
            viewport={"width": 1600, "height": 1400},
            accept_downloads=True,
        )
        return context_browser, browser, PROBE_DIRECT_OWNER_STATE_MODE, "; ".join(warning_parts)
    context_browser = browser.new_context(viewport={"width": 1600, "height": 1400}, accept_downloads=True)
    return context_browser, browser, "guest_context", "; ".join(warning_parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export SellerSprite product-research workbook through the real v3 product page and export-log flow.",
    )
    parser.add_argument("--context-row-index", type=int, default=1)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--direction-id", default=None)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--category-hint", default=None)
    parser.add_argument("--site", default=None)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--sample-top-n", type=int, default=None)
    parser.add_argument("--max-candidate-samples", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--log-dir", default=None)
    parser.add_argument("--download-dir", default=None)
    parser.add_argument("--max-wait-seconds", type=int, default=300)
    parser.add_argument("--poll-interval-seconds", type=int, default=10)
    parser.add_argument("--download-timeout-seconds", type=int, default=90)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execution-mode", choices=("auto", "persistent", "storage_state"), default="auto")
    parser.add_argument("--probe-market-handoff", action="store_true")
    return parser.parse_args()


def persist_run_summary(log_dir: Path, summary: dict[str, Any]) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(log_dir / LOG_LATEST, summary)
    append_jsonl(log_dir / LOG_HISTORY, summary)
    if summary.get("status") != "PASS":
        append_jsonl(log_dir / LOG_FAILURES, summary)


def fail_closed_on_auth(page, summary: dict[str, Any], step_name: str, message: str, redirect_from_url: str, context, execution_mode: str, dry_run: bool) -> None:
    incident = register_auth_incident(
        module_name="product_research",
        step_name=step_name,
        source_script=__file__,
        reason_code=SELLERSPRITE_AUTH_REQUIRED,
        current_url=page.url if page is not None else "",
        redirect_from_url=redirect_from_url,
        page=page,
        run_context={
            "context": context.__dict__,
            "execution_mode": execution_mode,
            "dry_run": dry_run,
        },
    )
    summary.update(replay_meta_from_incident(incident))
    record_step(
        summary,
        step_name,
        "FAIL",
        page=page,
        reason_code=SELLERSPRITE_AUTH_REQUIRED,
        screenshot_path=str(incident.get("screenshot_path", "")).strip(),
        extra={
            "auth_surface_family": incident.get("surface_family", ""),
            "auth_replay_available": incident.get("has_login_replay", False),
        },
    )
    raise BenchmarkExportFlowError(message, SELLERSPRITE_AUTH_REQUIRED)


def poll_until_product_export_ready(
    page,
    baseline_task_names: set[str],
    site: str,
    days: int,
    export_triggered_ts: float,
    max_wait_seconds: int,
    poll_interval_seconds: int,
    summary: dict[str, Any],
) -> dict[str, Any]:
    expected_prefix = f"Product-{site}-Last-{days}-days"
    deadline = time.monotonic() + max_wait_seconds
    locked_task_name = ""

    while time.monotonic() <= deadline:
        page.goto(EXPORT_LOG_URL, wait_until="domcontentloaded", timeout=90000)
        wait_for_page_open(page)
        if login_required(page):
            raise BenchmarkExportFlowError("SellerSprite product export-log redirected to login during polling.", SELLERSPRITE_AUTH_REQUIRED)
        tasks = collect_export_tasks(page)
        if locked_task_name:
            matched = next((task for task in tasks if str(task.get("task_name", "")).strip() == locked_task_name), None)
        else:
            matched = find_best_product_export_task(tasks, baseline_task_names, expected_prefix, export_triggered_ts)
            if matched is not None:
                locked_task_name = str(matched.get("task_name", "")).strip()
        if matched is None:
            record_step(
                summary,
                "product_stage_poll_export_log",
                "WAIT",
                page=page,
                extra={"matched_task_name": "", "status_value": "", "visible_task_count": len(tasks)},
            )
            time.sleep(poll_interval_seconds)
            continue

        summary["matched_task_name"] = locked_task_name or str(matched.get("task_name", "")).strip()
        summary["matched_status_value"] = str(matched.get("status_value", "")).strip()
        status_kind = export_status_kind(summary["matched_status_value"])
        if status_kind == "DONE":
            record_step(
                summary,
                "product_stage_poll_export_log",
                "PASS",
                page=page,
                extra={
                    "matched_task_name": summary["matched_task_name"],
                    "status_value": summary["matched_status_value"],
                    "source_name": matched.get("source_name", ""),
                },
            )
            return matched
        if status_kind == "FAIL":
            raise BenchmarkExportFlowError(
                f"Product export task `{summary['matched_task_name']}` failed with status `{summary['matched_status_value']}`.",
                PRODUCT_EXPORT_STATUS_FAILED,
            )

        record_step(
            summary,
            "product_stage_poll_export_log",
            "WAIT",
            page=page,
            extra={
                "matched_task_name": summary["matched_task_name"],
                "status_value": summary["matched_status_value"],
                "source_name": matched.get("source_name", ""),
            },
        )
        time.sleep(poll_interval_seconds)

    if not locked_task_name:
        raise BenchmarkExportFlowError("No new product export task could be locked in 我的导出 before timeout.", EXPORT_LOG_TASK_NOT_FOUND)
    raise BenchmarkExportFlowError(
        f"Product export task `{locked_task_name}` did not complete before timeout.",
        EXPORT_LOG_STATUS_TIMEOUT,
    )


def build_summary_base(context, args: argparse.Namespace, download_dir: Path) -> dict[str, Any]:
    return {
        "timestamp": iso_now(),
        "module": "product_research",
        "status": "BLOCKED",
        "reason_code": "",
        "message": "",
        "context_source": context.context_source,
        "运行名称": context.run_name,
        "方向ID": context.direction_id,
        "方向词": context.keyword,
        "站点": context.site,
        "attempted_url": build_product_research_url(context.site),
        "final_url": "",
        "page_title": "",
        "query_keyword": context.keyword,
        "raw_artifact_path": "",
        "raw_item_count": 0,
        "dry_run": bool(args.dry_run),
        "headless": bool(args.headless),
        "execution_mode": "",
        "execution_warning": "",
        "download_dir": str(download_dir),
        "workbook_download_path": "",
        "matched_task_name": "",
        "matched_status_value": "",
        "auth_incident_path": "",
        "auth_surface_family": "",
        "auth_replay_available": False,
        "auth_replay_snippet_path": "",
        "auth_owner_recording_drop_path": "",
        "auth_replay_attempted": False,
        "auth_replay_result": {},
        "visible_market_entry_count": 0,
        "same_session_probe_requested": bool(args.probe_market_handoff),
        "same_session_market_probe": {},
    }


def extract_visible_market_entry_overrides(page, max_rows: int) -> dict[str, dict[str, str]]:
    overrides: dict[str, dict[str, str]] = {}
    data_rows = page.locator(".el-table__body tr.el-table__row")
    row_count = min(data_rows.count(), max(max_rows, 0))
    for index in range(row_count):
        row = data_rows.nth(index)
        try:
            row_text = row.inner_text(timeout=3000)
        except Exception:
            row_text = ""
        asin_match = ASIN_PATTERN.search(str(row_text or ""))
        if not asin_match:
            continue
        asin = asin_match.group(1).strip().upper()
        if not asin:
            continue

        product_source_url = ""
        try:
            product_links = row.locator("a[href*='amazon.com/dp/']").evaluate_all(
                "els => els.map(el => el.href || '').filter(Boolean)"
            )
            if isinstance(product_links, list) and product_links:
                product_source_url = str(product_links[0]).strip()
        except Exception:
            product_source_url = ""

        expanded_row = row.locator("xpath=following-sibling::tr[1]").first
        market_analysis_url = ""
        category_path = ""
        candidate_market_name = ""
        try:
            market_links = expanded_row.locator("a[href*='/v2/market-research']").evaluate_all(
                "els => els.map(el => ({text:(el.innerText||'').trim(), href:el.href||''}))"
            )
            if isinstance(market_links, list) and market_links:
                market_analysis_url = str(market_links[0].get("href", "")).strip()
        except Exception:
            market_analysis_url = ""
        try:
            category_parts = expanded_row.locator(".product-type a.type").evaluate_all(
                "els => els.map(el => (el.innerText || '').trim()).filter(Boolean)"
            )
            if isinstance(category_parts, list) and category_parts:
                category_path = " > ".join(str(part).strip() for part in category_parts if str(part).strip())
                candidate_market_name = str(category_parts[-1]).strip()
        except Exception:
            category_path = ""
            candidate_market_name = ""

        if not any((market_analysis_url, product_source_url, category_path, candidate_market_name)):
            continue
        overrides[asin] = {
            "product_source_url": product_source_url,
            "market_analysis_url": market_analysis_url,
            "category_path": category_path,
            "candidate_market_name": candidate_market_name,
        }
    return overrides


def merge_visible_page_overrides(items: list[dict[str, Any]], visible_overrides: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        asin = str(item.get("asin", "")).strip().upper()
        override = visible_overrides.get(asin, {})
        merged_item = dict(item)
        for source_key in ("product_source_url", "market_analysis_url", "category_path", "candidate_market_name"):
            if not str(merged_item.get(source_key, "")).strip() and str(override.get(source_key, "")).strip():
                merged_item[source_key] = str(override.get(source_key, "")).strip()
        merged.append(merged_item)
    return merged


def normalize_binding_text(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def title_binding_tokens(title: str) -> list[str]:
    tokens = [token for token in re.findall(r"[a-z0-9]+", str(title or "").casefold()) if len(token) >= 4]
    unique: list[str] = []
    for token in tokens:
        if token not in unique:
            unique.append(token)
    return unique[:8]


def safe_page_title(page) -> str:
    try:
        return str(page.title() or "").strip()
    except Exception:
        return ""


def dump_session_storage(page) -> dict[str, str]:
    try:
        payload = page.evaluate(
            """
            () => {
              const out = {};
              try {
                for (let i = 0; i < window.sessionStorage.length; i += 1) {
                  const key = window.sessionStorage.key(i);
                  if (key !== null) {
                    out[key] = window.sessionStorage.getItem(key) || "";
                  }
                }
              } catch (error) {}
              return out;
            }
            """
        )
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in payload.items():
        text_key = str(key or "").strip()
        if not text_key:
            continue
        result[text_key] = str(value or "")
    return result


def rank_sort_key(item: dict[str, Any]) -> tuple[int, str]:
    text = str(item.get("rank", "")).strip()
    match = re.search(r"\d+", text)
    if not match:
        return (10**9, str(item.get("asin", "")).strip().upper())
    return (int(match.group(0)), str(item.get("asin", "")).strip().upper())


def select_same_session_probe_item(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [item for item in items if isinstance(item, dict) and str(item.get("market_analysis_url", "")).strip()]
    if not candidates:
        return None
    return sorted(candidates, key=rank_sort_key)[0]


def find_visible_probe_row(page, probe_item: dict[str, Any], row_count: int):
    data_rows = page.locator(".el-table__body tr.el-table__row")
    selected_asin = str(probe_item.get("asin", "")).strip().upper()
    selected_title = str(probe_item.get("title", "")).strip()
    title_tokens = title_binding_tokens(selected_title)
    exact_title_norm = normalize_binding_text(selected_title)
    best_row = None
    best_score = 0
    best_index = -1

    for index in range(row_count):
        row = data_rows.nth(index)
        try:
            row_text = str(row.inner_text(timeout=3000) or "")
        except Exception:
            row_text = ""
        row_text_upper = row_text.upper()
        row_text_norm = normalize_binding_text(row_text)
        score = 0
        if selected_asin and selected_asin in row_text_upper:
            score += 100
        if exact_title_norm and exact_title_norm in row_text_norm:
            score += 40
        score += 10 * sum(1 for token in title_tokens if token in row_text_norm)
        try:
            product_links = row.locator("a[href*='amazon.']").evaluate_all("els => els.map(el => el.href || '').filter(Boolean)")
        except Exception:
            product_links = []
        if selected_asin and isinstance(product_links, list) and any(selected_asin in str(href).upper() for href in product_links):
            score += 60
        if score > best_score:
            best_score = score
            best_row = row
            best_index = index

    return best_row, best_score, best_index


def locate_visible_market_analysis_link(row, preferred_href: str) -> tuple[Any | None, str]:
    expanded_row = row.locator("xpath=following-sibling::tr[1]").first
    links = expanded_row.locator("a[href*='/v2/market-research']")
    link_count = links.count()
    if link_count <= 0:
        return None, ""
    chosen_link = links.first
    chosen_href = ""
    normalized_preferred = str(preferred_href or "").strip()
    for index in range(link_count):
        candidate = links.nth(index)
        try:
            href = str(candidate.get_attribute("href") or "").strip()
        except Exception:
            href = ""
        if normalized_preferred and href == normalized_preferred:
            chosen_link = candidate
            chosen_href = href
            break
        if not chosen_href and href:
            chosen_link = candidate
            chosen_href = href
    return chosen_link, chosen_href


def run_same_session_market_probe(context_browser, product_page, summary: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    probe: dict[str, Any] = {
        "selected_product_research_url": str(product_page.url or "").strip(),
        "selected_visible_market_analysis_href": "",
        "sample_asin": "",
        "sample_title": "",
        "row_visible": False,
        "market_analysis_link_visible": False,
        "same_session_probe_status": "BLOCKED",
        "same_session_probe_stage": "",
        "same_session_probe_final_url": str(product_page.url or "").strip(),
        "same_session_probe_final_title": safe_page_title(product_page),
        "session_storage_dump": dump_session_storage(product_page),
        "market_page_session_storage_dump": {},
        "popup_or_new_page_observed": False,
        "opener_chain": "not_attempted",
        "workbook_download_attempted": False,
        "login_redirect_timing": "",
        "capture_timestamp": iso_now(),
    }
    probe_item = select_same_session_probe_item(items)
    if probe_item is None:
        probe["same_session_probe_stage"] = PRODUCT_MARKET_ANALYSIS_LINK_NOT_VISIBLE
        return probe

    probe["sample_asin"] = str(probe_item.get("asin", "")).strip().upper()
    probe["sample_title"] = str(probe_item.get("title", "")).strip()
    probe["selected_visible_market_analysis_href"] = str(probe_item.get("market_analysis_url", "")).strip()
    probe["selected_candidate_market_name"] = str(probe_item.get("candidate_market_name", "")).strip()
    probe["selected_market_path"] = str(probe_item.get("category_path", "")).strip()

    data_rows = product_page.locator(".el-table__body tr.el-table__row")
    row_count = data_rows.count()
    probe["visible_row_count"] = row_count
    if row_count <= 0:
        probe["same_session_probe_stage"] = PRODUCT_RESULT_ROWS_MISSING
        return probe

    best_row, best_score, best_index = find_visible_probe_row(product_page, probe_item, row_count)
    probe["row_rebind_score"] = best_score
    probe["row_index"] = best_index
    if best_row is None or best_score < 60:
        probe["same_session_probe_stage"] = PRODUCT_RESULT_ROWS_MISSING
        return probe

    probe["row_visible"] = True
    market_link, chosen_href = locate_visible_market_analysis_link(best_row, probe["selected_visible_market_analysis_href"])
    if market_link is None:
        probe["same_session_probe_stage"] = PRODUCT_MARKET_ANALYSIS_LINK_NOT_VISIBLE
        return probe

    probe["market_analysis_link_visible"] = True
    probe["selected_visible_market_analysis_href"] = chosen_href or probe["selected_visible_market_analysis_href"]
    market_page = None
    try:
        try:
            with context_browser.expect_page(timeout=15000) as popup_info:
                market_link.click(timeout=10000)
            market_page = popup_info.value
            market_page.wait_for_load_state("domcontentloaded", timeout=90000)
            probe["popup_or_new_page_observed"] = True
            probe["opener_chain"] = "popup_from_product_result_page"
        except Exception:
            with product_page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                market_link.click(timeout=10000)
            market_page = product_page
            probe["popup_or_new_page_observed"] = False
            probe["opener_chain"] = "same_tab_navigation_from_product_result_page"

        market_page.wait_for_timeout(2000)
        probe["same_session_probe_final_url"] = str(market_page.url or "").strip()
        probe["same_session_probe_final_title"] = safe_page_title(market_page)
        probe["market_page_session_storage_dump"] = dump_session_storage(market_page)
        if "/w/user/login" in probe["same_session_probe_final_url"]:
            probe["same_session_probe_stage"] = "MARKET_LOGIN_REDIRECT_AFTER_CLICK"
            probe["login_redirect_timing"] = "after_click"
            return probe
        probe["same_session_probe_status"] = "PASS"
        probe["same_session_probe_stage"] = "MARKET_HANDOFF_PAGE_OPENED"
        return probe
    finally:
        if market_page is not None and market_page is not product_page:
            try:
                market_page.close()
            except Exception:
                pass


def run_once(args: argparse.Namespace, *, replay_attempted: bool = False, replay_result: dict[str, Any] | None = None) -> tuple[int, dict[str, Any], Path]:
    context = resolve_context_from_namespace(args, require_direction_id=False)
    output_dir = output_dir_from_namespace(args)
    log_dir = log_dir_from_namespace(args)
    download_dir = safe_download_dir(args.download_dir)
    raw_artifact_path = ensure_within_repo(output_dir / RAW_ARTIFACT, "raw_artifact_path")
    poll_interval_seconds = ensure_min_poll_interval(args.poll_interval_seconds)
    summary = build_summary_base(context, args, download_dir)
    summary["auth_replay_attempted"] = replay_attempted
    summary["auth_replay_result"] = replay_result or {}

    browser = None
    context_browser = None
    try:
        if args.max_wait_seconds <= 0:
            raise BenchmarkExportFlowError("--max-wait-seconds must be > 0.", EXPORT_LOG_STATUS_TIMEOUT)

        with sync_playwright() as playwright:
            if args.probe_market_handoff:
                context_browser, browser, execution_mode, warning = launch_probe_direct_context(playwright, args)
            else:
                context_browser, browser, execution_mode, warning = launch_context(
                    playwright,
                    args,
                    runtime_replay_surface_family="SELLERSPRITE_PRODUCT_RESEARCH_AUTH",
                )
            summary["execution_mode"] = execution_mode
            summary["execution_warning"] = warning
            try:
                page = context_browser.pages[0] if context_browser.pages else context_browser.new_page()
                export_log_page = context_browser.new_page()
                baseline_task_names: set[str] = set()

                page.goto(build_product_research_url(context.site), wait_until="domcontentloaded", timeout=90000)
                wait_for_page_open(page)
                summary["page_title"] = page.title()
                if product_surface_redirected_to_login(page):
                    if args.probe_market_handoff:
                        summary["same_session_market_probe"] = {
                            "selected_product_research_url": build_product_research_url(context.site),
                            "selected_visible_market_analysis_href": "",
                            "sample_asin": "",
                            "sample_title": "",
                            "row_visible": False,
                            "market_analysis_link_visible": False,
                            "same_session_probe_status": "BLOCKED",
                            "same_session_probe_stage": "STEP1_OPEN_QUERY_SURFACE_AUTH_REQUIRED",
                            "same_session_probe_final_url": str(page.url or "").strip(),
                            "same_session_probe_final_title": safe_page_title(page),
                            "session_storage_dump": dump_session_storage(page),
                            "market_page_session_storage_dump": {},
                            "popup_or_new_page_observed": False,
                            "opener_chain": "not_started_auth_before_query_surface",
                            "workbook_download_attempted": False,
                            "login_redirect_timing": "before_probe_start",
                            "capture_timestamp": iso_now(),
                        }
                    fail_closed_on_auth(
                        page,
                        summary,
                        "product_stage_open_query_surface",
                        "SellerSprite product-research page requires authentication.",
                        PRODUCT_RESEARCH_URL,
                        context,
                        execution_mode,
                        bool(args.dry_run),
                    )

                prepare_product_query(page, context.keyword, summary)
                summary["final_url"] = page.url
                if product_surface_redirected_to_login(page):
                    if args.probe_market_handoff:
                        summary["same_session_market_probe"] = {
                            "selected_product_research_url": str(page.url or "").strip(),
                            "selected_visible_market_analysis_href": "",
                            "sample_asin": "",
                            "sample_title": "",
                            "row_visible": False,
                            "market_analysis_link_visible": False,
                            "same_session_probe_status": "BLOCKED",
                            "same_session_probe_stage": "STEP1_QUERY_RESULTS_AUTH_REQUIRED",
                            "same_session_probe_final_url": str(page.url or "").strip(),
                            "same_session_probe_final_title": safe_page_title(page),
                            "session_storage_dump": dump_session_storage(page),
                            "market_page_session_storage_dump": {},
                            "popup_or_new_page_observed": False,
                            "opener_chain": "not_started_auth_after_query",
                            "workbook_download_attempted": False,
                            "login_redirect_timing": "before_probe_start",
                            "capture_timestamp": iso_now(),
                        }
                    fail_closed_on_auth(
                        page,
                        summary,
                        "product_stage_query_results",
                        "SellerSprite product-research query redirected to login.",
                        PRODUCT_RESEARCH_URL,
                        context,
                        execution_mode,
                        bool(args.dry_run),
                    )

                row_count = ensure_product_rows(page, summary)
                record_step(summary, "product_stage_query_results", "PASS", page=page, extra={"row_count": row_count})
                visible_market_overrides = extract_visible_market_entry_overrides(page, row_count)
                summary["visible_market_entry_count"] = len(visible_market_overrides)
                select_product_results(page, summary)
                record_step(summary, "product_stage_select_rows", "PASS", page=page, extra={"selection_scope": "ALL_VISIBLE_RESULTS"})
                if product_export_auth_blocked(page):
                    fail_closed_on_auth(
                        page,
                        summary,
                        "product_stage_prepare_export",
                        "SellerSprite Product Research export stayed guest-only after rows were selected on the real product page.",
                        PRODUCT_RESEARCH_URL,
                        context,
                        execution_mode,
                        bool(args.dry_run),
                    )
                export_log_page.goto(EXPORT_LOG_URL, wait_until="domcontentloaded", timeout=90000)
                wait_for_page_open(export_log_page)
                if login_required(export_log_page):
                    fail_closed_on_auth(
                        export_log_page,
                        summary,
                        "product_stage_export_log_baseline",
                        "SellerSprite export-log page requires authentication before product export.",
                        EXPORT_LOG_URL,
                        context,
                        execution_mode,
                        bool(args.dry_run),
                    )
                baseline_tasks = collect_export_tasks(export_log_page)
                baseline_task_names = {str(task.get("task_name", "")).strip() for task in baseline_tasks if str(task.get("task_name", "")).strip()}
                record_step(summary, "product_stage_export_log_baseline", "PASS", page=export_log_page, extra={"baseline_task_count": len(baseline_task_names)})

                if args.dry_run:
                    summary["status"] = "PASS"
                    summary["reason_code"] = "DRY_RUN_ONLY"
                    summary["message"] = "Dry-run validated the real product-research query surface and export controls."
                    persist_run_summary(log_dir, summary)
                    return 0, summary, log_dir

                export_triggered_ts = time.time()
                try:
                    follow_action = trigger_product_export(page, summary)
                except BenchmarkExportFlowError as exc:
                    if exc.reason_code == SELLERSPRITE_AUTH_REQUIRED:
                        fail_closed_on_auth(
                            page,
                            summary,
                            "product_stage_trigger_export",
                            str(exc),
                            PRODUCT_RESEARCH_URL,
                            context,
                            execution_mode,
                            bool(args.dry_run),
                        )
                    raise
                record_step(summary, "product_stage_trigger_export", "PASS", page=page, extra={"follow_action": follow_action})

                matched_task = poll_until_product_export_ready(
                    export_log_page,
                    baseline_task_names,
                    context.site,
                    context.days,
                    export_triggered_ts,
                    args.max_wait_seconds,
                    poll_interval_seconds,
                    summary,
                )

                workbook_path, file_info = download_product_export_task(
                    export_log_page,
                    matched_task,
                    download_dir,
                    args.download_timeout_seconds * 1000,
                )
                record_step(summary, "product_stage_download_export", "PASS", page=export_log_page, extra={"task_name": matched_task.get("task_name", ""), "download": file_info})
                summary["workbook_download_path"] = str(workbook_path)
                try:
                    sheet_name, headers, items = parse_workbook_rows(workbook_path)
                except Exception as exc:
                    raise BenchmarkExportFlowError(
                        f"Downloaded product workbook could not be parsed into raw artifact: {workbook_path.name}",
                        PRODUCT_EXPORT_WORKBOOK_PARSE_FAILED,
                    ) from exc
                items = merge_visible_page_overrides(items, visible_market_overrides)

                raw_artifact = build_raw_artifact(context, workbook_path, sheet_name, headers, items, page.url, page.title())
                if args.probe_market_handoff:
                    try:
                        same_session_probe = run_same_session_market_probe(context_browser, page, summary, items)
                    except Exception as exc:
                        same_session_probe = {
                            "selected_product_research_url": str(page.url or "").strip(),
                            "selected_visible_market_analysis_href": "",
                            "sample_asin": "",
                            "sample_title": "",
                            "row_visible": False,
                            "market_analysis_link_visible": False,
                            "same_session_probe_status": "BLOCKED",
                            "same_session_probe_stage": "SAME_SESSION_PROBE_UNHANDLED_ERROR",
                            "same_session_probe_final_url": str(page.url or "").strip(),
                            "same_session_probe_final_title": safe_page_title(page),
                            "session_storage_dump": dump_session_storage(page),
                            "market_page_session_storage_dump": {},
                            "popup_or_new_page_observed": False,
                            "opener_chain": "probe_unhandled_error",
                            "workbook_download_attempted": False,
                            "login_redirect_timing": "",
                            "capture_timestamp": iso_now(),
                            "unhandled_error": str(exc),
                        }
                    summary["same_session_market_probe"] = same_session_probe
                    raw_artifact["same_session_market_probe"] = same_session_probe
                output_dir.mkdir(parents=True, exist_ok=True)
                write_json_atomic(raw_artifact_path, raw_artifact)

                summary["status"] = "PASS"
                summary["reason_code"] = "PASS"
                summary["message"] = "Real SellerSprite product-research workbook was downloaded, parsed, and persisted successfully."
                summary["raw_artifact_path"] = str(raw_artifact_path)
                summary["raw_item_count"] = len(items)
                summary["download_file"] = file_info
                summary["response_meta"] = {
                    "sheet_name": sheet_name,
                    "row_count": len(items),
                    "header_count": len(headers),
                }
            finally:
                if context_browser is not None:
                    context_browser.close()
                if browser is not None:
                    browser.close()
    except BenchmarkExportFlowError as exc:
        summary["status"] = "BLOCKED"
        summary["reason_code"] = exc.reason_code
        summary["message"] = str(exc)
    except Exception as exc:
        summary["status"] = "BLOCKED"
        summary["reason_code"] = "PRODUCT_RESEARCH_UNHANDLED_ERROR"
        summary["message"] = str(exc)

    if summary["status"] != "PASS":
        try:
            if context_browser is not None and context_browser.pages:
                screenshot_path = capture_screenshot(context_browser.pages[0], "product-stage-failure", SCREENSHOT_DIR)
                summary.setdefault("screenshots", []).append(screenshot_path)
        except Exception:
            pass

    persist_run_summary(log_dir, summary)
    return (0 if summary["status"] == "PASS" else 2), summary, log_dir


def main() -> int:
    args = parse_args()
    exit_code, summary, log_dir = run_once(args)
    if exit_code != 0 and summary_requests_auth_replay(summary):
        replay_result = perform_registered_login_replay(
            surface_family=str(summary.get("auth_surface_family", "")).strip(),
            module_name="product_research",
            trigger_reason_code=str(summary.get("reason_code", "")).strip(),
            trigger_summary=summary,
        )
        if replay_result.get("status") == "PASS":
            args.execution_mode = str(replay_result.get("execution_mode_override", "")).strip() or "storage_state"
            exit_code, summary, log_dir = run_once(args, replay_attempted=True, replay_result=replay_result)
        else:
            summary["auth_replay_attempted"] = True
            summary["auth_replay_result"] = replay_result
            persist_run_summary(log_dir, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
