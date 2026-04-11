from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from map_market_report_to_candidate_pool import (
    CANONICAL_WORKBOOK_PREFIX,
    DEFAULT_MARKET_DIR_RELATIVE,
    DIAGNOSTIC_WORKBOOK_PREFIXES,
    WORKBOOK_SELECTION_RULE,
    default_output_dir,
    ensure_within_repo,
    find_market_sheet_and_header,
    first_value,
    guess_site_from_workbook,
    latest_market_workbook,
    load_csv_rows,
    normalize_text,
    parse_sample_counts,
    read_sheet_rows,
    safe_number_text,
    write_csv_atomic,
)


ROOT = Path(__file__).resolve().parents[1]
CURRENT_GOAL_RELATIVE = Path("inputs/selection_run_current/00_选品运行目标与边界.csv")
CURRENT_ENTRY_RELATIVE = Path("inputs/selection_run_current/01_市场入口与筛选参数.csv")
CURRENT_ROUTE_RELATIVE = Path("inputs/selection_run_current/01_选品任务路由与目的.csv")
STANDARD_90_RELATIVE = Path("templates/selection_canonical_standards/90_下推参数表.csv")
STANDARD_99_RELATIVE = Path("templates/selection_canonical_standards/99_字段数据标准总表.csv")
DEFAULT_CATEGORY_PROFILE_RELATIVE = Path("templates/category_gate_profiles/01__CATEGORY_GATE_PROFILES__TOY_V1__20260411.csv")
RAW_INDEX_FILE = "30_市场调研原始索引.csv"
CLEANED_FILE = "31_市场调研清洗结果.csv"
GATE_FILE = "32_市场调研下推结果.csv"
COMPAT_MARKET_CLEANED_FILE = "market_cleaned.csv"
WORKBOOK_INDEX_CSV = "market_workbook_index.csv"
WORKBOOK_INDEX_MD = "market_workbook_index.md"
OUTPUT_INDEX_CSV = "market_chain_output_index.csv"
OUTPUT_INDEX_MD = "market_chain_output_index.md"
DEFAULT_DAYS = 30
DEFAULT_NEW_PRODUCT_WINDOW = "6"
DEFAULT_SAMPLE_TOP_N = 100
DEFAULT_HEAD_TOP_N = 10
CSV_READ_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk")
NEW_PRODUCT_DAYS_TO_WINDOW = {
    "30": "1",
    "90": "3",
    "180": "6",
    "365": "12",
}

PROFILE_PARAMETER_SPECS = {
    "avg_price_min": {"rule_id": "S3_MIN_AVG_PRICE", "metric_name": "平均价格", "comparator": ">=", "threshold_unit": "usd", "tie_breaker_rank": "1"},
    "avg_price_max": {"rule_id": "S3_MAX_AVG_PRICE", "metric_name": "平均价格", "comparator": "<=", "threshold_unit": "usd", "tie_breaker_rank": "2"},
    "monthly_sales_min": {"rule_id": "S3_MIN_MARKET_VOLUME", "metric_name": "月总销量", "comparator": ">=", "threshold_unit": "units", "tie_breaker_rank": "3"},
    "new_product_ratio_min": {"rule_id": "S3_MIN_NEW_PRODUCT_RATIO", "metric_name": "新品占比_pct", "comparator": ">=", "threshold_unit": "pct", "tie_breaker_rank": "4"},
    "commodity_concentration_max": {"rule_id": "S3_MAX_COMMODITY_CONCENTRATION", "metric_name": "商品集中度", "comparator": "<=", "threshold_unit": "ratio", "tie_breaker_rank": "5"},
    "brand_concentration_max": {"rule_id": "S3_MAX_BRAND_CONCENTRATION", "metric_name": "品牌集中度", "comparator": "<=", "threshold_unit": "ratio", "tie_breaker_rank": "6"},
    "seller_concentration_max": {"rule_id": "S3_MAX_SELLER_CONCENTRATION", "metric_name": "卖家集中度", "comparator": "<=", "threshold_unit": "ratio", "tie_breaker_rank": "7"},
    "avg_rating_min": {"rule_id": "S3_MIN_AVG_RATING", "metric_name": "平均星级", "comparator": ">=", "threshold_unit": "stars", "tie_breaker_rank": "8"},
}


class MarketChainError(RuntimeError):
    pass


@dataclass
class Context:
    run_name: str
    direction_id: str
    keyword: str
    site: str
    days: int
    new_product_window_months: str
    sample_top_n: int
    head_top_n: int
    context_row_index: int
    context_source: str
    purpose_type: str = ""
    category_l1: str = ""
    category_l2: str = ""
    parameter_profile_id: str = ""
    parameter_version: str = ""
    parameter_source: str = ""


@dataclass
class BuildArgs:
    market_dir: Path
    market_workbook: Path
    output_dir: Path
    context: Context
    batch_id: str


def latest_market_workbook_in_dir(market_dir: Path) -> Path:
    if not market_dir.exists():
        raise MarketChainError(f"market_dir does not exist: {market_dir}")
    if not market_dir.is_dir():
        raise MarketChainError(f"market_dir is not a directory: {market_dir}")

    canonical_candidates = sorted(
        (
            path
            for path in market_dir.glob("*.xlsx")
            if path.is_file() and not path.name.lower().startswith(DIAGNOSTIC_WORKBOOK_PREFIXES)
        ),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not canonical_candidates:
        raise MarketChainError(
            f"No eligible .xlsx workbook was found in market_dir: {market_dir}. "
            "Provide --market-workbook explicitly or rerun the STEP3 export."
        )
    return canonical_candidates[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build canonical SellerSprite market workbook indexes and STEP3 outputs from the selected raw workbook.",
    )
    parser.add_argument("--market-dir", default=str(DEFAULT_MARKET_DIR_RELATIVE))
    parser.add_argument("--market-workbook", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--context-row-index", type=int, default=1)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--direction-id", default=None)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--site", default=None)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--new-product-window", default=None, help="Months, aligned to SellerSprite market export controls.")
    parser.add_argument("--sample-top-n", type=int, default=None)
    parser.add_argument("--head-top-n", type=int, default=None)
    parser.add_argument("--batch-id", default=None)
    return parser.parse_args()


def parse_int_value(raw_value: str | int | None, field_name: str) -> int:
    try:
        return int(raw_value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise MarketChainError(f"{field_name} must be an integer value, got: {raw_value!r}") from exc


def normalize_new_product_window(value: str) -> str:
    normalized = str(value).strip().lower().rstrip("m")
    if normalized not in {"1", "3", "6", "12"}:
        raise MarketChainError("--new-product-window must resolve to one of: 1, 3, 6, 12.")
    return normalized


def normalize_new_product_window_from_days(value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        return DEFAULT_NEW_PRODUCT_WINDOW
    if normalized not in NEW_PRODUCT_DAYS_TO_WINDOW:
        raise MarketChainError(
            f"Current input 新品定义_天 is not supported by the verified SellerSprite flow: {normalized}. "
            "Use 30, 90, 180, or 365, or pass --new-product-window explicitly."
        )
    return NEW_PRODUCT_DAYS_TO_WINDOW[normalized]


def sanitize_keyword(keyword: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", keyword.strip().lower()).strip("-")
    return cleaned or "market"


def first_present(mapping: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = str(mapping.get(key, "")).strip()
        if value:
            return value
    return ""


def load_route_context(direction_id: str, keyword: str, site: str) -> dict[str, str]:
    route_path = ROOT / CURRENT_ROUTE_RELATIVE
    if not route_path.exists():
        return {}

    rows = load_csv_rows(route_path)
    if len(rows) < 2:
        return {}

    headers = rows[0]
    data_rows = [
        {header: row[idx] if idx < len(row) else "" for idx, header in enumerate(headers)}
        for row in rows[1:]
    ]

    direction_id = direction_id.strip()
    keyword = keyword.strip().casefold()
    site = site.strip().upper()

    matched_row: dict[str, str] | None = None
    for row in data_rows:
        if first_present(row, "任务ID") == direction_id:
            matched_row = row
            break
    if matched_row is None:
        for row in data_rows:
            if first_present(row, "input_value").strip().casefold() == keyword and first_present(row, "site").strip().upper() == site:
                matched_row = row
                break
    if matched_row is None:
        return {}

    return {
        "purpose_type": first_present(matched_row, "purpose_type", "业务目的"),
        "category_l1": first_present(matched_row, "类目大类"),
        "category_l2": first_present(matched_row, "类目子类"),
        "parameter_profile_id": first_present(matched_row, "参数模板ID"),
        "parameter_version": first_present(matched_row, "参数版本"),
        "parameter_source": first_present(matched_row, "参数来源"),
    }


def load_current_context(row_index: int) -> dict[str, str]:
    if row_index <= 0:
        raise MarketChainError("--context-row-index must be >= 1.")

    goal_path = ROOT / CURRENT_GOAL_RELATIVE
    entry_path = ROOT / CURRENT_ENTRY_RELATIVE
    if not goal_path.exists():
        raise MarketChainError(f"Current goal CSV is missing: {goal_path}")
    if not entry_path.exists():
        raise MarketChainError(f"Current market entry CSV is missing: {entry_path}")

    goal_rows = load_csv_rows(goal_path)
    entry_rows = load_csv_rows(entry_path)
    if len(goal_rows) < 2:
        raise MarketChainError(f"Current goal CSV has no data row: {goal_path}")
    if len(entry_rows) <= row_index:
        raise MarketChainError(
            f"--context-row-index {row_index} is out of range for {entry_path}; available rows: {max(len(entry_rows) - 1, 0)}"
        )

    goal_map = {header: goal_rows[1][idx] if idx < len(goal_rows[1]) else "" for idx, header in enumerate(goal_rows[0])}
    entry_map = {header: entry_rows[row_index][idx] if idx < len(entry_rows[row_index]) else "" for idx, header in enumerate(entry_rows[0])}
    route_context = load_route_context(
        entry_map.get("方向ID", "").strip(),
        entry_map.get("方向词", "").strip(),
        entry_map.get("站点", "").strip().upper(),
    )
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
        "purpose_type": route_context.get("purpose_type", ""),
        "category_l1": route_context.get("category_l1", ""),
        "category_l2": route_context.get("category_l2", ""),
        "parameter_profile_id": route_context.get("parameter_profile_id", ""),
        "parameter_version": route_context.get("parameter_version", ""),
        "parameter_source": route_context.get("parameter_source", ""),
    }


def resolve_context(namespace: argparse.Namespace) -> Context:
    current = load_current_context(namespace.context_row_index)
    run_name = (namespace.run_name or current.get("entry_run_name") or current.get("goal_run_name") or "").strip()
    direction_id = (namespace.direction_id or current.get("direction_id") or "").strip()
    keyword = (namespace.keyword or current.get("keyword") or "").strip()
    site = (namespace.site or current.get("site") or "").strip().upper()
    days = namespace.days if namespace.days is not None else parse_int_value(current.get("days") or DEFAULT_DAYS, "时间范围_天")
    if namespace.new_product_window is not None:
        new_product_window_months = normalize_new_product_window(namespace.new_product_window)
    else:
        new_product_window_months = normalize_new_product_window_from_days(current.get("new_product_days", ""))
    sample_top_n = (
        namespace.sample_top_n
        if namespace.sample_top_n is not None
        else parse_int_value(current.get("sample_top_n") or DEFAULT_SAMPLE_TOP_N, "样本数前N")
    )
    head_top_n = (
        namespace.head_top_n
        if namespace.head_top_n is not None
        else parse_int_value(current.get("head_top_n") or DEFAULT_HEAD_TOP_N, "头部商品前N")
    )
    context = Context(
        run_name=run_name,
        direction_id=direction_id,
        keyword=keyword,
        site=site,
        days=days,
        new_product_window_months=new_product_window_months,
        sample_top_n=sample_top_n,
        head_top_n=head_top_n,
        context_row_index=namespace.context_row_index,
        context_source=f"inputs/selection_run_current/01 row {namespace.context_row_index}",
        purpose_type=current.get("purpose_type", "").strip(),
        category_l1=current.get("category_l1", "").strip(),
        category_l2=current.get("category_l2", "").strip(),
        parameter_profile_id=current.get("parameter_profile_id", "").strip(),
        parameter_version=current.get("parameter_version", "").strip(),
        parameter_source=current.get("parameter_source", "").strip(),
    )
    validate_context(context)
    return context


def validate_context(context: Context) -> None:
    missing: list[str] = []
    if not context.run_name:
        missing.append("运行名称")
    if not context.direction_id:
        missing.append("方向ID")
    if not context.keyword:
        missing.append("方向词/关键词")
    if not context.site:
        missing.append("站点")
    if missing:
        raise MarketChainError(
            "Missing required current-input context for STEP3 outputs: "
            + ", ".join(missing)
            + ". Fill inputs/selection_run_current/01 manually or pass explicit CLI overrides."
        )


def resolve_build_args(namespace: argparse.Namespace) -> BuildArgs:
    context = resolve_context(namespace)
    market_dir = Path(namespace.market_dir).expanduser()
    if not market_dir.is_absolute():
        market_dir = ROOT / market_dir
    market_dir = ensure_within_repo(ROOT, market_dir, "market_dir")
    if namespace.market_workbook:
        market_workbook = Path(namespace.market_workbook).expanduser()
        if not market_workbook.is_absolute():
            market_workbook = ROOT / market_workbook
        market_workbook = ensure_within_repo(ROOT, market_workbook, "market_workbook")
    else:
        market_workbook = latest_market_workbook_in_dir(market_dir)
    if namespace.output_dir:
        output_dir = Path(namespace.output_dir).expanduser()
        if not output_dir.is_absolute():
            output_dir = ROOT / output_dir
        output_dir = ensure_within_repo(ROOT, output_dir, "output_dir")
    else:
        output_dir = default_output_dir(ROOT)
    batch_id = namespace.batch_id or f"MARKET_GATE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return BuildArgs(
        market_dir=market_dir,
        market_workbook=market_workbook,
        output_dir=output_dir,
        context=context,
        batch_id=batch_id,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_workbook_container(path: Path) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(path) as workbook:
            names = set(workbook.namelist())
    except zipfile.BadZipFile as exc:
        return "FAIL", str(exc)
    if "xl/workbook.xml" not in names:
        return "FAIL", "missing xl/workbook.xml"
    return "PASS", ""


def infer_controls_from_canonical_name(file_name: str) -> dict[str, str]:
    match = re.match(
        r"^market-report-(?P<site>[a-z]{2})-(?P<keyword>.+)-d(?P<days>\d+)-new(?P<new>\d+)m-sample(?P<sample>\d+)-head(?P<head>\d+)-(?P<stamp>\d{8}_\d{6})\.xlsx$",
        file_name,
    )
    if not match:
        return {}
    return {
        "site": match.group("site").upper(),
        "keyword_slug": match.group("keyword"),
        "days": match.group("days"),
        "new_product_window_months": match.group("new"),
        "sample_top_n": match.group("sample"),
        "head_top_n": match.group("head"),
        "captured_at": match.group("stamp"),
    }


def assert_selected_workbook_matches_context(path: Path, context: Context) -> dict[str, str]:
    inferred = infer_controls_from_canonical_name(path.name)
    if not inferred:
        return {}

    mismatches: list[str] = []
    expected_keyword_slug = sanitize_keyword(context.keyword)
    comparisons = {
        "site": context.site,
        "days": str(context.days),
        "new_product_window_months": context.new_product_window_months,
        "sample_top_n": str(context.sample_top_n),
        "head_top_n": str(context.head_top_n),
        "keyword_slug": expected_keyword_slug,
    }
    for key, expected in comparisons.items():
        actual = inferred.get(key, "")
        if actual and actual != expected:
            mismatches.append(f"{key}: expected {expected}, got {actual}")
    if mismatches:
        raise MarketChainError(
            "Selected workbook does not match resolved export controls: "
            + "; ".join(mismatches)
        )
    return inferred


def load_field_order(file_name: str) -> list[str]:
    standard_path = ROOT / STANDARD_99_RELATIVE
    rows = list(csv.DictReader(standard_path.read_text(encoding="utf-8-sig").splitlines()))
    return [row["field_name"] for row in rows if row["file_name"] == file_name]


def load_standard_step3_rules() -> list[dict[str, str]]:
    standard_path = ROOT / STANDARD_90_RELATIVE
    rows = list(csv.DictReader(standard_path.read_text(encoding="utf-8-sig").splitlines()))
    filtered = [row for row in rows if row.get("step_code") == "STEP3" and row.get("enabled") == "TRUE"]
    filtered.sort(key=lambda row: parse_int_value(row.get("tie_breaker_rank") or 999, "tie_breaker_rank"))
    return filtered


def severity_to_rule_flags(severity: str) -> tuple[str, str]:
    normalized = str(severity or "").strip().lower()
    if normalized == "hard":
        return "TRUE", "FAIL"
    return "FALSE", "HOLD"


def resolve_parameter_source(context: Context) -> Path:
    raw_value = context.parameter_source.strip() or str(DEFAULT_CATEGORY_PROFILE_RELATIVE)
    path = Path(raw_value).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return ensure_within_repo(ROOT, path, "parameter_source")


def load_profile_step3_rules(context: Context) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if not context.parameter_profile_id:
        return [], {
            "mode": "canonical",
            "profile_id": "",
            "rule_source": str(STANDARD_90_RELATIVE),
            "skipped_parameters": [],
        }

    source_path = resolve_parameter_source(context)
    if not source_path.exists():
        raise MarketChainError(f"Category gate profile CSV is missing: {source_path}")

    rows = list(csv.DictReader(source_path.read_text(encoding="utf-8-sig").splitlines()))
    matched_rows = [
        row
        for row in rows
        if row.get("profile_id", "").strip() == context.parameter_profile_id
        and row.get("category_l1", "").strip() == context.category_l1
        and row.get("category_l2", "").strip() == context.category_l2
        and row.get("purpose_type", "").strip() == context.purpose_type
        and row.get("enabled", "").strip().lower() == "true"
    ]
    if not matched_rows:
        raise MarketChainError(
            "No enabled category gate rows matched the current case: "
            f"profile_id={context.parameter_profile_id}, category_l1={context.category_l1}, "
            f"category_l2={context.category_l2}, purpose_type={context.purpose_type}"
        )

    rules: list[dict[str, str]] = []
    skipped_parameters: list[dict[str, str]] = []
    for row in matched_rows:
        parameter_name = row.get("parameter_name", "").strip()
        spec = PROFILE_PARAMETER_SPECS.get(parameter_name)
        if spec is None:
            skipped_parameters.append(
                {
                    "parameter_name": parameter_name,
                    "severity": row.get("severity", "").strip(),
                    "note": row.get("note", "").strip(),
                }
            )
            continue
        hard_fail, blank_action = severity_to_rule_flags(row.get("severity", ""))
        rules.append(
            {
                "step_code": "STEP3",
                "step_name": "市场调研筛市场",
                "rule_id": spec["rule_id"],
                "metric_name": spec["metric_name"],
                "metric_scope": "market",
                "comparator": spec["comparator"],
                "threshold_value": row.get("threshold_value", "").strip(),
                "threshold_unit": row.get("unit", "").strip() or spec["threshold_unit"],
                "enabled": "TRUE",
                "hard_fail": hard_fail,
                "blank_action": blank_action,
                "tie_breaker_rank": spec["tie_breaker_rank"],
                "note": row.get("note", "").strip(),
            }
        )
    rules.sort(key=lambda row: parse_int_value(row.get("tie_breaker_rank") or 999, "tie_breaker_rank"))
    return rules, {
        "mode": "profile",
        "profile_id": context.parameter_profile_id,
        "rule_source": str(source_path.relative_to(ROOT)),
        "skipped_parameters": skipped_parameters,
    }


def load_step3_rules(context: Context) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if context.parameter_profile_id:
        return load_profile_step3_rules(context)
    rules = load_standard_step3_rules()
    return rules, {
        "mode": "canonical",
        "profile_id": "",
        "rule_source": str(STANDARD_90_RELATIVE),
        "skipped_parameters": [],
    }


def safe_ratio_number(value: Any) -> str:
    if value is None or str(value).strip() == "":
        return ""
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric <= 1:
            numeric *= 100
        text = f"{numeric:.4f}".rstrip("0").rstrip(".")
        return text
    text = str(value).strip()
    if text.endswith("%"):
        text = text[:-1].strip()
    try:
        numeric = float(text)
    except ValueError:
        return text
    if numeric <= 1:
        numeric *= 100
    return f"{numeric:.4f}".rstrip("0").rstrip(".")


def safe_float(value: str) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    if text.endswith("%"):
        text = text[:-1].strip()
    try:
        return float(text)
    except ValueError:
        return None


def build_cleaned_rows(
    source_rows: list[tuple[int, list[Any]]],
    header_mapping: dict[str, list[int]],
    workbook_path: Path,
    sheet_name: str,
    context: Context,
) -> list[dict[str, str]]:
    cleaned_rows: list[dict[str, str]] = []
    for row_index, row_values in source_rows:
        candidate_name = normalize_text(first_value(row_values, header_mapping, "细分市场"))
        market_path = normalize_text(first_value(row_values, header_mapping, "市场路径"))
        if not candidate_name and not market_path:
            continue

        sample_counts = parse_sample_counts(normalize_text(first_value(row_values, header_mapping, "样本数量")))
        cleaned_rows.append(
            {
                "运行名称": context.run_name,
                "方向ID": context.direction_id,
                "关键词": context.keyword,
                "站点": context.site or guess_site_from_workbook(workbook_path),
                "市场路径": market_path,
                "候选市场名称": candidate_name,
                "商品样本数": sample_counts["商品样本数"],
                "品牌样本数": sample_counts["品牌样本数"],
                "卖家样本数": sample_counts["卖家样本数"],
                "月总销量": safe_number_text(first_value(row_values, header_mapping, "月总销量")),
                "月均销量": safe_number_text(first_value(row_values, header_mapping, "月均销量", 0)),
                "月均销售额": safe_number_text(first_value(row_values, header_mapping, "月均销售额", 0)),
                "平均价格": safe_number_text(first_value(row_values, header_mapping, "平均价格", 0)),
                "平均评分数": safe_number_text(first_value(row_values, header_mapping, "平均评分数", 0)),
                "平均星级": safe_number_text(first_value(row_values, header_mapping, "平均星级", 0)),
                "新品数量": safe_number_text(first_value(row_values, header_mapping, "新品数量")),
                "新品占比_pct": safe_ratio_number(first_value(row_values, header_mapping, "新品占比")),
                "商品集中度": safe_number_text(first_value(row_values, header_mapping, "商品集中度")),
                "品牌集中度": safe_number_text(first_value(row_values, header_mapping, "品牌集中度")),
                "卖家集中度": safe_number_text(first_value(row_values, header_mapping, "卖家集中度")),
                "来源工作簿": workbook_path.name,
                "来源工作表": sheet_name,
                "来源数据行": str(row_index),
            }
        )
    return cleaned_rows


def evaluate_rule(metric_value: str, rule: dict[str, str]) -> tuple[str, str]:
    value = safe_float(metric_value)
    comparator = rule["comparator"]
    threshold = safe_float(rule["threshold_value"])
    if value is None or threshold is None:
        return rule["blank_action"], f"blank->{rule['blank_action']}"

    passed = False
    if comparator == ">=":
        passed = value >= threshold
    elif comparator == "<=":
        passed = value <= threshold
    elif comparator == "==":
        passed = value == threshold
    else:
        raise MarketChainError(f"Unsupported comparator in STEP3 rule: {comparator}")

    if passed:
        return "PASS", "comparison_pass"
    if rule["hard_fail"] == "TRUE":
        return "FAIL", "hard_fail_threshold"
    return "HOLD", "soft_fail_threshold"


def build_gate_rows(cleaned_rows: list[dict[str, str]], rules: list[dict[str, str]], batch_id: str) -> tuple[list[dict[str, str]], dict[str, int]]:
    gate_rows: list[dict[str, str]] = []
    summary = {"PASS": 0, "FAIL": 0, "HOLD": 0}
    for row in cleaned_rows:
        non_pass_codes: list[str] = []
        pass_count = 0
        fail_count = 0
        overall_status = "PASS"
        for rule in rules:
            outcome, _detail = evaluate_rule(row.get(rule["metric_name"], ""), rule)
            if outcome == "PASS":
                pass_count += 1
                continue
            fail_count += 1
            non_pass_codes.append(f"{rule['rule_id']}:{outcome}")
            if outcome == "FAIL":
                overall_status = "FAIL"
            elif outcome == "HOLD" and overall_status != "FAIL":
                overall_status = "HOLD"

        summary[overall_status] += 1
        gate_rows.append(
            {
                "运行名称": row["运行名称"],
                "方向ID": row["方向ID"],
                "关键词": row["关键词"],
                "站点": row["站点"],
                "候选市场名称": row["候选市场名称"],
                "平均价格": row["平均价格"],
                "月总销量": row["月总销量"],
                "新品占比_pct": row["新品占比_pct"],
                "商品集中度": row["商品集中度"],
                "品牌集中度": row["品牌集中度"],
                "卖家集中度": row["卖家集中度"],
                "命中规则数": str(pass_count),
                "失败规则数": str(fail_count),
                "整体状态": overall_status,
                "失败原因代码": ";".join(non_pass_codes),
                "是否下推到Step4": "是" if overall_status == "PASS" else "否",
                "下推批次号": batch_id,
            }
        )
    return gate_rows, summary


def write_ordered_csv(path: Path, field_order: list[str], rows: list[dict[str, str]]) -> None:
    ordered_rows = [[row.get(field, "") for field in field_order] for row in rows]
    write_csv_atomic(path, field_order, ordered_rows)


def build_workbook_inventory(market_dir: Path, selected_workbook: Path) -> list[dict[str, str]]:
    inventory: list[dict[str, str]] = []
    workbooks = sorted(market_dir.glob("*.xlsx"), key=lambda item: item.stat().st_mtime, reverse=True)
    for workbook in workbooks:
        naming_contract = infer_controls_from_canonical_name(workbook.name)
        xlsx_status, xlsx_error = validate_workbook_container(workbook)
        lowered = workbook.name.lower()
        if lowered.startswith(DIAGNOSTIC_WORKBOOK_PREFIXES):
            role = "DIAGNOSTIC_SET"
        elif workbook.resolve() == selected_workbook.resolve():
            role = "KEEP_SET_SELECTED"
        elif lowered.startswith(CANONICAL_WORKBOOK_PREFIX):
            role = "KEEP_SET_CANDIDATE"
        else:
            role = "ARCHIVE_SET"
        inventory.append(
            {
                "file_name": workbook.name,
                "file_path": str(workbook),
                "file_size_bytes": str(workbook.stat().st_size),
                "modified_at": datetime.fromtimestamp(workbook.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
                "sha256": sha256_file(workbook),
                "role": role,
                "selected": "YES" if workbook.resolve() == selected_workbook.resolve() else "NO",
                "naming_status": "CANONICAL" if naming_contract else "NONCANONICAL_OR_ARCHIVE",
                "inferred_site": naming_contract.get("site", ""),
                "inferred_keyword_slug": naming_contract.get("keyword_slug", ""),
                "inferred_days": naming_contract.get("days", ""),
                "inferred_new_product_window_months": naming_contract.get("new_product_window_months", ""),
                "inferred_sample_top_n": naming_contract.get("sample_top_n", ""),
                "inferred_head_top_n": naming_contract.get("head_top_n", ""),
                "xlsx_status": xlsx_status,
                "xlsx_error": xlsx_error,
            }
        )
    return inventory


def build_workbook_index_markdown(inventory: list[dict[str, str]], selected_workbook: Path) -> str:
    lines = [
        "# Market Workbook Index",
        "",
        f"- Workbook selection rule: `{WORKBOOK_SELECTION_RULE}`",
        f"- Selected workbook: `{selected_workbook}`",
        "",
        "| file_name | role | selected | naming_status | inferred_site | inferred_days | inferred_new | inferred_sample | inferred_head | xlsx_status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in inventory:
        lines.append(
            f"| {item['file_name']} | {item['role']} | {item['selected']} | {item['naming_status']} | "
            f"{item['inferred_site']} | {item['inferred_days']} | {item['inferred_new_product_window_months']} | "
            f"{item['inferred_sample_top_n']} | {item['inferred_head_top_n']} | {item['xlsx_status']} |"
        )
    return "\n".join(lines) + "\n"


def build_output_index_rows(
    output_dir: Path,
    market_workbook: Path,
    workbook_index_csv: Path,
    workbook_index_md: Path,
    raw_index_csv: Path,
    cleaned_csv: Path,
    compat_cleaned_csv: Path,
    gate_csv: Path,
    summary: dict[str, int],
    rule_meta: dict[str, Any],
) -> list[dict[str, str]]:
    rule_source = rule_meta.get("rule_source", str(STANDARD_90_RELATIVE))
    profile_id = rule_meta.get("profile_id", "")
    profile_note = f"profile={profile_id}" if profile_id else "canonical-step3-rules"
    return [
        {
            "artifact_id": "RAW_WORKBOOK",
            "layer": "raw_workbook_layer",
            "artifact_path": str(market_workbook),
            "schema_source": "SellerSprite workbook",
            "control_source": "inputs/selection_run_current/01 + CLI overrides",
            "status": "SELECTED_KEEP_SET",
            "notes": "Selected raw workbook for STEP3 standardization.",
        },
        {
            "artifact_id": "WORKBOOK_INDEX_CSV",
            "layer": "raw_workbook_layer",
            "artifact_path": str(workbook_index_csv),
            "schema_source": "repo-local market workbook index contract",
            "control_source": "runs/manual/10_market inventory",
            "status": "CREATED",
            "notes": "All repo-visible workbooks indexed.",
        },
        {
            "artifact_id": "WORKBOOK_INDEX_MD",
            "layer": "raw_workbook_layer",
            "artifact_path": str(workbook_index_md),
            "schema_source": "repo-local market workbook index contract",
            "control_source": "runs/manual/10_market inventory",
            "status": "CREATED",
            "notes": "Human-readable workbook index summary.",
        },
        {
            "artifact_id": "STEP3_RAW_INDEX",
            "layer": "raw_workbook_layer",
            "artifact_path": str(raw_index_csv),
            "schema_source": "templates/selection_canonical_standards/99_字段数据标准总表.csv",
            "control_source": "selected raw workbook + current input context",
            "status": "CREATED",
            "notes": "Canonical 30 raw index row.",
        },
        {
            "artifact_id": "STEP3_CLEANED",
            "layer": "cleaned_layer",
            "artifact_path": str(cleaned_csv),
            "schema_source": "templates/selection_canonical_standards/99_字段数据标准总表.csv",
            "control_source": "selected raw workbook parse",
            "status": "CREATED",
            "notes": "Canonical 31 cleaned output.",
        },
        {
            "artifact_id": "MARKET_CLEANED_ALIAS",
            "layer": "cleaned_layer",
            "artifact_path": str(compat_cleaned_csv),
            "schema_source": "templates/selection_canonical_standards/99_字段数据标准总表.csv",
            "control_source": "selected raw workbook parse",
            "status": "CREATED",
            "notes": "Compatibility alias of the canonical 31 cleaned output.",
        },
        {
            "artifact_id": "STEP3_GATE_RESULT",
            "layer": "gate_result_layer",
            "artifact_path": str(gate_csv),
            "schema_source": "templates/selection_canonical_standards/99_字段数据标准总表.csv",
            "control_source": rule_source,
            "status": "CREATED",
            "notes": f"Gate summary PASS={summary['PASS']} FAIL={summary['FAIL']} HOLD={summary['HOLD']} ({profile_note}).",
        },
        {
            "artifact_id": "OUTPUT_DIR",
            "layer": "run_output_layer",
            "artifact_path": str(output_dir),
            "schema_source": "repo-local market chain contract",
            "control_source": "output_dir",
            "status": "CREATED",
            "notes": "Ignored runtime output directory for this market chain build.",
        },
    ]


def build_output_index_markdown(
    context: Context,
    market_workbook: Path,
    selected_contract: dict[str, str],
    output_rows: list[dict[str, str]],
    summary: dict[str, int],
    rule_meta: dict[str, Any],
) -> str:
    profile_id = rule_meta.get("profile_id", "")
    skipped_parameters = rule_meta.get("skipped_parameters", [])
    lines = [
        "# SellerSprite Market Chain Output Index",
        "",
        f"- Context source: `{context.context_source}`",
        f"- 运行名称: `{context.run_name}`",
        f"- 方向ID: `{context.direction_id}`",
        f"- 关键词: `{context.keyword}`",
        f"- 站点: `{context.site}`",
        f"- 时间窗: `{context.days}`",
        f"- 新品定义(月): `{context.new_product_window_months}`",
        f"- 样本数前N: `{context.sample_top_n}`",
        f"- 头部商品前N: `{context.head_top_n}`",
        f"- Purpose type: `{context.purpose_type or 'n/a'}`",
        f"- Category profile: `{profile_id or 'canonical-default'}`",
        f"- Category L1/L2: `{context.category_l1 or 'n/a'} / {context.category_l2 or 'n/a'}`",
        f"- Selected workbook: `{market_workbook}`",
        f"- Selected workbook canonical controls: `{json.dumps(selected_contract, ensure_ascii=False) if selected_contract else 'not encoded in filename'}`",
        f"- Gate rule source: `{rule_meta.get('rule_source', str(STANDARD_90_RELATIVE))}`",
        f"- Skipped profile parameters: `{json.dumps(skipped_parameters, ensure_ascii=False) if skipped_parameters else '[]'}`",
        f"- Gate summary: `PASS={summary['PASS']} FAIL={summary['FAIL']} HOLD={summary['HOLD']}`",
        "",
        "| artifact_id | layer | status | artifact_path | notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in output_rows:
        lines.append(
            f"| {row['artifact_id']} | {row['layer']} | {row['status']} | {row['artifact_path']} | {row['notes']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        args = resolve_build_args(parse_args())
        if args.market_workbook.suffix.lower() != ".xlsx":
            raise MarketChainError(f"market_workbook must be an .xlsx file: {args.market_workbook}")

        selected_contract = assert_selected_workbook_matches_context(args.market_workbook, args.context)
        inventory = build_workbook_inventory(args.market_dir, args.market_workbook)
        args.output_dir.mkdir(parents=True, exist_ok=True)

        workbook_index_csv = args.output_dir / WORKBOOK_INDEX_CSV
        workbook_index_md = args.output_dir / WORKBOOK_INDEX_MD
        workbook_index_fields = list(inventory[0].keys()) if inventory else []
        if inventory:
            write_ordered_csv(workbook_index_csv, workbook_index_fields, inventory)
        else:
            write_csv_atomic(workbook_index_csv, ["file_name"], [])
        workbook_index_md.write_text(
            build_workbook_index_markdown(inventory, args.market_workbook),
            encoding="utf-8",
        )

        sheet_name, header_row_index, _raw_headers, header_mapping = find_market_sheet_and_header(args.market_workbook)
        source_rows = read_sheet_rows(args.market_workbook, sheet_name, header_row_index)
        cleaned_rows = build_cleaned_rows(source_rows, header_mapping, args.market_workbook, sheet_name, args.context)
        if not cleaned_rows:
            raise MarketChainError("No market rows were parsed from the selected workbook.")

        raw_index_row = {
            "运行名称": args.context.run_name,
            "方向ID": args.context.direction_id,
            "关键词": args.context.keyword,
            "市场工作簿文件名": args.market_workbook.name,
            "市场工作表": sheet_name,
            "站点": args.context.site,
            "抓取时间": datetime.fromtimestamp(args.market_workbook.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
            "文件路径": str(args.market_workbook),
            "文件大小_bytes": str(args.market_workbook.stat().st_size),
            "解析状态": "PASS",
            "解析失败原因": "",
        }
        rules, rule_meta = load_step3_rules(args.context)
        gate_rows, summary = build_gate_rows(cleaned_rows, rules, args.batch_id)

        raw_index_csv = args.output_dir / RAW_INDEX_FILE
        cleaned_csv = args.output_dir / CLEANED_FILE
        compat_cleaned_csv = args.output_dir / COMPAT_MARKET_CLEANED_FILE
        gate_csv = args.output_dir / GATE_FILE
        write_ordered_csv(raw_index_csv, load_field_order(RAW_INDEX_FILE), [raw_index_row])
        cleaned_field_order = load_field_order(CLEANED_FILE)
        write_ordered_csv(cleaned_csv, cleaned_field_order, cleaned_rows)
        write_ordered_csv(compat_cleaned_csv, cleaned_field_order, cleaned_rows)
        write_ordered_csv(gate_csv, load_field_order(GATE_FILE), gate_rows)

        output_index_rows = build_output_index_rows(
            output_dir=args.output_dir,
            market_workbook=args.market_workbook,
            workbook_index_csv=workbook_index_csv,
            workbook_index_md=workbook_index_md,
            raw_index_csv=raw_index_csv,
            cleaned_csv=cleaned_csv,
            compat_cleaned_csv=compat_cleaned_csv,
            gate_csv=gate_csv,
            summary=summary,
            rule_meta=rule_meta,
        )
        output_index_csv = args.output_dir / OUTPUT_INDEX_CSV
        output_index_md = args.output_dir / OUTPUT_INDEX_MD
        write_ordered_csv(
            output_index_csv,
            ["artifact_id", "layer", "artifact_path", "schema_source", "control_source", "status", "notes"],
            output_index_rows,
        )
        output_index_md.write_text(
            build_output_index_markdown(args.context, args.market_workbook, selected_contract, output_index_rows, summary, rule_meta),
            encoding="utf-8",
        )

        print(f"Selected workbook: {args.market_workbook}")
        print(f"Selected sheet/header row: {sheet_name} / {header_row_index}")
        print(f"Workbook index CSV: {workbook_index_csv}")
        print(f"STEP3 raw index CSV: {raw_index_csv}")
        print(f"STEP3 cleaned CSV: {cleaned_csv}")
        print(f"STEP3 gate CSV: {gate_csv}")
        print(f"Profile id: {rule_meta.get('profile_id') or 'canonical-default'}")
        print(f"Rule source: {rule_meta.get('rule_source')}")
        print(f"Output index MD: {output_index_md}")
        print(f"Gate summary: PASS={summary['PASS']} FAIL={summary['FAIL']} HOLD={summary['HOLD']}")
        return 0
    except (MarketChainError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
