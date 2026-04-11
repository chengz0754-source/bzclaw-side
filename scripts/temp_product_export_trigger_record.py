from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from benchmark_chain_common import PROFILE_DIR, ensure_within_repo, resolve_context_from_namespace
from export_benchmark_competitors import (
    BenchmarkExportFlowError,
    SELLERSPRITE_AUTH_REQUIRED,
    checkbox_selected,
    handle_optional_export_dialog,
    launch_context,
    record_step,
    require_visible,
    wait_after_query,
    wait_before_click,
    wait_for_page_open,
)
from keyword_chain_common import ROOT
from sellersprite_overlay_guard import guard_page


PRODUCT_RESEARCH_URL = "https://www.sellersprite.com/v3/product-research"
PRODUCT_QUERY_INPUT_NOT_VISIBLE = "PRODUCT_QUERY_INPUT_NOT_VISIBLE"
PRODUCT_QUERY_BUTTON_NOT_VISIBLE = "PRODUCT_QUERY_BUTTON_NOT_VISIBLE"
PRODUCT_RESULT_CHECKBOX_NOT_VISIBLE = "PRODUCT_RESULT_CHECKBOX_NOT_VISIBLE"
PRODUCT_EXPORT_IMAGE_CHECKBOX_NOT_VISIBLE = "PRODUCT_EXPORT_IMAGE_CHECKBOX_NOT_VISIBLE"
PRODUCT_EXPORT_IMAGE_NOT_SELECTED = "PRODUCT_EXPORT_IMAGE_NOT_SELECTED"
PRODUCT_EXPORT_BUTTON_NOT_VISIBLE = "PRODUCT_EXPORT_BUTTON_NOT_VISIBLE"
PRODUCT_RESULT_ROWS_MISSING = "PRODUCT_RESULT_ROWS_MISSING"
PRODUCT_EXPORT_IMAGE_OPTIONAL_MISSING = "PRODUCT_EXPORT_IMAGE_OPTIONAL_MISSING"
PRODUCT_EXPORT_BUTTON_DISABLED = "PRODUCT_EXPORT_BUTTON_DISABLED"
PRODUCT_AUTH_BLOCK_MARKERS = (
    "未登录",
    "游客",
    "立即登录",
    "主人~ 您当前是游客身份",
    "建议 立即登录 后使用",
)


def build_product_research_url(site_code: str) -> str:
    site = str(site_code or "").strip().upper() or "US"
    return f"{PRODUCT_RESEARCH_URL}?market={site}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal product-research trigger record without any login actions.")
    parser.add_argument("--context-row-index", type=int, default=1)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--site", default=None)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--execution-mode", choices=("auto", "persistent", "storage_state"), default="auto")
    return parser.parse_args()


def product_phrase_match_radio(page):
    return page.locator(".el-radio", has_text="词组匹配").first


def product_keyword_input(page):
    return page.locator("input[placeholder='请输入关键词，多个以英文逗号区分']").nth(1)


def product_start_filter_button(page):
    return page.locator("button", has_text="开始筛选").first


def product_result_rows(page):
    return page.locator(".el-table__body tr")


def product_bulk_checkbox(page):
    return page.locator("div.left > label.el-checkbox").first


def product_export_image_checkbox(page):
    return page.locator(".el-checkbox.export-img .el-checkbox__inner").first


def product_export_button(page):
    return page.locator("button.my-download").first


def product_export_auth_blocked(page) -> bool:
    try:
        body_text = page.locator("body").inner_text(timeout=5000)
    except Exception:
        body_text = ""
    compacted = " ".join(str(body_text or "").split())
    return any(marker in compacted for marker in PRODUCT_AUTH_BLOCK_MARKERS)


def close_one_query_tip(page) -> bool:
    closer = page.locator(".el-icon-circle-close").first
    try:
        if closer.is_visible(timeout=1500):
            closer.click(timeout=3000)
            page.wait_for_timeout(500)
            return True
    except Exception:
        return False
    return False


def prepare_product_query(page, keyword: str, summary: dict[str, Any]) -> None:
    guard_page(page, "product_stage_open_query_surface", preserve_texts=("开始筛选",))
    phrase_radio = require_visible(
        page,
        product_phrase_match_radio(page),
        "product_stage_match_mode",
        summary,
        PRODUCT_QUERY_INPUT_NOT_VISIBLE,
        preserve_texts=("开始筛选",),
    )
    wait_before_click(page)
    phrase_radio.click(timeout=10000)

    keyword_input = require_visible(
        page,
        product_keyword_input(page),
        "product_stage_fill_keyword",
        summary,
        PRODUCT_QUERY_INPUT_NOT_VISIBLE,
        preserve_texts=("开始筛选",),
    )
    wait_before_click(page)
    keyword_input.click(timeout=10000)
    keyword_input.fill(keyword)

    start_button = require_visible(
        page,
        product_start_filter_button(page),
        "product_stage_submit_query",
        summary,
        PRODUCT_QUERY_BUTTON_NOT_VISIBLE,
        preserve_texts=("开始筛选",),
    )
    wait_before_click(page)
    start_button.click(timeout=10000)
    wait_after_query(page)
    page.wait_for_timeout(3000)
    close_one_query_tip(page)


def ensure_product_rows(page, summary: dict[str, Any]) -> int:
    guard_page(page, "product_stage_query_results", preserve_texts=("导出", "导出明细"))
    row_count = product_result_rows(page).count()
    if row_count <= 0:
        raise BenchmarkExportFlowError("Product research result table did not expose any visible rows.", PRODUCT_RESULT_ROWS_MISSING)
    return row_count


def select_product_results(page, summary: dict[str, Any]) -> None:
    checkbox = require_visible(
        page,
        product_bulk_checkbox(page),
        "product_stage_select_rows",
        summary,
        PRODUCT_RESULT_CHECKBOX_NOT_VISIBLE,
        preserve_texts=("导出", "导出明细"),
    )
    for attempt in range(1, 3):
        guard_page(page, f"product_stage_select_rows_attempt_{attempt}", preserve_texts=("导出", "导出明细"))
        wait_before_click(page)
        checkbox.click(timeout=10000, force=True)
        page.wait_for_timeout(800)
        if checkbox_selected(checkbox):
            return
    raise BenchmarkExportFlowError("Product result checkbox could not be selected.", PRODUCT_RESULT_CHECKBOX_NOT_VISIBLE)


def toggle_export_main_image(page, summary: dict[str, Any], required: bool = False) -> bool:
    checkbox_locator = product_export_image_checkbox(page)
    try:
        checkbox_visible = checkbox_locator.is_visible(timeout=1500)
    except Exception:
        checkbox_visible = False
    if checkbox_locator.count() <= 0 or not checkbox_visible:
        if required:
            raise BenchmarkExportFlowError("Product export main-image checkbox is not visible.", PRODUCT_EXPORT_IMAGE_CHECKBOX_NOT_VISIBLE)
        record_step(
            summary,
            "product_stage_toggle_export_image",
            "HOLD",
            page=page,
            reason_code=PRODUCT_EXPORT_IMAGE_OPTIONAL_MISSING,
            extra={"message": "Current session did not expose the export-main-image checkbox."},
        )
        return False
    checkbox = require_visible(
        page,
        checkbox_locator,
        "product_stage_toggle_export_image",
        summary,
        PRODUCT_EXPORT_IMAGE_CHECKBOX_NOT_VISIBLE,
        preserve_texts=("导出", "前往查看"),
    )
    if checkbox_selected(checkbox):
        return True
    wait_before_click(page)
    checkbox.click(timeout=10000, force=True)
    page.wait_for_timeout(800)
    if not checkbox_selected(checkbox):
        raise BenchmarkExportFlowError("Product export main-image checkbox did not stay selected.", PRODUCT_EXPORT_IMAGE_NOT_SELECTED)
    return True


def trigger_product_export(page, summary: dict[str, Any], require_export_image: bool = False) -> dict[str, Any]:
    summary["export_main_image_selected"] = toggle_export_main_image(page, summary, required=require_export_image)
    button = require_visible(
        page,
        product_export_button(page),
        "product_stage_trigger_export",
        summary,
        PRODUCT_EXPORT_BUTTON_NOT_VISIBLE,
        preserve_texts=("导出", "前往查看"),
    )
    wait_before_click(page)
    if button.is_disabled():
        if product_export_auth_blocked(page):
            raise BenchmarkExportFlowError(
                "SellerSprite Product Research export is disabled because the current session is guest-only on the real product page.",
                SELLERSPRITE_AUTH_REQUIRED,
            )
        raise BenchmarkExportFlowError(
            "Product export button stayed disabled after selecting rows on the real product page.",
            PRODUCT_EXPORT_BUTTON_DISABLED,
        )
    button.click(timeout=10000)
    page.wait_for_timeout(2500)
    return handle_optional_export_dialog(page)


def main() -> int:
    args = parse_args()
    context = resolve_context_from_namespace(args, require_direction_id=False)
    summary: dict[str, Any] = {
        "module": "temp_product_export_trigger_record",
        "status": "BLOCKED",
        "reason_code": "",
        "message": "",
        "query_keyword": str(args.keyword or context.keyword).strip(),
        "site": str(args.site or context.site).strip().upper(),
        "final_url": "",
        "page_title": "",
        "execution_mode": "",
    }

    browser = None
    context_browser = None
    try:
        with sync_playwright() as playwright:
            context_browser, browser, execution_mode, warning = launch_context(
                playwright,
                args,
                runtime_replay_surface_family="SELLERSPRITE_PRODUCT_RESEARCH_AUTH",
            )
            summary["execution_mode"] = execution_mode
            if warning:
                summary["execution_warning"] = warning
            page = context_browser.pages[0] if context_browser.pages else context_browser.new_page()
            page.goto(build_product_research_url(summary["site"]), wait_until="domcontentloaded", timeout=90000)
            wait_for_page_open(page)
            prepare_product_query(page, summary["query_keyword"], summary)
            summary["row_count"] = ensure_product_rows(page, summary)
            select_product_results(page, summary)
            follow_action = trigger_product_export(page, summary)
            summary["status"] = "PASS"
            summary["reason_code"] = "PASS"
            summary["message"] = "Real product-research page actions completed up to the export-log handoff."
            summary["follow_action"] = follow_action
            summary["final_url"] = page.url
            summary["page_title"] = page.title()
    except Exception as exc:
        summary["status"] = "BLOCKED"
        summary["reason_code"] = getattr(exc, "reason_code", "TEMP_PRODUCT_TRIGGER_FAILED")
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

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
