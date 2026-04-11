from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from benchmark_chain_common import BenchmarkChainError, clean_number, ensure_within_repo, log_dir_from_namespace, output_dir_from_namespace, resolve_context_from_namespace, stable_id
from keyword_chain_common import append_jsonl, iso_now, safe_float, timestamp_slug, write_csv_atomic, write_json_atomic
from sellersprite_route_router import resolve_route_decision


RAW_JSON = "product_research_raw.json"
RAW_CSV = "10_产品样本原始结果.csv"
SEED_CSV = "11_产品样本种子池.csv"
GATE_CSV = "12_产品样本下推结果.csv"
MARKET_HANDOFF_JSONL = "13_step1_market_handoff.jsonl"
MARKET_SESSION_BUNDLE_JSON = "13a_step1_market_session_bundle.json"
MARKET_PROBE_SUMMARY_JSON = "13b_step1_market_probe_summary.json"
LATEST_LOG = "latest_product_build_run.json"
RUN_HISTORY = "product_build_runs.jsonl"
RUN_FAILURES = "product_build_failures.jsonl"

RAW_FIELDS = [
    "运行名称",
    "方向ID",
    "关键词",
    "站点",
    "排名",
    "样品ASIN",
    "样品标题",
    "品牌",
    "父体ASIN",
    "价格",
    "评分",
    "评论数",
    "大类BSR文本",
    "销量文本",
    "销售额文本",
    "子体销量文本",
    "变体数",
    "毛利文本",
    "上架文本",
    "配送文本",
    "市场路径",
    "候选市场名称",
    "产品入口URL",
    "市场分析URL",
    "来源文件",
]

SEED_FIELDS = [
    "运行名称",
    "方向ID",
    "关键词",
    "样品ID",
    "样品ASIN",
    "样品标题",
    "品牌",
    "价格",
    "评分",
    "评论数",
    "父体ASIN",
    "变体数",
    "市场路径",
    "候选市场名称",
    "进入种子池状态",
    "去重组ID",
    "去重说明",
    "是否下推到Step4",
    "产品入口URL",
    "市场分析URL",
]

GATE_FIELDS = [
    "运行名称",
    "方向ID",
    "关键词",
    "站点",
    "样品ID",
    "样品ASIN",
    "样品标题",
    "候选市场名称",
    "市场路径",
    "竞品查询词",
    "整体状态",
    "失败原因代码",
    "是否下推到Step4",
    "下推批次号",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build STEP1 product-sample raw/seed/gate CSV outputs from the latest real Product Research workbook artifact.",
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
    parser.add_argument("--product-run", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--log-dir", default=None)
    parser.add_argument("--batch-id", default=None)
    return parser.parse_args()


def persist_run_summary(log_dir: Path, summary: dict[str, Any]) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(log_dir / LATEST_LOG, summary)
    append_jsonl(log_dir / RUN_HISTORY, summary)
    if summary.get("status") != "PASS":
        append_jsonl(log_dir / RUN_FAILURES, summary)


def latest_product_run_path(log_dir: Path) -> Path:
    return ensure_within_repo(log_dir / "latest_product_research_run.json", "latest_product_research_run")


def load_raw_payload(run_summary_path: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    if not run_summary_path.exists():
        raise BenchmarkChainError(
            f"Product research run summary is missing: {run_summary_path}. Run export_product_research.py first.",
            "PRODUCT_RUN_SUMMARY_MISSING",
        )
    summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "PASS":
        raise BenchmarkChainError(
            "Latest product research run is not successful. Resolve the real Product Research export blocker before building 10/11/12 outputs.",
            "PRODUCT_EXPORT_NOT_PASS",
        )
    raw_artifact_path = ensure_within_repo(Path(summary.get("raw_artifact_path", "")), "product_raw_artifact_path")
    if not raw_artifact_path.exists():
        raise BenchmarkChainError(f"Product raw artifact is missing on disk: {raw_artifact_path}", "PRODUCT_RAW_ARTIFACT_MISSING")
    artifact = json.loads(raw_artifact_path.read_text(encoding="utf-8"))
    return summary, artifact, raw_artifact_path


def first_number(value: Any) -> str:
    text = str(value or "").strip()
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", text)
    if not match:
        return ""
    return clean_number(match.group(0))


def raw_rows(context, raw_artifact: dict[str, Any], raw_artifact_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in raw_artifact.get("items", []):
        if not isinstance(item, dict):
            continue
        asin = str(item.get("asin", "")).strip().upper()
        title = str(item.get("title", "")).strip()
        if not asin or not title:
            continue
        rows.append(
            {
                "运行名称": context.run_name,
                "方向ID": context.direction_id,
                "关键词": context.keyword,
                "站点": context.site,
                "排名": str(item.get("rank", "")).strip(),
                "样品ASIN": asin,
                "样品标题": title,
                "品牌": str(item.get("brand", "")).strip(),
                "父体ASIN": str(item.get("parent_asin", "")).strip().upper(),
                "价格": first_number(item.get("price_text")),
                "评分": first_number(item.get("rating_text")),
                "评论数": first_number(item.get("review_text")),
                "大类BSR文本": str(item.get("bsr_text", "")).strip(),
                "销量文本": str(item.get("sales_text", "")).strip(),
                "销售额文本": str(item.get("sales_amount_text", "")).strip(),
                "子体销量文本": str(item.get("child_sales_text", "")).strip(),
                "变体数": first_number(item.get("variation_text")),
                "毛利文本": str(item.get("gross_profit_text", "")).strip(),
                "上架文本": str(item.get("launch_text", "")).strip(),
                "配送文本": str(item.get("delivery_text", "")).strip(),
                "市场路径": str(item.get("category_path", "")).strip(),
                "候选市场名称": str(item.get("candidate_market_name", "")).strip() or context.keyword,
                "产品入口URL": str(item.get("product_source_url", "")).strip(),
                "市场分析URL": str(item.get("market_analysis_url", "")).strip(),
                "来源文件": str(item.get("source_file", "")).strip() or str(raw_artifact_path),
            }
        )
    if not rows:
        raise BenchmarkChainError("Visible product artifact was found, but no canonical 10-row entries could be mapped.", "PRODUCT_RAW_ROWS_EMPTY")
    return rows


def dedupe_group_key(row: dict[str, str]) -> str:
    parent = str(row.get("父体ASIN", "")).strip().upper()
    asin = str(row.get("样品ASIN", "")).strip().upper()
    if parent:
        return f"PARENT:{parent}"
    return f"ASIN:{asin}"


def score_for_seed(row: dict[str, str]) -> tuple[float, float, float, str]:
    reviews = safe_float(row.get("评论数")) or 0.0
    rating = safe_float(row.get("评分")) or 0.0
    price = safe_float(row.get("价格")) or 0.0
    return (reviews, rating, price, row.get("样品ASIN", ""))


def deduped_seed_rows(context, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(dedupe_group_key(row), []).append(row)

    deduped: list[dict[str, str]] = []
    for group_key, group_rows in grouped.items():
        representative = sorted(group_rows, key=score_for_seed, reverse=True)[0]
        group_id = stable_id("PROD", context.site, group_key)
        sample_id = stable_id("PSMP", context.site, representative.get("样品ASIN", ""), representative.get("样品标题", ""))
        deduped.append(
            {
                "运行名称": context.run_name,
                "方向ID": context.direction_id,
                "关键词": context.keyword,
                "样品ID": sample_id,
                "样品ASIN": representative.get("样品ASIN", ""),
                "样品标题": representative.get("样品标题", ""),
                "品牌": representative.get("品牌", ""),
                "价格": representative.get("价格", ""),
                "评分": representative.get("评分", ""),
                "评论数": representative.get("评论数", ""),
                "父体ASIN": representative.get("父体ASIN", ""),
                "变体数": representative.get("变体数", ""),
                "市场路径": representative.get("市场路径", ""),
                "候选市场名称": representative.get("候选市场名称", "") or context.keyword,
                "进入种子池状态": "PASS",
                "去重组ID": group_id,
                "去重说明": "KEEP_HIGHEST_REVIEWS_IN_PARENT_GROUP" if representative.get("父体ASIN", "") else "UNIQUE_ASIN",
                "是否下推到Step4": "是",
                "产品入口URL": representative.get("产品入口URL", ""),
                "市场分析URL": representative.get("市场分析URL", ""),
            }
        )

    deduped.sort(key=score_for_seed, reverse=True)
    if context.max_candidate_samples is not None:
        deduped = deduped[: context.max_candidate_samples]
    return deduped


def gate_rows(context, seed_rows: list[dict[str, str]], batch_id: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in seed_rows:
        rows.append(
            {
                "运行名称": context.run_name,
                "方向ID": context.direction_id,
                "关键词": context.keyword,
                "站点": context.site,
                "样品ID": row.get("样品ID", ""),
                "样品ASIN": row.get("样品ASIN", ""),
                "样品标题": row.get("样品标题", ""),
                "候选市场名称": row.get("候选市场名称", "") or context.keyword,
                "市场路径": row.get("市场路径", ""),
                "竞品查询词": context.keyword,
                "整体状态": "PASS",
                "失败原因代码": "",
                "是否下推到Step4": "是",
                "下推批次号": batch_id,
            }
        )
    return rows


def write_jsonl_atomic(path: Path, records: list[dict[str, Any]]) -> None:
    ensure_within_repo(path, "market_handoff_jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    payload = ""
    if records:
        payload = "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n"
    temp_path.write_text(payload, encoding="utf-8")
    temp_path.replace(path)


def build_market_handoff_records(
    context,
    product_run_summary: dict[str, Any],
    seed_rows: list[dict[str, str]],
    *,
    seed_csv_path: Path,
    run_summary_path: Path,
) -> list[dict[str, Any]]:
    route_decision = resolve_route_decision(
        context_row_index=context.context_row_index,
        run_name=context.run_name,
        direction_id=context.direction_id,
        keyword=context.keyword,
        site=context.site,
    )
    task_id = str(route_decision.get("任务ID", "")).strip()
    purpose_type = str(route_decision.get("purpose_type", "")).strip()
    selected_product_research_url = str(product_run_summary.get("final_url") or product_run_summary.get("attempted_url") or "").strip()
    capture_timestamp = str(product_run_summary.get("timestamp") or iso_now()).strip() or iso_now()
    handoff_records: list[dict[str, Any]] = []
    for row in seed_rows:
        selected_market_href = str(row.get("市场分析URL", "")).strip()
        handoff_records.append(
            {
                "task_id": task_id,
                "purpose_type": purpose_type,
                "run_name": str(row.get("运行名称", "")).strip() or context.run_name,
                "direction_id": str(row.get("方向ID", "")).strip() or context.direction_id,
                "keyword": str(context.keyword or row.get("关键词", "")).strip(),
                "site": str(context.site).strip().upper(),
                "sample_id": str(row.get("样品ID", "")).strip(),
                "sample_asin": str(row.get("样品ASIN", "")).strip().upper(),
                "sample_title": str(row.get("样品标题", "")).strip(),
                "selected_product_research_url": selected_product_research_url,
                "selected_visible_market_analysis_href": selected_market_href,
                "selected_candidate_market_name": str(row.get("候选市场名称", "")).strip(),
                "selected_market_path": str(row.get("市场路径", "")).strip(),
                "handoff_capture_status": "PASS" if selected_market_href else "MISSING_MARKET_ANALYSIS_HREF",
                "capture_timestamp": capture_timestamp,
                "source_seed_csv_path": str(seed_csv_path),
                "product_run_summary_path": str(run_summary_path),
            }
        )
    return handoff_records


def normalize_binding_text(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


def match_probe_seed_row(seed_rows: list[dict[str, str]], probe_summary: dict[str, Any]) -> dict[str, str] | None:
    probe_asin = str(probe_summary.get("sample_asin", "")).strip().upper()
    if probe_asin:
        for row in seed_rows:
            if str(row.get("鏍峰搧ASIN", "")).strip().upper() == probe_asin:
                return row

    probe_title_norm = normalize_binding_text(probe_summary.get("sample_title", ""))
    if probe_title_norm:
        for row in seed_rows:
            if normalize_binding_text(row.get("鏍峰搧鏍囬", "")) == probe_title_norm:
                return row
    return seed_rows[0] if seed_rows else None


def row_value_with_key_hint(row: dict[str, str], hint: str) -> str:
    normalized_hint = str(hint or "").strip().casefold()
    for key, value in row.items():
        if normalized_hint and normalized_hint in str(key or "").casefold():
            return str(value or "").strip()
    return ""


def row_value_with_value_hint(row: dict[str, str], hint: str) -> str:
    normalized_hint = str(hint or "").strip()
    for value in row.values():
        text = str(value or "").strip()
        if normalized_hint and normalized_hint in text:
            return text
    return ""


def build_market_session_bundle(
    context,
    product_run_summary: dict[str, Any],
    seed_rows: list[dict[str, str]],
    *,
    seed_csv_path: Path,
    run_summary_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    route_decision = resolve_route_decision(
        context_row_index=context.context_row_index,
        run_name=context.run_name,
        direction_id=context.direction_id,
        keyword=context.keyword,
        site=context.site,
    )
    task_id = str(route_decision.get("浠诲姟ID", "")).strip()
    purpose_type = str(route_decision.get("purpose_type", "")).strip()
    probe_summary = product_run_summary.get("same_session_market_probe", {})
    if not isinstance(probe_summary, dict):
        probe_summary = {}

    matched_seed = match_probe_seed_row(seed_rows, probe_summary)
    sample_id = ""
    sample_asin = str(probe_summary.get("sample_asin", "")).strip().upper()
    sample_title = str(probe_summary.get("sample_title", "")).strip()
    selected_candidate_market_name = str(probe_summary.get("selected_candidate_market_name", "")).strip()
    selected_market_path = str(probe_summary.get("selected_market_path", "")).strip()
    selected_market_href = str(probe_summary.get("selected_visible_market_analysis_href", "")).strip()

    if matched_seed is not None:
        sample_id = sample_id or row_value_with_key_hint(matched_seed, "id")
        sample_asin = sample_asin or row_value_with_key_hint(matched_seed, "asin").upper()
        selected_market_href = selected_market_href or row_value_with_value_hint(matched_seed, "/v2/market-research")

    bundle = {
        "task_id": task_id,
        "purpose_type": purpose_type,
        "run_name": context.run_name,
        "direction_id": context.direction_id,
        "keyword": context.keyword,
        "site": str(context.site).strip().upper(),
        "sample_id": sample_id,
        "sample_asin": sample_asin,
        "sample_title": sample_title,
        "selected_product_research_url": str(probe_summary.get("selected_product_research_url", "")).strip()
        or str(product_run_summary.get("final_url") or product_run_summary.get("attempted_url") or "").strip(),
        "selected_visible_market_analysis_href": selected_market_href,
        "selected_candidate_market_name": selected_candidate_market_name,
        "selected_market_path": selected_market_path,
        "row_visible": bool(probe_summary.get("row_visible")),
        "market_analysis_link_visible": bool(probe_summary.get("market_analysis_link_visible")),
        "same_session_probe_status": str(probe_summary.get("same_session_probe_status", "MISSING")).strip() or "MISSING",
        "same_session_probe_stage": str(probe_summary.get("same_session_probe_stage", "STEP1_MARKET_SESSION_BUNDLE_MISSING")).strip()
        or "STEP1_MARKET_SESSION_BUNDLE_MISSING",
        "same_session_probe_final_url": str(probe_summary.get("same_session_probe_final_url", "")).strip(),
        "same_session_probe_final_title": str(probe_summary.get("same_session_probe_final_title", "")).strip(),
        "session_storage_dump": probe_summary.get("session_storage_dump", {}) if isinstance(probe_summary.get("session_storage_dump", {}), dict) else {},
        "market_page_session_storage_dump": probe_summary.get("market_page_session_storage_dump", {})
        if isinstance(probe_summary.get("market_page_session_storage_dump", {}), dict)
        else {},
        "popup_or_new_page_observed": bool(probe_summary.get("popup_or_new_page_observed")),
        "opener_chain": str(probe_summary.get("opener_chain", "")).strip(),
        "workbook_download_attempted": bool(probe_summary.get("workbook_download_attempted")),
        "login_redirect_timing": str(probe_summary.get("login_redirect_timing", "")).strip(),
        "capture_timestamp": str(probe_summary.get("capture_timestamp") or product_run_summary.get("timestamp") or iso_now()).strip() or iso_now(),
        "source_seed_csv_path": str(seed_csv_path),
        "product_run_summary_path": str(run_summary_path),
    }

    probe_record = dict(bundle)
    probe_record["product_run_status"] = str(product_run_summary.get("status", "")).strip()
    probe_record["product_run_reason_code"] = str(product_run_summary.get("reason_code", "")).strip()
    probe_record["same_session_probe_requested"] = bool(product_run_summary.get("same_session_probe_requested"))
    return bundle, probe_record


def main() -> int:
    args = parse_args()
    context = resolve_context_from_namespace(args, require_direction_id=False)
    output_dir = output_dir_from_namespace(args)
    log_dir = log_dir_from_namespace(args)
    run_summary_path = ensure_within_repo(Path(args.product_run), "product_run") if args.product_run else latest_product_run_path(log_dir)
    batch_id = str(args.batch_id or f"STEP1_PRODUCT_{timestamp_slug()}")
    summary: dict[str, Any] = {
        "timestamp": iso_now(),
        "module": "product_chain_build",
        "status": "BLOCKED",
        "reason_code": "",
        "message": "",
        "运行名称": context.run_name,
        "方向ID": context.direction_id,
        "方向词": context.keyword,
        "站点": context.site,
        "output_dir": str(output_dir),
    }

    try:
        product_run_summary, raw_artifact, raw_artifact_path = load_raw_payload(run_summary_path)
        raw_rows_output = raw_rows(context, raw_artifact, raw_artifact_path)
        seed_rows_output = deduped_seed_rows(context, raw_rows_output)
        if not seed_rows_output:
            raise BenchmarkChainError("Product raw rows were available, but no seed rows survived dedupe.", "PRODUCT_SEED_ROWS_EMPTY")
        gate_rows_output = gate_rows(context, seed_rows_output, batch_id)

        output_dir.mkdir(parents=True, exist_ok=True)
        raw_csv_path = ensure_within_repo(output_dir / RAW_CSV, "product_raw_csv")
        seed_csv_path = ensure_within_repo(output_dir / SEED_CSV, "product_seed_csv")
        gate_csv_path = ensure_within_repo(output_dir / GATE_CSV, "product_gate_csv")
        market_handoff_path = ensure_within_repo(output_dir / MARKET_HANDOFF_JSONL, "market_handoff_path")
        market_session_bundle_path = ensure_within_repo(output_dir / MARKET_SESSION_BUNDLE_JSON, "market_session_bundle_path")
        market_probe_summary_path = ensure_within_repo(output_dir / MARKET_PROBE_SUMMARY_JSON, "market_probe_summary_path")
        write_csv_atomic(raw_csv_path, RAW_FIELDS, [[row.get(field, "") for field in RAW_FIELDS] for row in raw_rows_output])
        write_csv_atomic(seed_csv_path, SEED_FIELDS, [[row.get(field, "") for field in SEED_FIELDS] for row in seed_rows_output])
        write_csv_atomic(gate_csv_path, GATE_FIELDS, [[row.get(field, "") for field in GATE_FIELDS] for row in gate_rows_output])
        market_handoff_records = build_market_handoff_records(
            context,
            product_run_summary,
            seed_rows_output,
            seed_csv_path=seed_csv_path,
            run_summary_path=run_summary_path,
        )
        write_jsonl_atomic(market_handoff_path, market_handoff_records)
        market_session_bundle, market_probe_summary = build_market_session_bundle(
            context,
            product_run_summary,
            seed_rows_output,
            seed_csv_path=seed_csv_path,
            run_summary_path=run_summary_path,
        )
        write_json_atomic(market_session_bundle_path, market_session_bundle)
        write_json_atomic(market_probe_summary_path, market_probe_summary)

        summary["status"] = "PASS"
        summary["reason_code"] = "PASS"
        summary["message"] = "Product entry outputs 10/11/12 were built successfully."
        summary["product_run_summary"] = str(run_summary_path)
        summary["product_export_status"] = product_run_summary.get("status", "")
        summary["raw_artifact_path"] = str(raw_artifact_path)
        summary["raw_csv_path"] = str(raw_csv_path)
        summary["seed_csv_path"] = str(seed_csv_path)
        summary["gate_csv_path"] = str(gate_csv_path)
        summary["market_handoff_path"] = str(market_handoff_path)
        summary["market_session_bundle_path"] = str(market_session_bundle_path)
        summary["market_probe_summary_path"] = str(market_probe_summary_path)
        summary["raw_row_count"] = len(raw_rows_output)
        summary["seed_row_count"] = len(seed_rows_output)
        summary["gate_row_count"] = len(gate_rows_output)
        summary["market_handoff_count"] = len(market_handoff_records)
        summary["same_session_probe_status"] = market_session_bundle.get("same_session_probe_status", "")
        summary["same_session_probe_stage"] = market_session_bundle.get("same_session_probe_stage", "")
        summary["batch_id"] = batch_id
    except BenchmarkChainError as exc:
        summary["status"] = "BLOCKED"
        summary["reason_code"] = exc.reason_code
        summary["message"] = str(exc)
    except Exception as exc:
        summary["status"] = "BLOCKED"
        summary["reason_code"] = "PRODUCT_BUILD_UNHANDLED_ERROR"
        summary["message"] = str(exc)

    persist_run_summary(log_dir, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
