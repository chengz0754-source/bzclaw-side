from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import Error, TimeoutError as PlaywrightTimeoutError, sync_playwright
from benchmark_chain_common import STEP1_SEED_FILE, latest_generated_files
from keyword_chain_common import PROFILE_DIR, REPLAY_PROFILE_DIR, STORAGE_STATE_PATH, preferred_sellersprite_profile_dir
from sellersprite_route_router import PRODUCT_IDEA_VALIDATION, resolve_route_decision
from sellersprite_auth_registry import auth_surface_detected, is_auth_reason, register_auth_incident, replay_meta_from_incident
from sellersprite_auth_replay import launch_runtime_seeded_persistent_context, perform_registered_login_replay
from temp_product_export_trigger_record import build_product_research_url


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "runs" / "manual" / "10_market"
DEFAULT_LOG_DIR = ROOT / "logs" / "market_exports"
CURRENT_GOAL_RELATIVE = Path("inputs/selection_run_current/00_选品运行目标与边界.csv")
CURRENT_ENTRY_RELATIVE = Path("inputs/selection_run_current/01_市场入口与筛选参数.csv")
MARKET_URL = "https://www.sellersprite.com/v2/market-research"
STEP1_MARKET_HANDOFF_FILE = "13_step1_market_handoff.jsonl"
STEP1_MARKET_SESSION_BUNDLE_FILE = "13a_step1_market_session_bundle.json"
CSV_READ_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk")
DEFAULT_KEYWORD = "Squeeze Toys"
DEFAULT_SITE = "US"
DEFAULT_DAYS = 30
DEFAULT_NEW_PRODUCT_WINDOW = "6"
DEFAULT_SAMPLE_TOP_N = 100
DEFAULT_HEAD_TOP_N = 10
ENTRY_MODE_AUTO = "auto"
ENTRY_MODE_KEYWORD_SEARCH = "keyword_search"
ENTRY_MODE_PRODUCT_MARKET_ANALYSIS = "product_market_analysis"
EXECUTION_MODE_AUTO = "auto"
EXECUTION_MODE_PERSISTENT = "persistent"
EXECUTION_MODE_STORAGE_STATE = "storage_state"

SITE_LABELS = {
    "US": "美国站(com)",
    "JP": "日本站(co.jp)",
    "UK": "英国站(co.uk)",
    "DE": "德国站(de)",
    "FR": "法国站(fr)",
    "IT": "意大利(it)",
    "ES": "西班牙(es)",
    "CA": "加拿大(ca)",
    "IN": "印度站(in)",
    "MX": "墨西哥(mx)",
}

NEW_PRODUCT_WINDOW_VALUES = {
    "1": "1",
    "1m": "1",
    "1mo": "1",
    "3": "3",
    "3m": "3",
    "3mo": "3",
    "6": "6",
    "6m": "6",
    "6mo": "6",
    "12": "12",
    "12m": "12",
    "12mo": "12",
}

NEW_PRODUCT_DAYS_TO_WINDOW = {
    "30": "1",
    "90": "3",
    "180": "6",
    "365": "12",
}

HEAD_TOP_VALUES = {"3", "5", "10", "20"}

SEARCH_INPUT_SELECTOR = "input[name='departmentKeyword']"
NEW_PRODUCT_SELECT_SELECTOR = "select[name='newReleaseNumSelect']"
HEAD_TOP_SELECT_SELECTOR = "select[name='topNSelect']"

FILTER_BUTTON_TEXT = "筛选市场"
EXPORT_BUTTON_TEXT = "导出Excel"
MONTH_LAST_30_LABEL = "最近30天"
NO_RESULT_MARKERS = ("很抱歉，暂无结果", "暂无结果")
PRODUCT_MARKET_ENTRY_ROW_MISSING = "PRODUCT_MARKET_ENTRY_ROW_MISSING"
STEP1_MARKET_HANDOFF_OBJECT_MISSING = "STEP1_MARKET_HANDOFF_OBJECT_MISSING"
STEP1_MARKET_SESSION_BUNDLE_MISSING = "STEP1_MARKET_SESSION_BUNDLE_MISSING"
STEP1_MARKET_SESSION_BUNDLE_INJECTION_FAILED = "STEP1_MARKET_SESSION_BUNDLE_INJECTION_FAILED"
STEP1_MARKET_HANDOFF_REBIND_FAILED = "STEP1_MARKET_HANDOFF_REBIND_FAILED"
PRODUCT_MARKET_ANALYSIS_LINK_NOT_VISIBLE = "PRODUCT_MARKET_ANALYSIS_LINK_NOT_VISIBLE"
MARKET_LOGIN_REDIRECT_BEFORE_REBIND = "MARKET_LOGIN_REDIRECT_BEFORE_REBIND"
MARKET_LOGIN_REDIRECT_AFTER_CLICK = "MARKET_LOGIN_REDIRECT_AFTER_CLICK"
MARKET_WORKBOOK_PASS = "MARKET_WORKBOOK_PASS"


class MarketExportError(RuntimeError):
    def __init__(self, message: str, reason_code: str = "MARKET_EXPORT_ERROR", details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.details = details or {}


class ExportExecutionError(MarketExportError):
    def __init__(self, message: str, attempts: list[dict[str, Any]], reason_code: str = "MARKET_EXPORT_ERROR", details: dict[str, Any] | None = None) -> None:
        super().__init__(message, reason_code=reason_code, details=details)
        self.attempts = attempts


@dataclass
class ExportArgs:
    keyword: str
    site: str
    days: int
    new_product_window: str
    sample_top_n: int
    head_top_n: int
    output_dir: Path
    log_dir: Path
    dry_run: bool
    max_attempts: int
    retry_wait_seconds: float
    execution_mode: str
    context_row_index: int | None
    run_name: str
    context_source: str
    task_id: str
    direction_id: str
    route_type: str
    step3_policy: str
    entry_mode: str
    market_entry_url: str
    entry_source_step: str
    market_handoff_path: str
    market_session_bundle_path: str
    selected_product_research_url: str
    product_seed_csv: str
    selected_sample_id: str
    selected_sample_asin: str
    selected_sample_title: str
    selected_candidate_market_name: str
    selected_market_path: str
    handoff_capture_status: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a SellerSprite market report using the local dedicated automation profile.",
    )
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--site", default=None)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--new-product-window", default=None)
    parser.add_argument("--sample-top-n", type=int, default=None)
    parser.add_argument("--head-top-n", type=int, default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--context-row-index", type=int, default=None)
    parser.add_argument(
        "--entry-mode",
        choices=(ENTRY_MODE_AUTO, ENTRY_MODE_KEYWORD_SEARCH, ENTRY_MODE_PRODUCT_MARKET_ANALYSIS),
        default=ENTRY_MODE_AUTO,
        help="Use product-sample market-analysis entry for product-form words instead of naked keyword search.",
    )
    parser.add_argument("--market-analysis-url", default=None)
    parser.add_argument("--market-handoff-jsonl", default=None)
    parser.add_argument("--market-session-bundle-json", default=None)
    parser.add_argument("--product-seed-csv", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Only resolve controls, naming, and logs; do not launch Playwright.")
    parser.add_argument("--max-attempts", type=int, default=2, help="Maximum export attempts, including the first attempt.")
    parser.add_argument("--retry-wait-seconds", type=float, default=3.0)
    parser.add_argument("--execution-mode", choices=(EXECUTION_MODE_AUTO, EXECUTION_MODE_PERSISTENT, EXECUTION_MODE_STORAGE_STATE), default=EXECUTION_MODE_AUTO)
    return parser.parse_args()


def ensure_within_repo(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise MarketExportError(f"{label} is outside the repo root: {resolved}")
    return resolved


def load_csv_rows(path: Path) -> list[list[str]]:
    raw_bytes = path.read_bytes()
    decode_errors: list[str] = []
    for encoding in CSV_READ_ENCODINGS:
        try:
            return list(csv.reader(raw_bytes.decode(encoding).splitlines()))
        except UnicodeDecodeError as exc:
            decode_errors.append(f"{encoding}@{exc.start}:{exc.reason}")
    detail = " | ".join(decode_errors) or "unknown decode failure"
    raise MarketExportError(f"Failed to read CSV with supported encodings: {path} | {detail}")


def load_current_input_context(row_index: int) -> dict[str, str]:
    if row_index <= 0:
        raise MarketExportError("--context-row-index must be >= 1.")

    goal_path = ROOT / CURRENT_GOAL_RELATIVE
    entry_path = ROOT / CURRENT_ENTRY_RELATIVE
    if not goal_path.exists():
        raise MarketExportError(f"Current goal CSV is missing: {goal_path}")
    if not entry_path.exists():
        raise MarketExportError(f"Current market entry CSV is missing: {entry_path}")

    goal_rows = load_csv_rows(goal_path)
    entry_rows = load_csv_rows(entry_path)
    if len(goal_rows) < 2:
        raise MarketExportError(f"Current goal CSV has no data row: {goal_path}")
    if len(entry_rows) <= row_index:
        raise MarketExportError(
            f"--context-row-index {row_index} is out of range for {entry_path}; available rows: {max(len(entry_rows) - 1, 0)}"
        )

    goal_map = {header: goal_rows[1][idx] if idx < len(goal_rows[1]) else "" for idx, header in enumerate(goal_rows[0])}
    entry_map = {header: entry_rows[row_index][idx] if idx < len(entry_rows[row_index]) else "" for idx, header in enumerate(entry_rows[0])}
    return {
        "goal_run_name": goal_map.get("运行名称", "").strip(),
        "entry_run_name": entry_map.get("运行名称", "").strip(),
        "direction_id": entry_map.get("方向ID", "").strip(),
        "keyword": entry_map.get("方向词", "").strip(),
        "site": entry_map.get("站点", "").strip().upper(),
        "days": entry_map.get("时间范围_天", "").strip(),
        "new_product_days": entry_map.get("新品定义_天", "").strip(),
        "sample_top_n": entry_map.get("样本数前N", "").strip(),
        "head_top_n": entry_map.get("头部商品前N", "").strip(),
    }


def normalize_new_product_window(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized not in NEW_PRODUCT_WINDOW_VALUES:
        raise MarketExportError(
            "--new-product-window must be one of: 1, 3, 6, 12, 1m, 3m, 6m, 12m."
        )
    return NEW_PRODUCT_WINDOW_VALUES[normalized]


def normalize_new_product_window_from_days(value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        return DEFAULT_NEW_PRODUCT_WINDOW
    if normalized not in NEW_PRODUCT_DAYS_TO_WINDOW:
        raise MarketExportError(
            f"Current input 新品定义_天 is not supported by the verified SellerSprite flow: {normalized}. "
            "Use 30, 90, 180, or 365, or pass --new-product-window explicitly."
        )
    return NEW_PRODUCT_DAYS_TO_WINDOW[normalized]


def parse_int_value(raw_value: str | int | None, field_name: str) -> int:
    try:
        return int(raw_value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise MarketExportError(f"{field_name} must be an integer value, got: {raw_value!r}") from exc


def load_csv_dict_rows(path: Path) -> list[dict[str, str]]:
    raw_bytes = path.read_bytes()
    decode_errors: list[str] = []
    for encoding in CSV_READ_ENCODINGS:
        try:
            return list(csv.DictReader(raw_bytes.decode(encoding).splitlines()))
        except UnicodeDecodeError as exc:
            decode_errors.append(f"{encoding}@{exc.start}:{exc.reason}")
    detail = " | ".join(decode_errors) or "unknown decode failure"
    raise MarketExportError(f"Failed to read CSV rows with supported encodings: {path} | {detail}")


def latest_step1_seed_paths(seed_path_override: str | None = None) -> list[Path]:
    if seed_path_override:
        seed_path = Path(seed_path_override).expanduser()
        if not seed_path.is_absolute():
            seed_path = ROOT / seed_path
        return [ensure_within_repo(seed_path, "product_seed_csv")]
    return latest_generated_files(STEP1_SEED_FILE)


def latest_step1_handoff_paths(handoff_path_override: str | None = None) -> list[Path]:
    if handoff_path_override:
        handoff_path = Path(handoff_path_override).expanduser()
        if not handoff_path.is_absolute():
            handoff_path = ROOT / handoff_path
        return [ensure_within_repo(handoff_path, "market_handoff_jsonl")]
    return latest_generated_files(STEP1_MARKET_HANDOFF_FILE)


def resolve_session_bundle_path(bundle_path_override: str | None, handoff_path: Path) -> Path | None:
    if str(bundle_path_override or "").strip():
        bundle_path = Path(str(bundle_path_override).strip()).expanduser()
        if not bundle_path.is_absolute():
            bundle_path = ROOT / bundle_path
        bundle_path = ensure_within_repo(bundle_path, "market_session_bundle_json")
        return bundle_path if bundle_path.exists() else None
    sibling = ensure_within_repo(handoff_path.with_name(STEP1_MARKET_SESSION_BUNDLE_FILE), "market_session_bundle_json")
    return sibling if sibling.exists() else None


def load_json_record(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise MarketExportError(f"Expected a JSON object in {path}.", reason_code=STEP1_MARKET_SESSION_BUNDLE_INJECTION_FAILED)
    return payload


def load_jsonl_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def resolve_product_market_entry(
    *,
    task_id: str,
    keyword: str,
    site: str,
    run_name: str,
    direction_id: str,
    handoff_path_override: str | None,
    bundle_path_override: str | None,
    seed_path_override: str | None,
    direct_market_analysis_url: str | None,
) -> dict[str, Any]:
    if str(direct_market_analysis_url or "").strip():
        return {
            "entry_source_step": "DIRECT_MARKET_ANALYSIS_URL",
            "market_entry_url": str(direct_market_analysis_url).strip(),
            "market_handoff_path": "",
            "market_session_bundle_path": "",
            "selected_product_research_url": "",
            "product_seed_csv": "",
            "selected_sample_id": "",
            "selected_sample_asin": "",
            "selected_sample_title": "",
            "selected_candidate_market_name": "",
            "selected_market_path": "",
            "handoff_capture_status": "DIRECT_URL_ONLY",
        }

    handoff_paths = latest_step1_handoff_paths(handoff_path_override)
    if not handoff_paths:
        raise MarketExportError(
            "Product-form STEP3 requires a materialized STEP1 market handoff object before rerun, but no handoff object was found.",
            reason_code=STEP1_MARKET_HANDOFF_OBJECT_MISSING,
        )

    normalized_task_id = task_id.strip().casefold()
    normalized_keyword = keyword.strip().casefold()
    normalized_site = site.strip().casefold()
    normalized_run_name = run_name.strip().casefold()
    normalized_direction_id = direction_id.strip().casefold()
    best_match: tuple[int, dict[str, Any], Path] | None = None
    for handoff_path in handoff_paths:
        rows = load_jsonl_records(handoff_path)
        for row in rows:
            capture_status = str(row.get("handoff_capture_status", "")).strip()
            market_href = str(row.get("selected_visible_market_analysis_href", "")).strip()
            score = 0
            if capture_status == "PASS":
                score += 20
            if market_href:
                score += 20
            if normalized_task_id and str(row.get("task_id", "")).strip().casefold() == normalized_task_id:
                score += 100
            if normalized_direction_id and str(row.get("direction_id", "")).strip().casefold() == normalized_direction_id:
                score += 50
            if normalized_run_name and str(row.get("run_name", "")).strip().casefold() == normalized_run_name:
                score += 25
            if normalized_keyword and str(row.get("keyword", "")).strip().casefold() == normalized_keyword:
                score += 10
            if normalized_site and str(row.get("site", "")).strip().casefold() == normalized_site:
                score += 10
            if score <= 0:
                continue
            if best_match is None or score > best_match[0]:
                best_match = (score, row, handoff_path)

    if best_match is None:
        raise MarketExportError(
            "Product-form STEP3 requires a matching STEP1 market handoff object, but no matching handoff row was found for the current context.",
            reason_code=STEP1_MARKET_HANDOFF_OBJECT_MISSING,
        )

    selected = best_match[1]
    seed_path = Path(str(selected.get("source_seed_csv_path", "")).strip()) if str(selected.get("source_seed_csv_path", "")).strip() else None
    if seed_path is None or not seed_path.exists():
        candidate_paths = latest_step1_seed_paths(seed_path_override)
        if not candidate_paths:
            raise MarketExportError(
                "STEP1 market handoff object was found, but its companion STEP1 seed CSV is missing.",
                reason_code=STEP1_MARKET_HANDOFF_OBJECT_MISSING,
            )
        seed_path = candidate_paths[0]
    else:
        seed_path = ensure_within_repo(seed_path, "product_seed_csv")

    if not str(selected.get("selected_visible_market_analysis_href", "")).strip():
        raise MarketExportError(
            "STEP1 market handoff object exists, but the captured visible market-analysis href is empty.",
            reason_code=STEP1_MARKET_HANDOFF_OBJECT_MISSING,
        )

    return {
        "entry_source_step": "STEP1_MARKET_HANDOFF_OBJECT",
        "market_entry_url": str(selected.get("selected_visible_market_analysis_href", "")).strip(),
        "market_handoff_path": str(best_match[2]),
        "market_session_bundle_path": str(resolve_session_bundle_path(bundle_path_override, best_match[2]) or ""),
        "selected_product_research_url": str(selected.get("selected_product_research_url", "")).strip(),
        "product_seed_csv": str(seed_path),
        "selected_sample_id": str(selected.get("sample_id", "")).strip(),
        "selected_sample_asin": str(selected.get("sample_asin", "")).strip().upper(),
        "selected_sample_title": str(selected.get("sample_title", "")).strip(),
        "selected_candidate_market_name": str(selected.get("selected_candidate_market_name", "")).strip(),
        "selected_market_path": str(selected.get("selected_market_path", "")).strip(),
        "handoff_capture_status": str(selected.get("handoff_capture_status", "")).strip() or "UNKNOWN",
    }


def resolve_args(namespace: argparse.Namespace) -> ExportArgs:
    context: dict[str, str] = {}
    if namespace.context_row_index is not None:
        context = load_current_input_context(namespace.context_row_index)
        context_source = f"inputs/selection_run_current/01 row {namespace.context_row_index}"
    else:
        context_source = "script defaults"

    keyword = (namespace.keyword or context.get("keyword") or DEFAULT_KEYWORD).strip()
    site = (namespace.site or context.get("site") or DEFAULT_SITE).strip().upper()
    days = namespace.days if namespace.days is not None else parse_int_value(context.get("days") or DEFAULT_DAYS, "时间范围_天")
    if namespace.new_product_window is not None:
        new_product_window = normalize_new_product_window(namespace.new_product_window)
    elif namespace.context_row_index is not None:
        new_product_window = normalize_new_product_window_from_days(context.get("new_product_days", ""))
    else:
        new_product_window = DEFAULT_NEW_PRODUCT_WINDOW
    sample_top_n = (
        namespace.sample_top_n
        if namespace.sample_top_n is not None
        else parse_int_value(context.get("sample_top_n") or DEFAULT_SAMPLE_TOP_N, "样本数前N")
    )
    head_top_n = (
        namespace.head_top_n
        if namespace.head_top_n is not None
        else parse_int_value(context.get("head_top_n") or DEFAULT_HEAD_TOP_N, "头部商品前N")
    )
    output_dir = Path(namespace.output_dir).expanduser()
    log_dir = Path(namespace.log_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    if not log_dir.is_absolute():
        log_dir = ROOT / log_dir
    run_name = context.get("entry_run_name") or context.get("goal_run_name") or ""
    direction_id = context.get("direction_id", "").strip()
    route_decision = resolve_route_decision(
        context_row_index=namespace.context_row_index or 1,
        run_name=run_name,
        direction_id=direction_id,
        keyword=keyword,
        site=site,
    )
    task_id = str(route_decision.get("任务ID", "")).strip()
    route_type = str(route_decision.get("purpose_type", PRODUCT_IDEA_VALIDATION)).strip() or PRODUCT_IDEA_VALIDATION
    step3_policy = str(route_decision.get("step3_policy", "OPTIONAL")).strip() or "OPTIONAL"
    requested_entry_mode = str(getattr(namespace, "entry_mode", ENTRY_MODE_AUTO) or ENTRY_MODE_AUTO).strip() or ENTRY_MODE_AUTO
    if requested_entry_mode == ENTRY_MODE_AUTO:
        entry_mode = ENTRY_MODE_PRODUCT_MARKET_ANALYSIS if route_type == PRODUCT_IDEA_VALIDATION else ENTRY_MODE_KEYWORD_SEARCH
    else:
        entry_mode = requested_entry_mode

    market_entry = {
        "entry_source_step": "",
        "market_entry_url": "",
        "market_handoff_path": "",
        "market_session_bundle_path": "",
        "selected_product_research_url": "",
        "product_seed_csv": "",
        "selected_sample_id": "",
        "selected_sample_asin": "",
        "selected_sample_title": "",
        "selected_candidate_market_name": "",
        "selected_market_path": "",
        "handoff_capture_status": "",
    }
    if entry_mode == ENTRY_MODE_PRODUCT_MARKET_ANALYSIS:
        market_entry = resolve_product_market_entry(
            task_id=task_id,
            keyword=keyword,
            site=site,
            run_name=run_name,
            direction_id=direction_id,
            handoff_path_override=getattr(namespace, "market_handoff_jsonl", None),
            bundle_path_override=getattr(namespace, "market_session_bundle_json", None),
            seed_path_override=getattr(namespace, "product_seed_csv", None),
            direct_market_analysis_url=getattr(namespace, "market_analysis_url", None),
        )
    return ExportArgs(
        keyword=keyword,
        site=site,
        days=days,
        new_product_window=new_product_window,
        sample_top_n=sample_top_n,
        head_top_n=head_top_n,
        output_dir=ensure_within_repo(output_dir, "output_dir"),
        log_dir=ensure_within_repo(log_dir, "log_dir"),
        dry_run=bool(namespace.dry_run),
        max_attempts=int(namespace.max_attempts),
        retry_wait_seconds=float(namespace.retry_wait_seconds),
        execution_mode=str(getattr(namespace, "execution_mode", EXECUTION_MODE_AUTO) or EXECUTION_MODE_AUTO).strip() or EXECUTION_MODE_AUTO,
        context_row_index=namespace.context_row_index,
        run_name=run_name,
        context_source=context_source,
        task_id=task_id,
        direction_id=direction_id,
        route_type=route_type,
        step3_policy=step3_policy,
        entry_mode=entry_mode,
        market_entry_url=market_entry["market_entry_url"],
        entry_source_step=market_entry["entry_source_step"],
        market_handoff_path=market_entry["market_handoff_path"],
        market_session_bundle_path=market_entry["market_session_bundle_path"],
        selected_product_research_url=market_entry["selected_product_research_url"],
        product_seed_csv=market_entry["product_seed_csv"],
        selected_sample_id=market_entry["selected_sample_id"],
        selected_sample_asin=market_entry["selected_sample_asin"],
        selected_sample_title=market_entry["selected_sample_title"],
        selected_candidate_market_name=market_entry["selected_candidate_market_name"],
        selected_market_path=market_entry["selected_market_path"],
        handoff_capture_status=market_entry["handoff_capture_status"],
    )


def sanitize_keyword(keyword: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", keyword.strip().lower()).strip("-")
    return cleaned or "market"


def recommended_filename(args: ExportArgs, timestamp: datetime) -> str:
    return (
        f"market-report-{args.site.lower()}-{sanitize_keyword(args.keyword)}-"
        f"d{args.days}-new{normalize_new_product_window(args.new_product_window)}m-"
        f"sample{args.sample_top_n}-head{args.head_top_n}-{timestamp.strftime('%Y%m%d_%H%M%S')}.xlsx"
    )


def validate_args(args: ExportArgs) -> None:
    if args.site not in SITE_LABELS:
        supported = ", ".join(sorted(SITE_LABELS))
        raise MarketExportError(f"--site must be one of: {supported}.")
    if args.days != 30:
        raise MarketExportError("Only --days 30 is verified on the current SellerSprite market flow.")
    if args.sample_top_n != 100:
        raise MarketExportError(
            "The current SellerSprite market flow only exposes sample top 100. Use --sample-top-n 100."
        )
    if str(args.head_top_n) not in HEAD_TOP_VALUES:
        raise MarketExportError("--head-top-n must be one of: 3, 5, 10, 20.")
    if args.max_attempts <= 0:
        raise MarketExportError("--max-attempts must be >= 1.")
    if args.retry_wait_seconds < 0:
        raise MarketExportError("--retry-wait-seconds must be >= 0.")
    if not args.keyword:
        raise MarketExportError("--keyword resolved to an empty value.")
    if args.entry_mode == ENTRY_MODE_PRODUCT_MARKET_ANALYSIS and not args.market_entry_url:
        raise MarketExportError(
            "Product-form STEP3 requires a STEP1 product sample with a 市场分析URL; refusing to fall back to naked keyword search.",
            reason_code="PRODUCT_MARKET_ENTRY_MISSING",
        )
    if args.entry_mode == ENTRY_MODE_PRODUCT_MARKET_ANALYSIS and args.entry_source_step != "DIRECT_MARKET_ANALYSIS_URL" and not args.market_handoff_path:
        raise MarketExportError(
            "Product-form STEP3 now requires a materialized STEP1 market handoff object before live rerun.",
            reason_code=STEP1_MARKET_HANDOFF_OBJECT_MISSING,
        )
    normalize_new_product_window(args.new_product_window)


def profile_has_content(profile_dir: Path) -> bool:
    return profile_dir.exists() and any(profile_dir.iterdir())


def ensure_local_auth_profile(profile_dir: Path | None = None) -> Path:
    selected_profile_dir = profile_dir or preferred_sellersprite_profile_dir()
    if selected_profile_dir is None or not selected_profile_dir.exists():
        raise MarketExportError(
            f"No SellerSprite persistent profile is ready. Checked replay profile {REPLAY_PROFILE_DIR} and main profile {PROFILE_DIR}.",
            "MARKET_PROFILE_MISSING",
        )
    try:
        next(selected_profile_dir.iterdir())
    except StopIteration as exc:
        raise MarketExportError(
            f"SellerSprite persistent profile is empty: {selected_profile_dir}.",
            "MARKET_PROFILE_EMPTY",
        ) from exc
    return ensure_within_repo(selected_profile_dir, "market_profile_dir")


def launch_market_context(playwright, args: ExportArgs) -> tuple[Any, Any | None, str, str]:
    warning = ""
    browser = None
    persistent_profile_dir = preferred_sellersprite_profile_dir()
    runtime_replay_surface_family = (
        "SELLERSPRITE_PRODUCT_RESEARCH_AUTH"
        if args.entry_mode == ENTRY_MODE_PRODUCT_MARKET_ANALYSIS
        else "SELLERSPRITE_MARKET_RESEARCH_AUTH"
    )
    if args.execution_mode in {EXECUTION_MODE_AUTO, EXECUTION_MODE_PERSISTENT} and persistent_profile_dir is not None:
        launch_errors: list[str] = []
        for attempt_index in range(1, 3):
            try:
                if persistent_profile_dir == REPLAY_PROFILE_DIR:
                    context, runtime_info = launch_runtime_seeded_persistent_context(
                        playwright,
                        surface_family=runtime_replay_surface_family,
                        headless=False,
                        viewport={"width": 1600, "height": 900},
                        accept_downloads=True,
                        channel="msedge",
                    )
                    warning = ((warning + " | ") if warning else "") + (
                        f"using_runtime_replay_surface={runtime_replay_surface_family}; "
                        f"runtime_profile_dir={runtime_info.get('runtime_profile_dir', '')}"
                    )
                else:
                    context = playwright.chromium.launch_persistent_context(
                        user_data_dir=str(persistent_profile_dir),
                        channel="msedge",
                        headless=False,
                        accept_downloads=True,
                        viewport={"width": 1600, "height": 900},
                    )
                return context, browser, "persistent_profile", warning
            except Exception as exc:
                launch_errors.append(f"attempt_{attempt_index}:{exc}")
                if attempt_index == 1:
                    time.sleep(1.5)
                    continue
                if args.execution_mode == EXECUTION_MODE_PERSISTENT:
                    raise MarketExportError(
                        f"Persistent SellerSprite market profile could not be opened: {'; '.join(launch_errors)}",
                        "MARKET_PERSISTENT_PROFILE_LAUNCH_FAILED",
                    ) from exc
                warning = "; ".join(launch_errors)

    if STORAGE_STATE_PATH.exists():
        browser = playwright.chromium.launch(channel="msedge", headless=False)
        context = browser.new_context(
            storage_state=str(STORAGE_STATE_PATH),
            accept_downloads=True,
            viewport={"width": 1600, "height": 900},
        )
        return context, browser, "storage_state", warning

    if args.execution_mode == EXECUTION_MODE_STORAGE_STATE:
        raise MarketExportError(
            f"Requested storage_state execution but the canonical SellerSprite state is missing: {STORAGE_STATE_PATH}",
            "MARKET_STORAGE_STATE_MISSING",
        )
    raise MarketExportError(
        "No usable SellerSprite auth context is available for market export. Neither a persistent profile nor a canonical storage_state is ready.",
        "MARKET_AUTH_CONTEXT_UNAVAILABLE",
    )


def build_target_path(output_dir: Path, file_name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / file_name


def validate_download(path: Path) -> None:
    if not path.exists():
        raise MarketExportError(f"Download file was not saved: {path}")
    if path.stat().st_size <= 0:
        raise MarketExportError(f"Downloaded file is empty: {path}")
    if path.suffix.lower() != ".xlsx":
        raise MarketExportError(f"Downloaded file is not an .xlsx workbook: {path.name}")
    try:
        with zipfile.ZipFile(path) as workbook:
            names = set(workbook.namelist())
    except zipfile.BadZipFile as exc:
        raise MarketExportError(f"Downloaded workbook is not a valid XLSX zip container: {path}") from exc
    if "xl/workbook.xml" not in names:
        raise MarketExportError(f"Downloaded workbook is missing xl/workbook.xml: {path}")


def click_visible_button(page, label: str) -> None:
    locator = page.locator(f"button:has-text('{label}')").first
    locator.wait_for(state="visible", timeout=15000)
    locator.click(timeout=15000)


def page_has_no_results(page) -> bool:
    try:
        body_text = page.locator("body").inner_text(timeout=5000)
    except Exception:
        return False
    compacted = " ".join(body_text.split())
    return any(marker in compacted for marker in NO_RESULT_MARKERS)


def configure_market_filters(page, args: ExportArgs, *, fill_keyword: bool) -> None:
    site_label = SITE_LABELS[args.site]
    click_visible_button(page, site_label)
    click_visible_button(page, MONTH_LAST_30_LABEL)
    page.locator(NEW_PRODUCT_SELECT_SELECTOR).select_option(normalize_new_product_window(args.new_product_window))
    page.locator(HEAD_TOP_SELECT_SELECTOR).select_option(str(args.head_top_n))
    if fill_keyword:
        page.locator(SEARCH_INPUT_SELECTOR).click()
        page.locator(SEARCH_INPUT_SELECTOR).fill(args.keyword)


def normalize_binding_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def title_binding_tokens(title: str) -> list[str]:
    tokens = [token for token in re.findall(r"[a-z0-9]+", str(title or "").casefold()) if len(token) >= 4]
    unique: list[str] = []
    for token in tokens:
        if token not in unique:
            unique.append(token)
    return unique[:8]


def wait_for_product_result_rows(page, timeout_ms: int = 20000) -> int:
    data_rows = page.locator(".el-table__body tr.el-table__row")
    deadline = time.monotonic() + (timeout_ms / 1000)
    row_count = 0
    while time.monotonic() <= deadline:
        row_count = data_rows.count()
        if row_count > 0:
            return row_count
        page.wait_for_timeout(1000)
    return row_count


def rebind_product_result_row(page, args: ExportArgs) -> tuple[Any, int, int]:
    data_rows = page.locator(".el-table__body tr.el-table__row")
    row_count = wait_for_product_result_rows(page)
    if row_count <= 0:
        raise MarketExportError(
            "STEP3 reopened the captured Product Research surface, but no visible rows were rendered for rebind.",
            reason_code=PRODUCT_RESULT_ROWS_MISSING,
        )

    selected_asin = str(args.selected_sample_asin or "").strip().upper()
    selected_title = str(args.selected_sample_title or "").strip()
    title_tokens = title_binding_tokens(selected_title)
    exact_title_norm = normalize_binding_text(selected_title)
    best_row = None
    best_score = 0

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

    if best_row is None or best_score < 60:
        raise MarketExportError(
            "STEP3 could not rebind the captured STEP1 sample on the reopened Product Research surface.",
            reason_code=STEP1_MARKET_HANDOFF_REBIND_FAILED,
        )
    return best_row, row_count, best_score


def locate_product_market_analysis_link_from_row(row, args: ExportArgs) -> tuple[Any, str]:
    expanded_row = row.locator("xpath=following-sibling::tr[1]").first
    links = expanded_row.locator("a[href*='/v2/market-research']")
    link_count = links.count()
    if link_count <= 0:
        raise MarketExportError(
            "STEP3 rebound the exact Product Research row, but no visible 市场分析 link was exposed on that row.",
            reason_code=PRODUCT_MARKET_ANALYSIS_LINK_NOT_VISIBLE,
        )

    chosen_link = links.first
    chosen_href = ""
    selected_url = str(args.market_entry_url or "").strip()
    for index in range(link_count):
        candidate = links.nth(index)
        try:
            href = str(candidate.get_attribute("href") or "").strip()
        except Exception:
            href = ""
        if selected_url and href == selected_url:
            chosen_link = candidate
            chosen_href = href
            break
        if not chosen_href and href:
            chosen_link = candidate
            chosen_href = href
    return chosen_link, chosen_href


def apply_session_bundle_to_context(context, bundle: dict[str, Any]) -> dict[str, Any]:
    session_storage_dump = bundle.get("session_storage_dump", {})
    if not isinstance(session_storage_dump, dict):
        session_storage_dump = {}
    normalized_storage: dict[str, str] = {}
    for key, value in session_storage_dump.items():
        text_key = str(key or "").strip()
        if not text_key:
            continue
        normalized_storage[text_key] = str(value or "")
    if not normalized_storage:
        return {"status": "NO_SESSION_STORAGE", "injected_item_count": 0}

    init_payload = {
        "origin": "https://www.sellersprite.com",
        "items": normalized_storage,
    }
    context.add_init_script(
        script="""
        (payload) => {
          const apply = () => {
            try {
              if (!payload || window.location.origin !== payload.origin) {
                return;
              }
              const items = payload.items || {};
              for (const [key, value] of Object.entries(items)) {
                window.sessionStorage.setItem(key, String(value ?? ""));
              }
            } catch (error) {}
          };
          apply();
          document.addEventListener("DOMContentLoaded", apply);
        }
        """,
        arg=init_payload,
    )
    return {"status": "PASS", "injected_item_count": len(normalized_storage)}


def open_market_via_raw_url_fallback(page, args: ExportArgs, summary: dict[str, Any], fallback_reason: str):
    summary["market_entry_method"] = "raw_direct_url_fallback"
    summary["market_entry_fallback_reason_code"] = fallback_reason
    summary["failure_stage_name"] = fallback_reason
    summary["raw_direct_url_attempted"] = args.market_entry_url
    page.goto(args.market_entry_url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(2000)
    summary["market_entry_click_url"] = args.market_entry_url
    summary["market_entry_final_url"] = page.url
    return page, args.market_entry_url


def open_market_via_product_entry(context, args: ExportArgs, summary: dict[str, Any]):
    product_page = context.pages[0] if context.pages else context.new_page()
    base_product_url = build_product_research_url(args.site)
    product_entry_url = str(args.selected_product_research_url or base_product_url).strip()
    summary["product_handoff_path"] = args.market_handoff_path
    summary["product_handoff_capture_status"] = args.handoff_capture_status
    summary["selected_product_research_url"] = product_entry_url
    summary["product_entry_url_attempted"] = product_entry_url
    summary["product_surface_warmup_url"] = base_product_url
    summary["rebind_attempted"] = False
    summary["rows_visible"] = False
    summary["market_analysis_link_visible"] = False
    summary["popup_or_navigation"] = "not_attempted"
    summary["workbook_download_attempted"] = False
    if product_entry_url != base_product_url:
        product_page.goto(base_product_url, wait_until="domcontentloaded", timeout=90000)
        product_page.wait_for_timeout(2000)
        summary["product_surface_warmup_final_url"] = product_page.url
        if "/w/user/login" in product_page.url:
            summary["failure_stage_name"] = "market_open_product_entry_warmup"
            summary["login_redirect_timing"] = "before_rebind"
            incident = register_auth_incident(
                module_name="market_export",
                step_name="market_open_product_entry_warmup",
                source_script=__file__,
                reason_code="SELLERSPRITE_AUTH_REQUIRED",
                current_url=product_page.url,
                redirect_from_url=base_product_url,
                page=product_page,
                run_context={
                    "keyword": args.keyword,
                    "site": args.site,
                    "run_name": args.run_name,
                    "direction_id": args.direction_id,
                    "entry_mode": args.entry_mode,
                    "entry_source_step": args.entry_source_step,
                    "selected_sample_asin": args.selected_sample_asin,
                },
            )
            raise MarketExportError(
                "SellerSprite product page redirected to login during Product Research warmup before page-visible 市场分析 handoff could start.",
                reason_code="SELLERSPRITE_AUTH_REQUIRED",
                details=replay_meta_from_incident(incident),
            )
    product_page.goto(product_entry_url, wait_until="domcontentloaded", timeout=90000)
    product_page.wait_for_timeout(2000)
    summary["product_entry_final_url"] = product_page.url
    if "/w/user/login" in product_page.url:
        summary["failure_stage_name"] = "market_open_product_entry"
        summary["login_redirect_timing"] = "before_rebind"
        incident = register_auth_incident(
            module_name="market_export",
            step_name="market_open_product_entry",
            source_script=__file__,
            reason_code="SELLERSPRITE_AUTH_REQUIRED",
            current_url=product_page.url,
            redirect_from_url=product_entry_url,
            page=product_page,
            run_context={
                "keyword": args.keyword,
                "site": args.site,
                "run_name": args.run_name,
                "direction_id": args.direction_id,
                "entry_mode": args.entry_mode,
                "entry_source_step": args.entry_source_step,
                "selected_sample_asin": args.selected_sample_asin,
            },
        )
        raise MarketExportError(
            "SellerSprite product page redirected to login before page-visible 市场分析 handoff could start.",
            reason_code="SELLERSPRITE_AUTH_REQUIRED",
            details=replay_meta_from_incident(incident),
        )

    try:
        summary["rebind_attempted"] = True
        bound_row, row_count, match_score = rebind_product_result_row(product_page, args)
        summary["product_entry_row_count"] = row_count
        summary["product_entry_rebind_score"] = match_score
        summary["product_entry_bound_sample_id"] = args.selected_sample_id
        summary["product_entry_bound_sample_asin"] = args.selected_sample_asin
        summary["rows_visible"] = row_count > 0
        link, chosen_href = locate_product_market_analysis_link_from_row(bound_row, args)
        summary["market_analysis_link_visible"] = True
    except MarketExportError as exc:
        summary["product_entry_rebind_reason_code"] = exc.reason_code
        summary["failure_stage_name"] = exc.reason_code
        if args.market_entry_url:
            return open_market_via_raw_url_fallback(product_page, args, summary, exc.reason_code)
        raise
    except Exception as exc:
        raise MarketExportError(str(exc), reason_code="PRODUCT_MARKET_ENTRY_FAILED") from exc
    summary["page_visible_market_entry_url"] = chosen_href

    try:
        with context.expect_page(timeout=15000) as popup_info:
            link.click(timeout=10000)
        market_page = popup_info.value
        market_page.wait_for_load_state("domcontentloaded", timeout=90000)
        summary["popup_or_navigation"] = "popup"
    except PlaywrightTimeoutError:
        with product_page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
            link.click(timeout=10000)
        market_page = product_page
        summary["popup_or_navigation"] = "same_tab_navigation"

    market_page.wait_for_timeout(2000)
    summary["market_entry_method"] = "page_visible_handoff"
    summary["market_entry_click_url"] = chosen_href
    summary["market_entry_final_url"] = market_page.url
    return market_page, chosen_href or product_entry_url


def open_market_via_product_entry_with_session_bundle(context, args: ExportArgs, summary: dict[str, Any]):
    product_page = context.pages[0] if context.pages else context.new_page()
    base_product_url = build_product_research_url(args.site)
    product_entry_url = str(args.selected_product_research_url or base_product_url).strip()
    session_bundle_path = str(args.market_session_bundle_path or "").strip()
    summary["product_handoff_path"] = args.market_handoff_path
    summary["market_session_bundle_path"] = session_bundle_path
    summary["product_handoff_capture_status"] = args.handoff_capture_status
    summary["selected_product_research_url"] = product_entry_url
    summary["product_entry_url_attempted"] = product_entry_url
    summary["product_surface_warmup_url"] = base_product_url
    summary["rebind_attempted"] = False
    summary["rows_visible"] = False
    summary["market_analysis_link_visible"] = False
    summary["popup_or_navigation"] = "not_attempted"
    summary["workbook_download_attempted"] = False
    summary["session_bundle_consumed"] = False
    summary["session_bundle_injection"] = {}
    summary["session_bundle_probe_status"] = ""
    summary["session_bundle_probe_stage"] = ""

    if session_bundle_path:
        bundle_path = ensure_within_repo(Path(session_bundle_path), "market_session_bundle_json")
        if bundle_path.exists():
            session_bundle = load_json_record(bundle_path)
            summary["session_bundle_consumed"] = True
            summary["session_bundle_probe_status"] = str(session_bundle.get("same_session_probe_status", "")).strip()
            summary["session_bundle_probe_stage"] = str(session_bundle.get("same_session_probe_stage", "")).strip()
            try:
                summary["session_bundle_injection"] = apply_session_bundle_to_context(context, session_bundle)
            except Exception as exc:
                summary["failure_stage_name"] = STEP1_MARKET_SESSION_BUNDLE_INJECTION_FAILED
                raise MarketExportError(
                    "STEP3 located a STEP1 market session bundle, but sessionStorage injection into the replay context failed.",
                    reason_code=STEP1_MARKET_SESSION_BUNDLE_INJECTION_FAILED,
                ) from exc
        else:
            summary["session_bundle_probe_stage"] = STEP1_MARKET_SESSION_BUNDLE_MISSING

    if product_entry_url != base_product_url and not summary["session_bundle_consumed"]:
        product_page.goto(base_product_url, wait_until="domcontentloaded", timeout=90000)
        product_page.wait_for_timeout(2000)
        summary["product_surface_warmup_final_url"] = product_page.url
        if "/w/user/login" in product_page.url:
            summary["failure_stage_name"] = "market_open_product_entry_warmup"
            summary["login_redirect_timing"] = "before_rebind"
            incident = register_auth_incident(
                module_name="market_export",
                step_name="market_open_product_entry_warmup",
                source_script=__file__,
                reason_code="SELLERSPRITE_AUTH_REQUIRED",
                current_url=product_page.url,
                redirect_from_url=base_product_url,
                page=product_page,
                run_context={
                    "keyword": args.keyword,
                    "site": args.site,
                    "run_name": args.run_name,
                    "direction_id": args.direction_id,
                    "entry_mode": args.entry_mode,
                    "entry_source_step": args.entry_source_step,
                    "selected_sample_asin": args.selected_sample_asin,
                    "selected_sample_id": args.selected_sample_id,
                },
            )
            raise MarketExportError(
                "SellerSprite product page redirected to login during Product Research warmup before page-visible 市场分析 handoff could start.",
                reason_code=MARKET_LOGIN_REDIRECT_BEFORE_REBIND,
                details=replay_meta_from_incident(incident),
            )

    product_page.goto(product_entry_url, wait_until="domcontentloaded", timeout=90000)
    product_page.wait_for_timeout(2000)
    summary["product_entry_final_url"] = product_page.url
    if "/w/user/login" in product_page.url:
        summary["failure_stage_name"] = "market_open_product_entry"
        summary["login_redirect_timing"] = "before_rebind"
        incident = register_auth_incident(
            module_name="market_export",
            step_name="market_open_product_entry",
            source_script=__file__,
            reason_code="SELLERSPRITE_AUTH_REQUIRED",
            current_url=product_page.url,
            redirect_from_url=product_entry_url,
            page=product_page,
            run_context={
                "keyword": args.keyword,
                "site": args.site,
                "run_name": args.run_name,
                "direction_id": args.direction_id,
                "entry_mode": args.entry_mode,
                "entry_source_step": args.entry_source_step,
                "selected_sample_asin": args.selected_sample_asin,
                "selected_sample_id": args.selected_sample_id,
            },
        )
        raise MarketExportError(
            "SellerSprite product page redirected to login before page-visible 市场分析 handoff could start.",
            reason_code=MARKET_LOGIN_REDIRECT_BEFORE_REBIND,
            details=replay_meta_from_incident(incident),
        )

    try:
        summary["rebind_attempted"] = True
        bound_row, row_count, match_score = rebind_product_result_row(product_page, args)
        summary["product_entry_row_count"] = row_count
        summary["product_entry_rebind_score"] = match_score
        summary["product_entry_bound_sample_id"] = args.selected_sample_id
        summary["product_entry_bound_sample_asin"] = args.selected_sample_asin
        summary["rows_visible"] = row_count > 0
        link, chosen_href = locate_product_market_analysis_link_from_row(bound_row, args)
        summary["market_analysis_link_visible"] = True
    except MarketExportError as exc:
        summary["product_entry_rebind_reason_code"] = exc.reason_code
        summary["failure_stage_name"] = exc.reason_code
        if args.market_entry_url:
            return open_market_via_raw_url_fallback(product_page, args, summary, exc.reason_code)
        raise
    except Exception as exc:
        raise MarketExportError(str(exc), reason_code="PRODUCT_MARKET_ENTRY_FAILED") from exc

    summary["page_visible_market_entry_url"] = chosen_href

    try:
        with context.expect_page(timeout=15000) as popup_info:
            link.click(timeout=10000)
        market_page = popup_info.value
        market_page.wait_for_load_state("domcontentloaded", timeout=90000)
        summary["popup_or_navigation"] = "popup"
    except PlaywrightTimeoutError:
        with product_page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
            link.click(timeout=10000)
        market_page = product_page
        summary["popup_or_navigation"] = "same_tab_navigation"

    market_page.wait_for_timeout(2000)
    summary["market_entry_method"] = "page_visible_handoff"
    summary["market_entry_click_url"] = chosen_href
    summary["market_entry_final_url"] = market_page.url
    if "/w/user/login" in market_page.url:
        summary["failure_stage_name"] = MARKET_LOGIN_REDIRECT_AFTER_CLICK
        summary["login_redirect_timing"] = "after_click"
        incident = register_auth_incident(
            module_name="market_export",
            step_name="market_open_after_click",
            source_script=__file__,
            reason_code="SELLERSPRITE_AUTH_REQUIRED",
            current_url=market_page.url,
            redirect_from_url=chosen_href or product_entry_url,
            page=market_page,
            run_context={
                "keyword": args.keyword,
                "site": args.site,
                "run_name": args.run_name,
                "direction_id": args.direction_id,
                "entry_mode": args.entry_mode,
                "entry_source_step": args.entry_source_step,
                "selected_sample_asin": args.selected_sample_asin,
                "selected_sample_id": args.selected_sample_id,
            },
        )
        raise MarketExportError(
            "SellerSprite market handoff redirected to login after the row-scoped 市场分析 click.",
            reason_code=MARKET_LOGIN_REDIRECT_AFTER_CLICK,
            details=replay_meta_from_incident(incident),
        )
    return market_page, chosen_href or product_entry_url


def market_entry_url(args: ExportArgs) -> str:
    if args.entry_mode == ENTRY_MODE_PRODUCT_MARKET_ANALYSIS and args.market_entry_url:
        return args.market_entry_url
    return MARKET_URL


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_run_record(log_dir: Path, run_label: str, record: dict[str, Any]) -> tuple[Path, Path]:
    log_dir.mkdir(parents=True, exist_ok=True)
    run_log_path = log_dir / f"{run_label}.json"
    latest_run_path = log_dir / "latest_run.json"
    write_json(run_log_path, record)
    write_json(latest_run_path, record)
    append_jsonl(log_dir / "export_runs.jsonl", record)
    if record.get("status") == "FAILED":
        append_jsonl(log_dir / "export_failures.jsonl", record)
    return run_log_path, latest_run_path


def export_report_once(args: ExportArgs, target_path: Path) -> tuple[Path, str, str, str, dict[str, Any]]:
    if target_path.exists():
        target_path.unlink()

    entry_url = market_entry_url(args)
    fill_keyword = args.entry_mode != ENTRY_MODE_PRODUCT_MARKET_ANALYSIS
    entry_execution: dict[str, Any] = {}
    with sync_playwright() as playwright:
        context, browser, execution_mode, execution_warning = launch_market_context(playwright, args)
        page = None
        try:
            entry_execution["execution_mode_used"] = execution_mode
            entry_execution["execution_warning"] = execution_warning
            entry_execution["entry_mode"] = args.entry_mode
            entry_execution["entry_source_step"] = args.entry_source_step
            entry_execution["workbook_download_attempted"] = False
            page = context.pages[0] if context.pages else context.new_page()
            redirect_from_url = entry_url
            if args.entry_mode == ENTRY_MODE_PRODUCT_MARKET_ANALYSIS and args.entry_source_step != "DIRECT_MARKET_ANALYSIS_URL":
                page, redirect_from_url = open_market_via_product_entry_with_session_bundle(context, args, entry_execution)
            else:
                entry_execution["market_surface_url_attempted"] = entry_url
                page.goto(entry_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2000)
                entry_execution["market_surface_final_url"] = page.url
            if "/w/user/login" in page.url:
                incident = register_auth_incident(
                    module_name="market_export",
                    step_name="market_open_surface",
                    source_script=__file__,
                    reason_code="SELLERSPRITE_AUTH_REQUIRED",
                    current_url=page.url,
                    redirect_from_url=redirect_from_url,
                    page=page,
                    run_context={
                        "keyword": args.keyword,
                        "site": args.site,
                        "days": args.days,
                        "new_product_window": args.new_product_window,
                        "sample_top_n": args.sample_top_n,
                        "head_top_n": args.head_top_n,
                        "run_name": args.run_name,
                        "context_source": args.context_source,
                        "entry_mode": args.entry_mode,
                        "entry_source_step": args.entry_source_step,
                        "market_entry_url": args.market_entry_url,
                    },
                )
                raise MarketExportError(
                    "SellerSprite market research redirected to login before filters could be applied. Refresh repo-local auth first.",
                    reason_code="SELLERSPRITE_AUTH_REQUIRED",
                    details=replay_meta_from_incident(incident),
                )
            configure_market_filters(page, args, fill_keyword=fill_keyword)
            click_visible_button(page, FILTER_BUTTON_TEXT)
            page.wait_for_timeout(5000)
            if page_has_no_results(page):
                raise MarketExportError(
                    "SellerSprite market research returned no results for the current controls, so no market workbook can be exported.",
                    reason_code="MARKET_SOURCE_EMPTY",
                )
            export_button = page.locator("button", has_text=EXPORT_BUTTON_TEXT).first
            export_button.wait_for(state="visible", timeout=120000)
            entry_execution["workbook_download_attempted"] = True
            with page.expect_download(timeout=120000) as download_info:
                export_button.click(timeout=15000)
            download = download_info.value
            download.save_as(str(target_path))
            validate_download(target_path)
            entry_execution["workbook_status"] = MARKET_WORKBOOK_PASS
            return target_path, download.suggested_filename, execution_mode, execution_warning, entry_execution
        except MarketExportError as exc:
            if entry_execution and "entry_execution" not in exc.details:
                exc.details["entry_execution"] = entry_execution
            raise
        except PlaywrightTimeoutError as exc:
            if page is not None and auth_surface_detected(page=page):
                incident = register_auth_incident(
                    module_name="market_export",
                    step_name="market_export_timeout",
                    source_script=__file__,
                    reason_code="SELLERSPRITE_AUTH_REQUIRED",
                    current_url=page.url,
                    redirect_from_url=redirect_from_url,
                    page=page,
                    run_context={
                        "keyword": args.keyword,
                        "site": args.site,
                        "days": args.days,
                        "new_product_window": args.new_product_window,
                        "sample_top_n": args.sample_top_n,
                        "head_top_n": args.head_top_n,
                        "run_name": args.run_name,
                        "context_source": args.context_source,
                        "entry_mode": args.entry_mode,
                        "entry_source_step": args.entry_source_step,
                        "market_entry_url": args.market_entry_url,
                    },
                )
                raise MarketExportError(
                    "SellerSprite market research fell back to a login/auth surface while waiting for the export controls.",
                    reason_code="SELLERSPRITE_AUTH_REQUIRED",
                    details=replay_meta_from_incident(incident),
                ) from exc
            message = (
                "Timed out while waiting for SellerSprite export controls or download. "
                "The local session may be expired; refresh auth with scripts/bootstrap_sellersprite_auth.py."
            )
            raise MarketExportError(message, reason_code="MARKET_TIMEOUT", details={"entry_execution": entry_execution}) from exc
        except Error as exc:
            raise MarketExportError(
                f"Playwright failed during market export: {exc}",
                reason_code="MARKET_PLAYWRIGHT_ERROR",
                details={"entry_execution": entry_execution},
            ) from exc
        finally:
            context.close()
            if browser is not None:
                browser.close()


def build_run_label(args: ExportArgs, timestamp: datetime) -> str:
    return (
        f"{timestamp.strftime('%Y%m%d_%H%M%S')}-market-export-"
        f"{args.site.lower()}-{sanitize_keyword(args.keyword)}"
    )


def run_export(args: ExportArgs) -> tuple[Path, str, list[dict[str, Any]], str, str, dict[str, Any]]:
    preferred_profile_dir = preferred_sellersprite_profile_dir()
    if args.execution_mode == EXECUTION_MODE_PERSISTENT or (args.execution_mode == EXECUTION_MODE_AUTO and preferred_profile_dir is not None):
        ensure_local_auth_profile(preferred_profile_dir)
    run_started = datetime.now()
    target_path = build_target_path(args.output_dir, recommended_filename(args, run_started))
    attempts: list[dict[str, Any]] = []
    last_error: MarketExportError | None = None
    effective_execution_mode = ""
    execution_warning = ""
    last_entry_execution: dict[str, Any] = {}

    for attempt_index in range(1, args.max_attempts + 1):
        attempt_started = iso_now()
        try:
            saved_path, suggested_filename, effective_execution_mode, execution_warning, entry_execution = export_report_once(args, target_path)
            attempts.append(
                {
                    "attempt": attempt_index,
                    "started_at": attempt_started,
                    "finished_at": iso_now(),
                    "status": "SUCCESS",
                    "target_path": str(saved_path),
                    "seller_suggested_filename": suggested_filename,
                    "execution_mode": effective_execution_mode,
                    "execution_warning": execution_warning,
                    "entry_execution": entry_execution,
                }
            )
            return saved_path, suggested_filename, attempts, effective_execution_mode, execution_warning, entry_execution
        except MarketExportError as exc:
            last_error = exc
            last_entry_execution = exc.details.get("entry_execution", {}) if isinstance(exc.details.get("entry_execution", {}), dict) else {}
            attempts.append(
                {
                    "attempt": attempt_index,
                    "started_at": attempt_started,
                    "finished_at": iso_now(),
                    "status": "FAILED",
                    "target_path": str(target_path),
                    "error": str(exc),
                    "execution_mode": effective_execution_mode,
                    "execution_warning": execution_warning,
                    "entry_execution": last_entry_execution,
                }
            )
            if attempt_index >= args.max_attempts:
                break
            time.sleep(args.retry_wait_seconds)

    assert last_error is not None
    if last_entry_execution and "entry_execution" not in last_error.details:
        last_error.details["entry_execution"] = last_entry_execution
    raise ExportExecutionError(
        str(last_error),
        attempts,
        reason_code=getattr(last_error, "reason_code", "MARKET_EXPORT_ERROR"),
        details=getattr(last_error, "details", {}),
    )


def build_record_base(args: ExportArgs, run_label: str, planned_target: Path) -> dict[str, Any]:
    return {
        "run_label": run_label,
        "status": "UNKNOWN",
        "started_at": iso_now(),
        "finished_at": None,
        "runner": "scripts/export_market_report.py",
        "context_source": args.context_source,
        "context_row_index": args.context_row_index,
        "task_id": args.task_id,
        "run_name": args.run_name,
        "direction_id": args.direction_id,
        "route_type": args.route_type,
        "step3_policy": args.step3_policy,
        "controls": {
            "keyword": args.keyword,
            "site": args.site,
            "days": args.days,
            "new_product_window_months": normalize_new_product_window(args.new_product_window),
            "sample_top_n": args.sample_top_n,
            "head_top_n": args.head_top_n,
            "entry_mode": args.entry_mode,
        },
        "raw_layer": {
            "output_dir": str(args.output_dir),
            "target_workbook": str(planned_target),
            "target_file_name": planned_target.name,
        },
        "entry_source": {
            "entry_mode": args.entry_mode,
            "entry_source_step": args.entry_source_step,
            "market_handoff_path": args.market_handoff_path,
            "market_session_bundle_path": args.market_session_bundle_path,
            "selected_product_research_url": args.selected_product_research_url,
            "market_entry_url": args.market_entry_url,
            "product_seed_csv": args.product_seed_csv,
            "selected_sample_id": args.selected_sample_id,
            "selected_sample_asin": args.selected_sample_asin,
            "selected_sample_title": args.selected_sample_title,
            "selected_candidate_market_name": args.selected_candidate_market_name,
            "selected_market_path": args.selected_market_path,
            "handoff_capture_status": args.handoff_capture_status,
        },
        "log_dir": str(args.log_dir),
        "attempts": [],
        "seller_suggested_filename": None,
        "execution_mode_requested": args.execution_mode,
        "execution_mode_effective": "",
        "execution_warning": "",
        "failure_reason": None,
        "failure_reason_code": None,
        "auth_incident_path": "",
        "auth_surface_family": "",
        "auth_replay_available": False,
        "auth_replay_snippet_path": "",
        "auth_owner_recording_drop_path": "",
        "auth_replay_attempted": False,
        "auth_replay_result": {},
    }


def run_once(args: ExportArgs, *, replay_attempted: bool = False, replay_result: dict[str, Any] | None = None) -> tuple[int, dict[str, Any], Path]:
    record: dict[str, Any] | None = None
    run_log_path: Path | None = None
    latest_run_path: Path | None = None
    run_started = datetime.now()
    planned_target = build_target_path(args.output_dir, recommended_filename(args, run_started))
    run_label = build_run_label(args, run_started)
    record = build_record_base(args, run_label, planned_target)
    record["auth_replay_attempted"] = replay_attempted
    record["auth_replay_result"] = replay_result or {}
    record["started_at"] = iso_now()
    try:
        validate_args(args)
        if args.dry_run:
            record["status"] = "DRY_RUN"
            record["finished_at"] = iso_now()
            run_log_path, latest_run_path = write_run_record(args.log_dir, run_label, record)
            record["run_log_path"] = str(run_log_path)
            record["latest_run_path"] = str(latest_run_path)
            return 0, record, args.log_dir

        saved_path, suggested_filename, attempts, effective_execution_mode, execution_warning, entry_execution = run_export(args)
        record["status"] = "SUCCESS"
        record["reason_code"] = MARKET_WORKBOOK_PASS
        record["finished_at"] = iso_now()
        record["attempts"] = attempts
        record["seller_suggested_filename"] = suggested_filename
        record["execution_mode_effective"] = effective_execution_mode
        record["execution_warning"] = execution_warning
        record["entry_execution"] = entry_execution
        record["raw_layer"]["saved_workbook"] = str(saved_path)
        record["raw_layer"]["saved_file_size_bytes"] = saved_path.stat().st_size
        run_log_path, latest_run_path = write_run_record(args.log_dir, run_label, record)
        record["run_log_path"] = str(run_log_path)
        record["latest_run_path"] = str(latest_run_path)
        return 0, record, args.log_dir
    except MarketExportError as exc:
        assert record is not None
        record["status"] = "FAILED"
        record["finished_at"] = iso_now()
        record["failure_reason"] = str(exc)
        record["failure_reason_code"] = getattr(exc, "reason_code", "MARKET_EXPORT_ERROR")
        record["execution_mode_effective"] = str(record.get("entry_execution", {}).get("execution_mode_used", "")) if isinstance(record.get("entry_execution", {}), dict) else ""
        record["execution_warning"] = str(record.get("entry_execution", {}).get("execution_warning", "")) if isinstance(record.get("entry_execution", {}), dict) else ""
        if isinstance(exc.details.get("entry_execution", {}), dict):
            record["entry_execution"] = exc.details.get("entry_execution", {})
            record["execution_mode_effective"] = str(record["entry_execution"].get("execution_mode_used", ""))
            record["execution_warning"] = str(record["entry_execution"].get("execution_warning", ""))
        if getattr(exc, "details", None):
            record.update({key: value for key, value in exc.details.items() if key.startswith("auth_")})
        if isinstance(exc, ExportExecutionError):
            record["attempts"] = exc.attempts
        run_log_path, latest_run_path = write_run_record(args.log_dir, record["run_label"], record)
        record["run_log_path"] = str(run_log_path)
        record["latest_run_path"] = str(latest_run_path)
        return 1, record, args.log_dir


def record_requests_auth_replay(record: dict[str, Any], attempted_surfaces: set[str]) -> bool:
    if not isinstance(record, dict):
        return False
    surface_family = str(record.get("auth_surface_family", "")).strip()
    if not surface_family or surface_family in attempted_surfaces:
        return False
    if not bool(record.get("auth_replay_available")):
        return False
    return is_auth_reason(record.get("failure_reason_code"))


def main() -> int:
    args: ExportArgs | None = None
    try:
        args = resolve_args(parse_args())
        exit_code, record, log_dir = run_once(args)
        attempted_surfaces: set[str] = set()
        while exit_code != 0 and record_requests_auth_replay(record, attempted_surfaces):
            surface_family = str(record.get("auth_surface_family", "")).strip()
            if not surface_family or surface_family in attempted_surfaces:
                break
            attempted_surfaces.add(surface_family)
            replay_result = perform_registered_login_replay(
                surface_family=surface_family,
                module_name="market_export",
                trigger_reason_code=str(record.get("failure_reason_code", "")).strip(),
                trigger_summary=record,
            )
            if replay_result.get("status") != "PASS":
                record["auth_replay_attempted"] = True
                record["auth_replay_result"] = replay_result
                write_run_record(log_dir, str(record.get("run_label", "latest")), record)
                break
            args.execution_mode = str(replay_result.get("execution_mode_override", "")).strip() or EXECUTION_MODE_STORAGE_STATE
            exit_code, record, log_dir = run_once(args, replay_attempted=True, replay_result=replay_result)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return exit_code
    except MarketExportError as exc:
        print(json.dumps({"status": "FAILED", "reason_code": exc.reason_code, "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
