from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from benchmark_chain_common import resolve_context_from_namespace
from keyword_chain_common import (
    OUTPUTS_ROOT,
    ROOT,
    ensure_within_repo,
    iso_now,
    load_csv_rows,
    parse_int_value,
    safe_float,
    timestamp_slug,
    write_csv_atomic,
    write_json_atomic,
)
from sellersprite_route_router import MARKET_DISCOVERY, PRODUCT_IDEA_VALIDATION, resolve_route_decision


DEFAULT_BATCH_SUMMARY = ROOT / "logs" / "direction_batch" / "latest_run.json"
DEFAULT_LOG_DIR = ROOT / "logs" / "candidate_pool"
STANDARD_99_PATH = ROOT / "templates" / "selection_canonical_standards" / "99_字段数据标准总表.csv"

INTERMEDIATE_FILE = "03_候选市场与候选品初筛池.csv"
FINAL_FILE = "60_候选样品池.csv"
FINAL_MD = "60_候选样品池.md"
SUMMARY_JSON = "candidate_pool_summary.json"
LATEST_RUN_FILE = "latest_run.json"
RUN_HISTORY_FILE = "candidate_pool_runs.jsonl"
RUN_FAILURE_FILE = "candidate_pool_failures.jsonl"

STEP4_SEED_FILE = "41_候选产品种子池.csv"
STEP4_GATE_FILE = "42_竞品基准下推结果.csv"
STEP1_SEED_FILE = "11_产品样本种子池.csv"
STEP1_GATE_FILE = "12_产品样本下推结果.csv"

INTERMEDIATE_FIELDS = [
    "运行名称",
    "方向ID",
    "方向词",
    "来源关键词",
    "站点",
    "样品ID",
    "样品ASIN",
    "样品标题",
    "品牌",
    "市场路径",
    "候选市场名称",
    "样品价格",
    "评分",
    "评论数",
    "去重组ID",
    "近义合并组ID",
    "样品来源阶段",
    "样品来源批次号",
    "来源记录",
    "市场下推状态",
    "竞品下推状态",
    "关键词价值状态",
    "广告依赖状态",
    "当前池状态",
    "备注",
]

TITLE_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "pack",
    "pcs",
    "piece",
    "pieces",
    "toy",
    "toys",
    "fidget",
    "squishy",
    "squeeze",
    "stress",
    "ball",
    "balls",
    "kids",
    "kid",
    "adult",
    "adults",
    "mini",
    "small",
    "sensory",
    "stuffers",
    "stuffer",
}

FIELD_RUN_NAME = "\u8fd0\u884c\u540d\u79f0"
FIELD_DIRECTION_ID = "\u65b9\u5411ID"
FIELD_DIRECTION_WORD = "\u65b9\u5411\u8bcd"
FIELD_KEYWORD = "\u5173\u952e\u8bcd"
FIELD_SOURCE_KEYWORD = "\u6765\u6e90\u5173\u952e\u8bcd"
FIELD_SITE = "\u7ad9\u70b9"
FIELD_SAMPLE_ID = "\u6837\u54c1ID"
FIELD_SAMPLE_ASIN = "\u6837\u54c1ASIN"
FIELD_SAMPLE_TITLE = "\u6837\u54c1\u6807\u9898"
FIELD_BRAND = "\u54c1\u724c"
FIELD_MARKET_PATH = "\u5e02\u573a\u8def\u5f84"
FIELD_CANDIDATE_MARKET = "\u5019\u9009\u5e02\u573a\u540d\u79f0"
FIELD_SAMPLE_PRICE = "\u6837\u54c1\u4ef7\u683c"
FIELD_PRICE = "\u4ef7\u683c"
FIELD_RATING = "\u8bc4\u5206"
FIELD_REVIEWS = "\u8bc4\u8bba\u6570"
FIELD_DEDUPE_GROUP_ID = "\u53bb\u91cd\u7ec4ID"
FIELD_MERGE_GROUP_ID = "\u8fd1\u4e49\u5408\u5e76\u7ec4ID"
FIELD_SOURCE_STAGE = "\u6837\u54c1\u6765\u6e90\u9636\u6bb5"
FIELD_SOURCE_BATCH = "\u6837\u54c1\u6765\u6e90\u6279\u6b21\u53f7"
FIELD_SOURCE_RECORD = "\u6765\u6e90\u8bb0\u5f55"
FIELD_MARKET_STATUS = "\u5e02\u573a\u4e0b\u63a8\u72b6\u6001"
FIELD_BENCHMARK_STATUS = "\u7ade\u54c1\u4e0b\u63a8\u72b6\u6001"
FIELD_KEYWORD_VALUE_STATUS = "\u5173\u952e\u8bcd\u4ef7\u503c\u72b6\u6001"
FIELD_AD_DEPENDENCY_STATUS = "\u5e7f\u544a\u4f9d\u8d56\u72b6\u6001"
FIELD_POOL_STATUS = "\u5f53\u524d\u6c60\u72b6\u6001"
FIELD_NOTE = "\u5907\u6ce8"
FIELD_OVERALL_STATUS = "\u6574\u4f53\u72b6\u6001"
FIELD_FAILURE_REASON = "\u5931\u8d25\u539f\u56e0\u4ee3\u7801"
FIELD_PUSH_BATCH = "\u4e0b\u63a8\u6279\u6b21\u53f7"
FIELD_BENCHMARK_QUERY = "\u7ade\u54c1\u67e5\u8be2\u8bcd"


class CandidatePoolError(RuntimeError):
    def __init__(self, message: str, reason_code: str = "CANDIDATE_POOL_ERROR") -> None:
        super().__init__(message)
        self.reason_code = reason_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the runtime intermediate candidate pool and final 60 candidate pool from structured STEP3/STEP4 outputs.",
    )
    parser.add_argument("--context-row-index", type=int, default=1)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--direction-id", default=None)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--site", default=None)
    parser.add_argument("--batch-summary", default=str(DEFAULT_BATCH_SUMMARY))
    parser.add_argument("--queue-csv", default=None)
    parser.add_argument("--nightly-state", default=None)
    parser.add_argument("--step1-seed-csv", default=None)
    parser.add_argument("--step1-gate-csv", default=None)
    parser.add_argument("--step2-gate-csv", default=None)
    parser.add_argument("--step3-gate-csv", default=None)
    parser.add_argument("--step4-seed-csv", default=None)
    parser.add_argument("--step4-gate-csv", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--batch-id", default=None)
    return parser.parse_args()


def repo_path(raw_path: str | None, label: str) -> Path:
    if not raw_path:
        raise CandidatePoolError(f"Missing path for {label}.", "PATH_MISSING")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return ensure_within_repo(path, label)


def default_output_dir(batch_id: str) -> Path:
    return ensure_within_repo(OUTPUTS_ROOT / batch_id / "02_generated_outputs", "output_dir")


def append_jsonl(path: Path, payload: Any) -> None:
    ensure_within_repo(path, "jsonl_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_dict_rows(path: Path) -> list[dict[str, str]]:
    rows = load_csv_rows(path)
    if not rows:
        return []
    headers = rows[0]
    return [
        {header: row[idx] if idx < len(row) else "" for idx, header in enumerate(headers)}
        for row in rows[1:]
    ]


def load_field_order(file_name: str) -> list[str]:
    rows = list(csv.DictReader(STANDARD_99_PATH.read_text(encoding="utf-8-sig").splitlines()))
    return [row["field_name"] for row in rows if row["file_name"] == file_name]


def parse_snapshot(raw_value: str) -> dict[str, Any]:
    text = str(raw_value or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"raw_snapshot": text}
    return payload if isinstance(payload, dict) else {"value": payload}


def normalize_status(value: str) -> str:
    normalized = str(value or "").strip().upper()
    if normalized in {"PASS", "FAIL", "HOLD"}:
        return normalized
    if normalized == "BLOCKED":
        return "HOLD"
    return "HOLD"


def normalize_runtime_status(value: str, blank_default: str = "HOLD") -> str:
    normalized = str(value or "").strip().upper()
    if normalized in {"PASS", "FAIL", "HOLD", "SOURCE_EMPTY", "FALLBACK_NEXT", "BLOCKED"}:
        return normalized
    return blank_default


def join_unique(values: list[str]) -> str:
    seen: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.append(text)
    return "; ".join(seen)


def stable_id(prefix: str, *parts: str) -> str:
    raw = "|".join(str(part or "").strip() for part in parts if str(part or "").strip())
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}_{digest}"


def normalize_title_tokens(title: str) -> list[str]:
    tokens = re.findall(r"[0-9A-Za-z\u4e00-\u9fff]+", str(title or "").casefold())
    normalized: list[str] = []
    for token in tokens:
        if len(token) <= 2 or token in TITLE_STOPWORDS:
            continue
        if token.endswith("s") and len(token) > 4:
            token = token[:-1]
        if token not in normalized:
            normalized.append(token)
    return normalized


def merge_group_id(title: str, brand: str, market_name: str) -> str:
    signature = "|".join(normalize_title_tokens(title)[:5]) or str(title or "").strip().casefold()
    return stable_id("MERGE", brand.casefold(), market_name.casefold(), signature)


def candidate_score(row: dict[str, str]) -> tuple[float, float, float, str]:
    reviews = safe_float(row.get("评论数")) or 0.0
    rating = safe_float(row.get("评分")) or 0.0
    price = safe_float(row.get("样品价格")) or 0.0
    return (reviews, rating, price, row.get("样品ASIN", ""))


def aggregate_status(values: list[str], blank_default: str = "HOLD") -> str:
    normalized = [normalize_status(value) for value in values if str(value or "").strip()]
    if not normalized:
        return blank_default
    if any(value == "FAIL" for value in normalized):
        return "FAIL"
    if any(value == "HOLD" for value in normalized):
        return "HOLD"
    return "PASS"


def merge_pool_status(values: list[str]) -> str:
    normalized = [str(value or "").strip().upper() for value in values if str(value or "").strip()]
    if "PASS_WITH_MARKET_MAPPING_PENDING" in normalized:
        return "PASS_WITH_MARKET_MAPPING_PENDING"
    if "PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING" in normalized:
        return "PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING"
    if "MARKET_MAPPING_PENDING" in normalized:
        return "MARKET_MAPPING_PENDING"
    if "BLOCKED_BY_MARKET_SOURCE_EMPTY" in normalized:
        return "BLOCKED_BY_MARKET_SOURCE_EMPTY"
    if "PARTIAL_REAL_SAMPLE_ONLY" in normalized:
        return "PARTIAL_REAL_SAMPLE_ONLY"
    return aggregate_status(values)


def split_keywords(keywords: list[str]) -> tuple[str, str]:
    unique_keywords = [value for value in keywords if str(value or "").strip()]
    if not unique_keywords:
        return "", ""
    core = "; ".join(unique_keywords[:3])
    long_tail = "; ".join(unique_keywords[3:])
    return core, long_tail


def write_markdown(path: Path, content: str) -> None:
    ensure_within_repo(path, "markdown_path")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_batch_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise CandidatePoolError(f"Direction batch summary is missing: {path}", "DIRECTION_BATCH_SUMMARY_MISSING")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CandidatePoolError(f"Direction batch summary is not a JSON object: {path}", "DIRECTION_BATCH_SUMMARY_INVALID")
    return payload


def queue_index(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], dict[str, str]]:
    indexed: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (
            str(row.get("row_index", "")).strip(),
            str(row.get("关键词", "")).strip(),
            str(row.get("stage_code", "")).strip(),
        )
        indexed[key] = row
    return indexed


def first_matching_gate_row(rows: list[dict[str, str]], sample_id: str, sample_asin: str) -> dict[str, str]:
    for row in rows:
        if str(row.get("样品ID", "")).strip() == sample_id:
            return row
    for row in rows:
        if str(row.get("样品ASIN", "")).strip().upper() == sample_asin.upper():
            return row
    return {}


def build_source_rows(queue_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    indexed_queue = queue_index(queue_rows)
    source_rows: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, str]] = []

    for queue_row in queue_rows:
        stage_code = str(queue_row.get("stage_code", "")).strip()
        if stage_code != "STEP4_BENCHMARK_TRIGGER":
            continue
        keyword = str(queue_row.get("关键词", "")).strip()
        row_index = str(queue_row.get("row_index", "")).strip()
        if normalize_status(queue_row.get("status", "")) != "PASS":
            blocked_rows.append(
                {
                    "row_index": row_index,
                    "方向词": str(queue_row.get("方向词", "")).strip(),
                    "关键词": keyword,
                    "reason_code": str(queue_row.get("reason_code", "")).strip(),
                }
            )
            continue

        trigger_snapshot = parse_snapshot(queue_row.get("data_snapshot", ""))
        build_summary = trigger_snapshot.get("build_summary", {})
        if not isinstance(build_summary, dict) or str(build_summary.get("status", "")).strip().upper() != "PASS":
            blocked_rows.append(
                {
                    "row_index": row_index,
                    "方向词": str(queue_row.get("方向词", "")).strip(),
                    "关键词": keyword,
                    "reason_code": "STEP4_BUILD_SUMMARY_MISSING",
                }
            )
            continue

        benchmark_output_dir = repo_path(str(build_summary.get("output_dir", "")), "benchmark_output_dir")
        seed_path = ensure_within_repo(benchmark_output_dir / STEP4_SEED_FILE, "seed_path")
        gate_path = ensure_within_repo(benchmark_output_dir / STEP4_GATE_FILE, "gate_path")
        if not seed_path.exists() or not gate_path.exists():
            blocked_rows.append(
                {
                    "row_index": row_index,
                    "方向词": str(queue_row.get("方向词", "")).strip(),
                    "关键词": keyword,
                    "reason_code": "STEP4_OUTPUT_FILES_MISSING",
                }
            )
            continue

        seed_rows = load_dict_rows(seed_path)
        gate_rows = load_dict_rows(gate_path)
        if not seed_rows:
            blocked_rows.append(
                {
                    "row_index": row_index,
                    "方向词": str(queue_row.get("方向词", "")).strip(),
                    "关键词": keyword,
                    "reason_code": "STEP4_SEED_ROWS_EMPTY",
                }
            )
            continue

        step2_row = indexed_queue.get((row_index, keyword, "STEP2_KEYWORD_GATE"), {})
        step3_row = indexed_queue.get((row_index, keyword, "STEP3_MARKET_GATE"), {})
        step4_gate_row = indexed_queue.get((row_index, keyword, "STEP4_BENCHMARK_GATE"), {})
        step3_snapshot = parse_snapshot(step3_row.get("data_snapshot", ""))
        matched_step3 = step3_snapshot.get("matched_step3_gate_rows", [])
        market_gate_row = matched_step3[0] if isinstance(matched_step3, list) and matched_step3 else {}

        export_summary = trigger_snapshot.get("export_summary", {})
        source_stage = "STEP4_BENCHMARK"
        source_keyword = keyword
        direction_word = str(queue_row.get("方向词", "")).strip()
        site = str(market_gate_row.get("站点", "")).strip() or str(export_summary.get("站点", "")).strip()
        keyword_value_status = normalize_status(step2_row.get("status", "HOLD"))
        market_status = normalize_status(str(market_gate_row.get("整体状态", "")).strip() or step3_row.get("status", "HOLD"))

        for seed_row in seed_rows:
            gate_row = first_matching_gate_row(
                gate_rows,
                sample_id=str(seed_row.get("样品ID", "")).strip(),
                sample_asin=str(seed_row.get("样品ASIN", "")).strip(),
            )
            benchmark_status = normalize_status(str(gate_row.get("整体状态", "")).strip() or build_summary.get("gate_status", "HOLD"))
            ad_dependency_status = "HOLD"
            current_pool_status = aggregate_status([keyword_value_status, market_status, benchmark_status, ad_dependency_status])
            step3_batch = str(market_gate_row.get("下推批次号", "")).strip()
            step4_batch = str(gate_row.get("下推批次号", "")).strip() or str(build_summary.get("benchmark_run_summary", "")).strip()

            source_rows.append(
                {
                    "运行名称": str(seed_row.get("运行名称", "")).strip(),
                    "方向ID": str(seed_row.get("方向ID", "")).strip(),
                    "方向词": direction_word,
                    "来源关键词": source_keyword,
                    "站点": site,
                    "样品ID": str(seed_row.get("样品ID", "")).strip(),
                    "样品ASIN": str(seed_row.get("样品ASIN", "")).strip().upper(),
                    "样品标题": str(seed_row.get("样品标题", "")).strip(),
                    "品牌": str(seed_row.get("品牌", "")).strip(),
                    "市场路径": str(seed_row.get("市场路径", "")).strip() or str(export_summary.get("market_path", "")).strip(),
                    "候选市场名称": str(seed_row.get("候选市场名称", "")).strip() or str(export_summary.get("candidate_market_name", "")).strip(),
                    "样品价格": str(seed_row.get("价格", "")).strip(),
                    "评分": str(seed_row.get("评分", "")).strip(),
                    "评论数": str(seed_row.get("评论数", "")).strip(),
                    "去重组ID": str(seed_row.get("去重组ID", "")).strip(),
                    "近义合并组ID": merge_group_id(str(seed_row.get("样品标题", "")), str(seed_row.get("品牌", "")), str(seed_row.get("候选市场名称", ""))),
                    "样品来源阶段": source_stage,
                    "样品来源批次号": step4_batch,
                    "来源记录": join_unique(
                        [
                            f"DIRECTION:{direction_word}",
                            f"KEYWORD:{source_keyword}",
                            f"STEP2:{keyword_value_status}",
                            f"STEP3:{step3_batch}",
                            f"STEP4:{step4_batch}",
                        ]
                    ),
                    "市场下推状态": market_status,
                    "竞品下推状态": benchmark_status,
                    "关键词价值状态": keyword_value_status,
                    "广告依赖状态": ad_dependency_status,
                    "当前池状态": current_pool_status,
                    "备注": "",
                    "_market_avg_price": str(market_gate_row.get("平均价格", "")).strip(),
                    "_market_monthly_sales": str(market_gate_row.get("月总销量", "")).strip(),
                    "_market_new_product_ratio": str(market_gate_row.get("新品占比_pct", "")).strip(),
                    "_market_product_concentration": str(market_gate_row.get("商品集中度", "")).strip(),
                    "_market_brand_concentration": str(market_gate_row.get("品牌集中度", "")).strip(),
                    "_market_seller_concentration": str(market_gate_row.get("卖家集中度", "")).strip(),
                }
            )

    return source_rows, blocked_rows


def repo_path_if_present(raw_path: str | None, label: str) -> Path | None:
    if not str(raw_path or "").strip():
        return None
    return repo_path(raw_path, label)


def direct_artifact_mode_requested(args: argparse.Namespace) -> bool:
    return any(
        str(getattr(args, option, "") or "").strip()
        for option in (
            "step1_seed_csv",
            "step1_gate_csv",
            "step2_gate_csv",
            "step3_gate_csv",
            "step4_seed_csv",
            "step4_gate_csv",
        )
    )


def field_value(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def match_context_any(row: dict[str, Any], keys: tuple[str, ...], expected: str) -> bool:
    normalized_expected = str(expected or "").strip().casefold()
    if not normalized_expected:
        return True
    saw_value = False
    for key in keys:
        value = field_value(row, key)
        if not value:
            continue
        saw_value = True
        if value.casefold() == normalized_expected:
            return True
    return not saw_value


def context_matched_rows(rows: list[dict[str, str]], *, direction_id: str, keyword: str, site: str) -> list[dict[str, str]]:
    strict_matches: list[dict[str, str]] = []
    fallback_matches: list[dict[str, str]] = []
    for row in rows:
        if site and not match_context_any(row, (FIELD_SITE,), site):
            continue
        if keyword and not match_context_any(row, (FIELD_KEYWORD, FIELD_DIRECTION_WORD, FIELD_SOURCE_KEYWORD), keyword):
            continue
        if direction_id and match_context_any(row, (FIELD_DIRECTION_ID,), direction_id):
            strict_matches.append(row)
            continue
        if not direction_id:
            strict_matches.append(row)
            continue
        fallback_matches.append(row)
    return strict_matches or fallback_matches


def stage_status_from_gate_rows(rows: list[dict[str, str]], missing_default: str = "HOLD") -> str:
    statuses = [normalize_runtime_status(field_value(row, FIELD_OVERALL_STATUS), missing_default) for row in rows]
    if not statuses:
        return missing_default
    if any(status == "PASS" for status in statuses):
        return "PASS"
    if any(status == "HOLD" for status in statuses):
        return "HOLD"
    if any(status == "SOURCE_EMPTY" for status in statuses):
        return "SOURCE_EMPTY"
    if any(status == "FALLBACK_NEXT" for status in statuses):
        return "FALLBACK_NEXT"
    if any(status == "BLOCKED" for status in statuses):
        return "BLOCKED"
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    return missing_default


def resolve_purpose_meta(*, context_row_index: int, run_name: str, direction_id: str, keyword: str, site: str) -> dict[str, Any]:
    payload = resolve_route_decision(
        context_row_index=context_row_index,
        run_name=run_name,
        direction_id=direction_id,
        keyword=keyword,
        site=site,
    )
    purpose_type = str(payload.get("purpose_type", PRODUCT_IDEA_VALIDATION)).strip() or PRODUCT_IDEA_VALIDATION
    step3_policy = str(payload.get("step3_policy", "OPTIONAL")).strip() or "OPTIONAL"
    return {
        "purpose_type": purpose_type,
        "step3_policy": step3_policy,
        "step3_required": bool(payload.get("step3_required")),
        "step3_optional_enrichment": bool(payload.get("step3_optional_enrichment")),
    }


def market_mapping_pending_status(keyword_status: str, benchmark_status: str, source_stage: str) -> str:
    if benchmark_status == "PASS" and keyword_status == "PASS":
        return "PASS_WITH_MARKET_MAPPING_PENDING"
    if source_stage in {"STEP4_BENCHMARK", "STEP1_PRODUCT_ENTRY"} and benchmark_status in {"PASS", "HOLD", "FALLBACK_NEXT", "BLOCKED", "SOURCE_EMPTY"}:
        return "PRODUCT_FEASIBLE__MARKET_ABSTRACTION_PENDING"
    return "MARKET_MAPPING_PENDING"


def artifact_seed_path(seed_arg: str | None, gate_path: Path | None, default_file_name: str, label: str) -> Path | None:
    explicit_path = repo_path_if_present(seed_arg, label)
    if explicit_path is not None:
        return explicit_path
    if gate_path is None:
        return None
    return ensure_within_repo(gate_path.with_name(default_file_name), label)


def build_source_rows_from_direct_artifacts(
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    context = resolve_context_from_namespace(args, require_direction_id=False)
    purpose_meta = resolve_purpose_meta(
        context_row_index=context.context_row_index,
        run_name=context.run_name,
        direction_id=context.direction_id,
        keyword=context.keyword,
        site=context.site,
    )
    purpose_type = str(purpose_meta["purpose_type"])
    step3_required = bool(purpose_meta["step3_required"])
    step1_gate_path = repo_path_if_present(args.step1_gate_csv, "step1_gate_csv")
    step2_gate_path = repo_path_if_present(args.step2_gate_csv, "step2_gate_csv")
    step3_gate_path = repo_path_if_present(args.step3_gate_csv, "step3_gate_csv")
    step4_gate_path = repo_path_if_present(args.step4_gate_csv, "step4_gate_csv")
    step1_seed_path = artifact_seed_path(args.step1_seed_csv, step1_gate_path, STEP1_SEED_FILE, "step1_seed_csv")
    step4_seed_path = artifact_seed_path(args.step4_seed_csv, step4_gate_path, STEP4_SEED_FILE, "step4_seed_csv")

    if not any((step1_gate_path, step2_gate_path, step3_gate_path, step4_gate_path)):
        raise CandidatePoolError(
            "Direct artifact mode requires at least one step gate path.",
            "DIRECT_ARTIFACT_INPUTS_MISSING",
        )

    def load_rows_if_exists(path: Path | None) -> list[dict[str, str]]:
        if path is None or not path.exists():
            return []
        return load_dict_rows(path)

    step1_gate_rows_all = load_rows_if_exists(step1_gate_path)
    step2_gate_rows_all = load_rows_if_exists(step2_gate_path)
    step3_gate_rows_all = load_rows_if_exists(step3_gate_path)
    step4_gate_rows_all = load_rows_if_exists(step4_gate_path)
    step1_seed_rows_all = load_rows_if_exists(step1_seed_path)
    step4_seed_rows_all = load_rows_if_exists(step4_seed_path)

    context_kwargs = {
        "direction_id": context.direction_id,
        "keyword": context.keyword,
        "site": context.site,
    }
    step1_gate_rows = context_matched_rows(step1_gate_rows_all, **context_kwargs)
    step2_gate_rows = context_matched_rows(step2_gate_rows_all, **context_kwargs)
    step3_gate_rows = context_matched_rows(step3_gate_rows_all, **context_kwargs)
    step4_gate_rows = context_matched_rows(step4_gate_rows_all, **context_kwargs)
    step1_seed_rows = context_matched_rows(step1_seed_rows_all, **context_kwargs)
    step4_seed_rows = context_matched_rows(step4_seed_rows_all, **context_kwargs)

    keyword_status = stage_status_from_gate_rows(step2_gate_rows, "HOLD")
    product_status = stage_status_from_gate_rows(step1_gate_rows, "HOLD")
    benchmark_status = stage_status_from_gate_rows(
        step4_gate_rows,
        "FALLBACK_NEXT" if step1_gate_rows else "HOLD",
    )
    step3_context_missing = bool(step3_gate_path and not step3_gate_rows)
    market_status = stage_status_from_gate_rows(step3_gate_rows, "SOURCE_EMPTY" if step3_context_missing else "HOLD")

    blocked_rows: list[dict[str, str]] = []
    if step3_context_missing:
        blocked_rows.append(
            {
                "row_index": str(context.context_row_index),
                FIELD_DIRECTION_WORD: context.keyword,
                FIELD_KEYWORD: context.keyword,
                "reason_code": "STEP3_CONTEXT_ROWS_MISSING",
            }
        )

    source_rows: list[dict[str, Any]] = []
    used_product_fallback = False

    if step4_seed_rows and step4_gate_rows:
        for seed_row in step4_seed_rows:
            gate_row = first_matching_gate_row(
                step4_gate_rows,
                sample_id=field_value(seed_row, FIELD_SAMPLE_ID),
                sample_asin=field_value(seed_row, FIELD_SAMPLE_ASIN),
            )
            per_row_benchmark_status = normalize_runtime_status(
                field_value(gate_row, FIELD_OVERALL_STATUS) or benchmark_status,
                benchmark_status,
            )
            source_keyword = field_value(seed_row, FIELD_KEYWORD, FIELD_SOURCE_KEYWORD, FIELD_DIRECTION_WORD) or context.keyword
            candidate_market = field_value(seed_row, FIELD_CANDIDATE_MARKET) or context.keyword
            market_path = field_value(seed_row, FIELD_MARKET_PATH)
            current_pool_status = boundary_pool_status(
                keyword_status,
                market_status,
                per_row_benchmark_status,
                "STEP4_BENCHMARK",
                purpose_type=purpose_type,
                step3_required=step3_required,
            )
            source_rows.append(
                {
                    FIELD_RUN_NAME: field_value(seed_row, FIELD_RUN_NAME) or context.run_name,
                    FIELD_DIRECTION_ID: field_value(seed_row, FIELD_DIRECTION_ID) or context.direction_id,
                    FIELD_DIRECTION_WORD: context.keyword,
                    FIELD_SOURCE_KEYWORD: source_keyword,
                    FIELD_SITE: field_value(seed_row, FIELD_SITE) or context.site,
                    FIELD_SAMPLE_ID: field_value(seed_row, FIELD_SAMPLE_ID),
                    FIELD_SAMPLE_ASIN: field_value(seed_row, FIELD_SAMPLE_ASIN).upper(),
                    FIELD_SAMPLE_TITLE: field_value(seed_row, FIELD_SAMPLE_TITLE),
                    FIELD_BRAND: field_value(seed_row, FIELD_BRAND),
                    FIELD_MARKET_PATH: market_path,
                    FIELD_CANDIDATE_MARKET: candidate_market,
                    FIELD_SAMPLE_PRICE: field_value(seed_row, FIELD_SAMPLE_PRICE, FIELD_PRICE),
                    FIELD_RATING: field_value(seed_row, FIELD_RATING),
                    FIELD_REVIEWS: field_value(seed_row, FIELD_REVIEWS),
                    FIELD_DEDUPE_GROUP_ID: field_value(seed_row, FIELD_DEDUPE_GROUP_ID),
                    FIELD_MERGE_GROUP_ID: merge_group_id(
                        field_value(seed_row, FIELD_SAMPLE_TITLE),
                        field_value(seed_row, FIELD_BRAND),
                        candidate_market,
                    ),
                    FIELD_SOURCE_STAGE: "STEP4_BENCHMARK",
                    FIELD_SOURCE_BATCH: field_value(gate_row, FIELD_PUSH_BATCH),
                    FIELD_SOURCE_RECORD: join_unique(
                        [
                            f"DIRECTION:{context.keyword}",
                            f"KEYWORD:{source_keyword}",
                            f"STEP2:{keyword_status}",
                            f"STEP3:{market_status}",
                            f"STEP4:{per_row_benchmark_status}",
                        ]
                    ),
                    FIELD_MARKET_STATUS: market_status,
                    FIELD_BENCHMARK_STATUS: per_row_benchmark_status,
                    FIELD_KEYWORD_VALUE_STATUS: keyword_status,
                    FIELD_AD_DEPENDENCY_STATUS: "HOLD",
                    FIELD_POOL_STATUS: current_pool_status,
                    FIELD_NOTE: "",
                    "_market_avg_price": "",
                    "_market_monthly_sales": "",
                    "_market_new_product_ratio": "",
                    "_market_product_concentration": "",
                    "_market_brand_concentration": "",
                    "_market_seller_concentration": "",
                }
            )
    elif step1_seed_rows and step1_gate_rows and product_status in {"PASS", "HOLD"}:
        used_product_fallback = True
        effective_benchmark_status = benchmark_status if benchmark_status != "PASS" else "FALLBACK_NEXT"
        for seed_row in step1_seed_rows:
            gate_row = first_matching_gate_row(
                step1_gate_rows,
                sample_id=field_value(seed_row, FIELD_SAMPLE_ID),
                sample_asin=field_value(seed_row, FIELD_SAMPLE_ASIN),
            )
            source_keyword = field_value(seed_row, FIELD_KEYWORD, FIELD_SOURCE_KEYWORD, FIELD_DIRECTION_WORD) or field_value(
                gate_row,
                FIELD_BENCHMARK_QUERY,
                FIELD_KEYWORD,
            ) or context.keyword
            candidate_market = field_value(seed_row, FIELD_CANDIDATE_MARKET) or field_value(gate_row, FIELD_CANDIDATE_MARKET) or context.keyword
            market_path = field_value(seed_row, FIELD_MARKET_PATH) or field_value(gate_row, FIELD_MARKET_PATH)
            current_pool_status = boundary_pool_status(
                keyword_status,
                market_status,
                effective_benchmark_status,
                "STEP1_PRODUCT_ENTRY",
                purpose_type=purpose_type,
                step3_required=step3_required,
            )
            source_rows.append(
                {
                    FIELD_RUN_NAME: field_value(seed_row, FIELD_RUN_NAME) or context.run_name,
                    FIELD_DIRECTION_ID: field_value(seed_row, FIELD_DIRECTION_ID) or context.direction_id,
                    FIELD_DIRECTION_WORD: context.keyword,
                    FIELD_SOURCE_KEYWORD: source_keyword,
                    FIELD_SITE: field_value(seed_row, FIELD_SITE) or context.site,
                    FIELD_SAMPLE_ID: field_value(seed_row, FIELD_SAMPLE_ID),
                    FIELD_SAMPLE_ASIN: field_value(seed_row, FIELD_SAMPLE_ASIN).upper(),
                    FIELD_SAMPLE_TITLE: field_value(seed_row, FIELD_SAMPLE_TITLE),
                    FIELD_BRAND: field_value(seed_row, FIELD_BRAND),
                    FIELD_MARKET_PATH: market_path,
                    FIELD_CANDIDATE_MARKET: candidate_market,
                    FIELD_SAMPLE_PRICE: field_value(seed_row, FIELD_SAMPLE_PRICE, FIELD_PRICE),
                    FIELD_RATING: field_value(seed_row, FIELD_RATING),
                    FIELD_REVIEWS: field_value(seed_row, FIELD_REVIEWS),
                    FIELD_DEDUPE_GROUP_ID: field_value(seed_row, FIELD_DEDUPE_GROUP_ID),
                    FIELD_MERGE_GROUP_ID: merge_group_id(
                        field_value(seed_row, FIELD_SAMPLE_TITLE),
                        field_value(seed_row, FIELD_BRAND),
                        candidate_market,
                    ),
                    FIELD_SOURCE_STAGE: "STEP1_PRODUCT_ENTRY",
                    FIELD_SOURCE_BATCH: field_value(gate_row, FIELD_PUSH_BATCH),
                    FIELD_SOURCE_RECORD: join_unique(
                        [
                            f"DIRECTION:{context.keyword}",
                            f"KEYWORD:{source_keyword}",
                            f"STEP1:{product_status}",
                            f"STEP2:{keyword_status}",
                            f"STEP3:{market_status}",
                            f"STEP4:{effective_benchmark_status}",
                        ]
                    ),
                    FIELD_MARKET_STATUS: market_status,
                    FIELD_BENCHMARK_STATUS: effective_benchmark_status,
                    FIELD_KEYWORD_VALUE_STATUS: keyword_status,
                    FIELD_AD_DEPENDENCY_STATUS: "HOLD",
                    FIELD_POOL_STATUS: current_pool_status,
                    FIELD_NOTE: "",
                    "_market_avg_price": "",
                    "_market_monthly_sales": "",
                    "_market_new_product_ratio": "",
                    "_market_product_concentration": "",
                    "_market_brand_concentration": "",
                    "_market_seller_concentration": "",
                }
            )
    else:
        blocked_rows.append(
            {
                "row_index": str(context.context_row_index),
                FIELD_DIRECTION_WORD: context.keyword,
                FIELD_KEYWORD: context.keyword,
                "reason_code": "NO_STEP1_OR_STEP4_REAL_SAMPLE_SOURCE",
            }
        )

    summary_status = "PASS"
    summary_reason_code = "PASS"
    if not source_rows:
        summary_status = "HOLD"
        summary_reason_code = "NO_REAL_CANDIDATE_ROWS"
    elif not step3_required and purpose_type != MARKET_DISCOVERY and market_status in {"SOURCE_EMPTY", "HOLD", "BLOCKED", "FALLBACK_NEXT"}:
        summary_status = "HOLD"
        summary_reason_code = market_mapping_pending_status(
            keyword_status,
            benchmark_status,
            "STEP1_PRODUCT_ENTRY" if used_product_fallback else "STEP4_BENCHMARK",
        )
    elif market_status == "SOURCE_EMPTY":
        summary_status = "HOLD"
        summary_reason_code = "BLOCKED_BY_MARKET_SOURCE_EMPTY"
    elif used_product_fallback:
        summary_status = "HOLD"
        summary_reason_code = "PARTIAL_REAL_SAMPLE_ONLY"
    elif keyword_status in {"HOLD", "BLOCKED", "SOURCE_EMPTY"}:
        summary_status = "HOLD"
        summary_reason_code = "STEP2_HOLD__REAL_SAMPLES_CONTINUED"
    elif benchmark_status in {"HOLD", "SOURCE_EMPTY", "FALLBACK_NEXT", "BLOCKED"}:
        summary_status = "HOLD"
        summary_reason_code = f"STEP4_{benchmark_status}"

    return source_rows, blocked_rows, {
        "mode": "direct_artifacts",
        "summary_status": summary_status,
        "summary_reason_code": summary_reason_code,
        "step1_status": product_status,
        "step2_status": keyword_status,
        "step3_status": market_status,
        "step4_status": benchmark_status,
        "step1_seed_path": str(step1_seed_path or ""),
        "step1_gate_path": str(step1_gate_path or ""),
        "step2_gate_path": str(step2_gate_path or ""),
        "step3_gate_path": str(step3_gate_path or ""),
        "step4_seed_path": str(step4_seed_path or ""),
        "step4_gate_path": str(step4_gate_path or ""),
        "context_direction_id": context.direction_id,
        "context_keyword": context.keyword,
        "context_site": context.site,
        "purpose_type": purpose_type,
        "step3_policy": str(purpose_meta["step3_policy"]),
        "step3_required": step3_required,
    }


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise CandidatePoolError(f"JSON file is missing: {path}", "JSON_FILE_MISSING")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CandidatePoolError(f"JSON file is not an object: {path}", "JSON_FILE_INVALID")
    return payload


def boundary_pool_status(
    keyword_status: str,
    market_status: str,
    benchmark_status: str,
    source_stage: str,
    *,
    purpose_type: str = PRODUCT_IDEA_VALIDATION,
    step3_required: bool = False,
) -> str:
    if not step3_required and purpose_type != MARKET_DISCOVERY and market_status in {"SOURCE_EMPTY", "HOLD", "BLOCKED", "FALLBACK_NEXT"}:
        return market_mapping_pending_status(keyword_status, benchmark_status, source_stage)
    if market_status == "SOURCE_EMPTY":
        return "BLOCKED_BY_MARKET_SOURCE_EMPTY"
    if source_stage == "STEP1_PRODUCT_ENTRY" and benchmark_status in {"SOURCE_EMPTY", "FALLBACK_NEXT", "BLOCKED", "HOLD"}:
        return "PARTIAL_REAL_SAMPLE_ONLY"
    aggregate_inputs = [
        keyword_status if keyword_status in {"PASS", "FAIL", "HOLD"} else "HOLD",
        market_status if market_status in {"PASS", "FAIL", "HOLD"} else "HOLD",
        benchmark_status if benchmark_status in {"PASS", "FAIL", "HOLD"} else "HOLD",
        "HOLD",
    ]
    return aggregate_status(aggregate_inputs)


def first_existing_path(*candidates: Path | None) -> Path | None:
    for candidate in candidates:
        if candidate is not None and candidate.exists():
            return candidate
    return None


def build_source_rows_from_nightly_state(nightly_state_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    nightly_state = load_json_object(nightly_state_path)
    steps = nightly_state.get("steps", {})
    if not isinstance(steps, dict):
        raise CandidatePoolError("Nightly state is missing a valid `steps` object.", "NIGHTLY_STATE_STEPS_INVALID")

    context = nightly_state.get("context", {})
    if not isinstance(context, dict):
        context = {}

    output_dir = repo_path(str(nightly_state.get("output_dir", "")), "nightly_output_dir")
    keyword_step = steps.get("step2_keyword", {}) if isinstance(steps.get("step2_keyword", {}), dict) else {}
    market_step = steps.get("step3_market", {}) if isinstance(steps.get("step3_market", {}), dict) else {}
    benchmark_step = steps.get("step4_benchmark", {}) if isinstance(steps.get("step4_benchmark", {}), dict) else {}
    product_step = steps.get("step1_product", {}) if isinstance(steps.get("step1_product", {}), dict) else {}

    keyword_status = normalize_runtime_status(str(keyword_step.get("status", "HOLD")), "HOLD")
    market_status = normalize_runtime_status(str(market_step.get("status", "HOLD")), "HOLD")
    benchmark_status = normalize_runtime_status(str(benchmark_step.get("status", "FALLBACK_NEXT")), "FALLBACK_NEXT")
    product_status = normalize_runtime_status(str(product_step.get("status", "HOLD")), "HOLD")

    step4_seed_path = first_existing_path(
        repo_path_if_present(benchmark_step.get("seed_csv_path"), "step4_seed_csv"),
        ensure_within_repo(output_dir / STEP4_SEED_FILE, "step4_seed_path"),
    )
    step4_gate_path = first_existing_path(
        repo_path_if_present(benchmark_step.get("gate_csv_path"), "step4_gate_csv"),
        ensure_within_repo(output_dir / STEP4_GATE_FILE, "step4_gate_path"),
    )
    step1_seed_path = first_existing_path(
        repo_path_if_present(product_step.get("seed_csv_path"), "step1_seed_csv"),
        ensure_within_repo(output_dir / STEP1_SEED_FILE, "step1_seed_path"),
    )
    step1_gate_path = first_existing_path(
        repo_path_if_present(product_step.get("gate_csv_path"), "step1_gate_csv"),
        ensure_within_repo(output_dir / STEP1_GATE_FILE, "step1_gate_path"),
    )

    direction_word = str(context.get("keyword", "") or context.get("方向词", "")).strip()
    run_name = str(context.get("run_name", "") or context.get("运行名称", "")).strip()
    direction_id = str(context.get("direction_id", "") or context.get("方向ID", "")).strip()
    site = str(context.get("site", "") or context.get("站点", "")).strip()
    context_row_index = int(context.get("context_row_index", 1) or 1)
    purpose_meta = resolve_purpose_meta(
        context_row_index=context_row_index,
        run_name=run_name,
        direction_id=direction_id,
        keyword=direction_word,
        site=site,
    )
    purpose_type = str(purpose_meta["purpose_type"])
    step3_required = bool(purpose_meta["step3_required"])
    source_rows: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, str]] = []
    used_product_fallback = False

    if step4_seed_path and step4_gate_path:
        seed_rows = load_dict_rows(step4_seed_path)
        gate_rows = load_dict_rows(step4_gate_path)
        for seed_row in seed_rows:
            gate_row = first_matching_gate_row(
                gate_rows,
                sample_id=str(seed_row.get("样品ID", "")).strip(),
                sample_asin=str(seed_row.get("样品ASIN", "")).strip(),
            )
            per_row_benchmark_status = normalize_runtime_status(
                str(gate_row.get("整体状态", "")).strip() or benchmark_status,
                benchmark_status,
            )
            current_pool_status = boundary_pool_status(
                keyword_status,
                market_status,
                per_row_benchmark_status,
                "STEP4_BENCHMARK",
                purpose_type=purpose_type,
                step3_required=step3_required,
            )
            source_rows.append(
                {
                    "运行名称": str(seed_row.get("运行名称", "")).strip() or run_name,
                    "方向ID": str(seed_row.get("方向ID", "")).strip() or direction_id,
                    "方向词": direction_word,
                    "来源关键词": str(seed_row.get("关键词", "")).strip() or direction_word,
                    "站点": site,
                    "样品ID": str(seed_row.get("样品ID", "")).strip(),
                    "样品ASIN": str(seed_row.get("样品ASIN", "")).strip().upper(),
                    "样品标题": str(seed_row.get("样品标题", "")).strip(),
                    "品牌": str(seed_row.get("品牌", "")).strip(),
                    "市场路径": str(seed_row.get("市场路径", "")).strip(),
                    "候选市场名称": str(seed_row.get("候选市场名称", "")).strip() or direction_word,
                    "样品价格": str(seed_row.get("价格", "")).strip(),
                    "评分": str(seed_row.get("评分", "")).strip(),
                    "评论数": str(seed_row.get("评论数", "")).strip(),
                    "去重组ID": str(seed_row.get("去重组ID", "")).strip(),
                    "近义合并组ID": merge_group_id(str(seed_row.get("样品标题", "")), str(seed_row.get("品牌", "")), str(seed_row.get("候选市场名称", ""))),
                    "样品来源阶段": "STEP4_BENCHMARK",
                    "样品来源批次号": str(gate_row.get("下推批次号", "")).strip() or str(benchmark_step.get("batch_id", "")).strip(),
                    "来源记录": join_unique(
                        [
                            f"DIRECTION:{direction_word}",
                            f"KEYWORD:{str(seed_row.get('关键词', '')).strip() or direction_word}",
                            f"STEP2:{keyword_status}",
                            f"STEP3:{market_status}",
                            f"STEP4:{per_row_benchmark_status}",
                        ]
                    ),
                    "市场下推状态": market_status,
                    "竞品下推状态": per_row_benchmark_status,
                    "关键词价值状态": keyword_status,
                    "广告依赖状态": "HOLD",
                    "当前池状态": current_pool_status,
                    "备注": "",
                    "_market_avg_price": "",
                    "_market_monthly_sales": "",
                    "_market_new_product_ratio": "",
                    "_market_product_concentration": "",
                    "_market_brand_concentration": "",
                    "_market_seller_concentration": "",
                }
            )
    elif step1_seed_path and step1_gate_path and product_status in {"PASS", "HOLD"}:
        used_product_fallback = True
        seed_rows = load_dict_rows(step1_seed_path)
        gate_rows = load_dict_rows(step1_gate_path)
        effective_benchmark_status = benchmark_status if benchmark_status != "PASS" else "FALLBACK_NEXT"
        for seed_row in seed_rows:
            gate_row = first_matching_gate_row(
                gate_rows,
                sample_id=str(seed_row.get("样品ID", "")).strip(),
                sample_asin=str(seed_row.get("样品ASIN", "")).strip(),
            )
            current_pool_status = boundary_pool_status(
                keyword_status,
                market_status,
                effective_benchmark_status,
                "STEP1_PRODUCT_ENTRY",
                purpose_type=purpose_type,
                step3_required=step3_required,
            )
            source_rows.append(
                {
                    "运行名称": str(seed_row.get("运行名称", "")).strip() or run_name,
                    "方向ID": str(seed_row.get("方向ID", "")).strip() or direction_id,
                    "方向词": direction_word,
                    "来源关键词": str(seed_row.get("关键词", "")).strip() or direction_word,
                    "站点": site,
                    "样品ID": str(seed_row.get("样品ID", "")).strip(),
                    "样品ASIN": str(seed_row.get("样品ASIN", "")).strip().upper(),
                    "样品标题": str(seed_row.get("样品标题", "")).strip(),
                    "品牌": str(seed_row.get("品牌", "")).strip(),
                    "市场路径": str(seed_row.get("市场路径", "")).strip(),
                    "候选市场名称": str(seed_row.get("候选市场名称", "")).strip() or direction_word,
                    "样品价格": str(seed_row.get("价格", "")).strip(),
                    "评分": str(seed_row.get("评分", "")).strip(),
                    "评论数": str(seed_row.get("评论数", "")).strip(),
                    "去重组ID": str(seed_row.get("去重组ID", "")).strip(),
                    "近义合并组ID": merge_group_id(str(seed_row.get("样品标题", "")), str(seed_row.get("品牌", "")), str(seed_row.get("候选市场名称", ""))),
                    "样品来源阶段": "STEP1_PRODUCT_ENTRY",
                    "样品来源批次号": str(gate_row.get("下推批次号", "")).strip() or str(product_step.get("batch_id", "")).strip(),
                    "来源记录": join_unique(
                        [
                            f"DIRECTION:{direction_word}",
                            f"KEYWORD:{str(seed_row.get('关键词', '')).strip() or direction_word}",
                            f"STEP1:{product_status}",
                            f"STEP2:{keyword_status}",
                            f"STEP3:{market_status}",
                            f"STEP4:{effective_benchmark_status}",
                        ]
                    ),
                    "市场下推状态": market_status,
                    "竞品下推状态": effective_benchmark_status,
                    "关键词价值状态": keyword_status,
                    "广告依赖状态": "HOLD",
                    "当前池状态": current_pool_status,
                    "备注": "",
                    "_market_avg_price": "",
                    "_market_monthly_sales": "",
                    "_market_new_product_ratio": "",
                    "_market_product_concentration": "",
                    "_market_brand_concentration": "",
                    "_market_seller_concentration": "",
                }
            )
    else:
        blocked_rows.append(
            {
                "row_index": str(context.get("context_row_index", "")).strip(),
                "方向词": direction_word,
                "关键词": direction_word,
                "reason_code": "NO_STEP1_OR_STEP4_REAL_SAMPLE_SOURCE",
            }
        )

    summary_status = "PASS"
    summary_reason_code = "PASS"
    if not source_rows:
        summary_status = "HOLD"
        summary_reason_code = "NO_REAL_CANDIDATE_ROWS"
    elif not step3_required and purpose_type != MARKET_DISCOVERY and market_status in {"SOURCE_EMPTY", "HOLD", "BLOCKED", "FALLBACK_NEXT"}:
        summary_status = "HOLD"
        summary_reason_code = market_mapping_pending_status(
            keyword_status,
            benchmark_status,
            "STEP1_PRODUCT_ENTRY" if used_product_fallback else "STEP4_BENCHMARK",
        )
    elif market_status == "SOURCE_EMPTY":
        summary_status = "HOLD"
        summary_reason_code = "BLOCKED_BY_MARKET_SOURCE_EMPTY"
    elif used_product_fallback:
        summary_status = "HOLD"
        summary_reason_code = "PARTIAL_REAL_SAMPLE_ONLY"
    elif keyword_status in {"HOLD", "BLOCKED"}:
        summary_status = "HOLD"
        summary_reason_code = "STEP2_HOLD__REAL_SAMPLES_CONTINUED"
    elif benchmark_status in {"HOLD", "SOURCE_EMPTY", "FALLBACK_NEXT", "BLOCKED"}:
        summary_status = "HOLD"
        summary_reason_code = f"STEP4_{benchmark_status}"

    return source_rows, blocked_rows, {
        "mode": "nightly_state",
        "nightly_state_path": str(nightly_state_path),
        "step1_status": product_status,
        "step2_status": keyword_status,
        "step3_status": market_status,
        "step4_status": benchmark_status,
        "purpose_type": purpose_type,
        "step3_policy": str(purpose_meta["step3_policy"]),
        "step3_required": step3_required,
        "summary_status": summary_status,
        "summary_reason_code": summary_reason_code,
    }


def merge_source_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in source_rows:
        grouped[str(row.get("样品ASIN", "")).strip().upper()].append(row)

    merged_rows: list[dict[str, Any]] = []
    for sample_asin, rows in grouped.items():
        representative = sorted(rows, key=candidate_score, reverse=True)[0]
        direction_ids = [str(row.get("方向ID", "")).strip() for row in rows]
        direction_words = [str(row.get("方向词", "")).strip() for row in rows]
        source_keywords = [str(row.get("来源关键词", "")).strip() for row in rows]
        sample_ids = [str(row.get("样品ID", "")).strip() for row in rows]
        source_records = [str(row.get("来源记录", "")).strip() for row in rows]
        core_keywords, long_tail_keywords = split_keywords(sorted({value for value in source_keywords if value}))
        merged_rows.append(
            {
                "运行名称": join_unique([str(row.get("运行名称", "")).strip() for row in rows]),
                "方向ID": join_unique(direction_ids),
                "方向词": join_unique(direction_words),
                "站点": str(representative.get("站点", "")).strip(),
                "样品ID": str(representative.get("样品ID", "")).strip(),
                "样品ASIN": sample_asin,
                "样品标题": str(representative.get("样品标题", "")).strip(),
                "品牌": str(representative.get("品牌", "")).strip(),
                "市场路径": str(representative.get("市场路径", "")).strip(),
                "候选市场名称": str(representative.get("候选市场名称", "")).strip(),
                "核心关键词": core_keywords,
                "长尾关键词": long_tail_keywords,
                "平均价格": str(representative.get("_market_avg_price", "")).strip(),
                "月总销量": str(representative.get("_market_monthly_sales", "")).strip(),
                "新品占比_pct": str(representative.get("_market_new_product_ratio", "")).strip(),
                "商品集中度": str(representative.get("_market_product_concentration", "")).strip(),
                "品牌集中度": str(representative.get("_market_brand_concentration", "")).strip(),
                "卖家集中度": str(representative.get("_market_seller_concentration", "")).strip(),
                "自然流量占比_pct": "",
                "广告流量占比_pct": "",
                "推荐流量占比_pct": "",
                "建议竞价中位数": "",
                "关键词价值状态": aggregate_status([str(row.get("关键词价值状态", "")).strip() for row in rows]),
                "广告依赖状态": aggregate_status([str(row.get("广告依赖状态", "")).strip() for row in rows]),
                "当前下推状态": merge_pool_status([str(row.get("当前池状态", "")).strip() for row in rows]),
                "合规": "",
                "改良点": "",
                "最终解释": "",
                "利润核价": "",
                "备注": "",
                "_source_sample_ids": join_unique(sample_ids),
                "_source_records": join_unique(source_records),
                "_merge_group_id": str(representative.get("近义合并组ID", "")).strip(),
                "_dedupe_group_ids": join_unique([str(row.get("去重组ID", "")).strip() for row in rows]),
            }
        )

    merged_rows.sort(
        key=lambda row: (
            safe_float(row.get("月总销量")) or 0.0,
            safe_float(row.get("平均价格")) or 0.0,
            row.get("样品ASIN", ""),
        ),
        reverse=True,
    )
    return merged_rows


def markdown_summary(summary: dict[str, Any], rows_60: list[dict[str, Any]]) -> str:
    mode = str(summary.get("mode", "direction_batch")).strip() or "direction_batch"
    input_lines = [f"- mode: `{mode}`"]
    if mode == "direct_artifacts":
        input_lines.extend(
            [
                f"- step1_gate_path: `{summary.get('step1_gate_path', '')}`",
                f"- step2_gate_path: `{summary.get('step2_gate_path', '')}`",
                f"- step3_gate_path: `{summary.get('step3_gate_path', '')}`",
                f"- step4_gate_path: `{summary.get('step4_gate_path', '')}`",
            ]
        )
    elif mode == "nightly_state":
        input_lines.append(f"- nightly_state_path: `{summary.get('nightly_state_path', '')}`")
    else:
        input_lines.append(f"- source_queue_path: `{summary.get('queue_path', '')}`")
    lines = [
        "# 60 候选样品池",
        "",
        f"- batch_id: `{summary['batch_id']}`",
        f"- status: `{summary['status']}`",
        f"- reason_code: `{summary['reason_code']}`",
        f"- purpose_type: `{summary.get('purpose_type', '')}`",
        f"- step3_policy: `{summary.get('step3_policy', '')}`",
        f"- step3_required: `{summary.get('step3_required', False)}`",
        f"- intermediate_rows: `{summary['intermediate_row_count']}`",
        f"- final_rows: `{summary['final_row_count']}`",
        f"- contributing_directions: `{summary['contributing_direction_count']}`",
        "",
        "## Upstream",
        "",
        *input_lines,
        f"- direction_batch_status: `{summary['direction_batch_status']}`",
        f"- direction_batch_reason: `{summary['direction_batch_reason']}`",
        "",
        "## Candidate Pool",
        "",
        "| 样品ID | 样品ASIN | 方向词 | 核心关键词 | 候选市场名称 | 当前下推状态 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows_60:
        title = str(row.get("样品标题", "")).strip()
        truncated_title = title if len(title) <= 72 else title[:69] + "..."
        lines.append(
            f"| {row['样品ID']} | {row['样品ASIN']} | {row['方向词']} | {row['核心关键词']} | {row['候选市场名称']} | {row['当前下推状态']} |"
        )
        lines.append(f"|  |  |  |  | `{truncated_title}` |  |")
    if not rows_60:
        lines.append("| - | - | - | - | - | - |")

    blocked = summary.get("blocked_rows", [])
    if blocked:
        lines.extend(
            [
                "",
                "## Blocked Rows",
                "",
                "| row_index | 方向词 | 关键词 | reason_code |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in blocked:
            lines.append(
                f"| {item['row_index']} | {item['方向词']} | {item['关键词']} | {item['reason_code']} |"
            )

    lines.extend(
        [
            "",
            "## Manual Fields",
            "",
            "- `合规` 保持留空",
            "- `改良点` 保持留空",
            "- `最终解释` 保持留空",
            "- `利润核价` 保持留空",
            "- `备注` 在本轮保持留空",
        ]
    )
    return "\n".join(lines) + "\n"


def persist_logs(log_dir: Path, summary: dict[str, Any]) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(log_dir / LATEST_RUN_FILE, summary)
    append_jsonl(log_dir / RUN_HISTORY_FILE, summary)
    if summary["status"] != "PASS":
        append_jsonl(log_dir / RUN_FAILURE_FILE, summary)


def main() -> int:
    args = parse_args()
    batch_id = str(args.batch_id or f"CANDIDATE_POOL_{timestamp_slug()}")
    log_dir = repo_path(args.log_dir, "log_dir")
    output_dir = repo_path(args.output_dir, "output_dir") if args.output_dir else default_output_dir(batch_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_summary_path = ""
    queue_path = ""
    direction_batch_summary: dict[str, Any] = {"status": "", "reason_code": ""}
    nightly_meta: dict[str, Any] = {}

    if direct_artifact_mode_requested(args):
        source_rows, blocked_rows, nightly_meta = build_source_rows_from_direct_artifacts(args)
    elif args.nightly_state:
        nightly_state_path = repo_path(args.nightly_state, "nightly_state")
        source_rows, blocked_rows, nightly_meta = build_source_rows_from_nightly_state(nightly_state_path)
    else:
        batch_summary_path = str(repo_path(args.batch_summary, "batch_summary"))
        direction_batch_summary = load_batch_summary(Path(batch_summary_path))
        queue_path = str(repo_path(args.queue_csv, "queue_csv")) if args.queue_csv else str(repo_path(direction_batch_summary.get("queue_path", ""), "queue_path"))
        queue_rows = load_dict_rows(Path(queue_path))
        source_rows, blocked_rows = build_source_rows(queue_rows)
    rows_60 = merge_source_rows(source_rows)

    intermediate_path = ensure_within_repo(output_dir / INTERMEDIATE_FILE, "intermediate_path")
    final_path = ensure_within_repo(output_dir / FINAL_FILE, "final_path")
    final_md_path = ensure_within_repo(output_dir / FINAL_MD, "final_md_path")
    summary_path = ensure_within_repo(output_dir / SUMMARY_JSON, "summary_path")

    write_csv_atomic(
        intermediate_path,
        INTERMEDIATE_FIELDS,
        [[str(row.get(field, "")).strip() for field in INTERMEDIATE_FIELDS] for row in source_rows],
    )
    final_field_order = load_field_order(FINAL_FILE)
    write_csv_atomic(
        final_path,
        final_field_order,
        [[str(row.get(field, "")).strip() for field in final_field_order] for row in rows_60],
    )

    if direct_artifact_mode_requested(args) or args.nightly_state:
        status = str(nightly_meta.get("summary_status", "HOLD")).strip() or "HOLD"
        reason_code = str(nightly_meta.get("summary_reason_code", "NO_REAL_CANDIDATE_ROWS")).strip() or "NO_REAL_CANDIDATE_ROWS"
    else:
        status = "PASS"
        reason_code = "PASS"
        if direction_batch_summary.get("status") != "PASS":
            status = "HOLD"
            upstream_reason = str(direction_batch_summary.get("reason_code", "DIRECTION_BATCH_NOT_PASS")).strip()
            if upstream_reason.startswith("BLOCKED_BY_UPSTREAM_CHAIN__"):
                reason_code = upstream_reason
            else:
                reason_code = f"BLOCKED_BY_UPSTREAM_CHAIN__{upstream_reason}"
        if not rows_60:
            status = "HOLD"
            reason_code = "NO_REAL_CANDIDATE_ROWS"

    summary = {
        "timestamp": iso_now(),
        "module": "candidate_pool_build",
        "batch_id": batch_id,
        "status": status,
        "reason_code": reason_code,
        "batch_summary_path": str(batch_summary_path),
        "queue_path": str(queue_path),
        "nightly_state_path": str(nightly_meta.get("nightly_state_path", "")),
        "mode": str(nightly_meta.get("mode", "direction_batch")),
        "step1_seed_path": str(nightly_meta.get("step1_seed_path", "")).strip(),
        "step1_gate_path": str(nightly_meta.get("step1_gate_path", "")).strip(),
        "step2_gate_path": str(nightly_meta.get("step2_gate_path", "")).strip(),
        "step3_gate_path": str(nightly_meta.get("step3_gate_path", "")).strip(),
        "step4_seed_path": str(nightly_meta.get("step4_seed_path", "")).strip(),
        "step4_gate_path": str(nightly_meta.get("step4_gate_path", "")).strip(),
        "context_direction_id": str(nightly_meta.get("context_direction_id", "")).strip(),
        "context_keyword": str(nightly_meta.get("context_keyword", "")).strip(),
        "context_site": str(nightly_meta.get("context_site", "")).strip(),
        "purpose_type": str(nightly_meta.get("purpose_type", "")).strip(),
        "step3_policy": str(nightly_meta.get("step3_policy", "")).strip(),
        "step3_required": bool(nightly_meta.get("step3_required")),
        "direction_batch_status": str(direction_batch_summary.get("status", "")).strip(),
        "direction_batch_reason": str(direction_batch_summary.get("reason_code", "")).strip(),
        "step1_status": str(nightly_meta.get("step1_status", "")).strip(),
        "step2_status": str(nightly_meta.get("step2_status", "")).strip(),
        "step3_status": str(nightly_meta.get("step3_status", "")).strip(),
        "step4_status": str(nightly_meta.get("step4_status", "")).strip(),
        "intermediate_path": str(intermediate_path),
        "final_path": str(final_path),
        "final_md_path": str(final_md_path),
        "intermediate_row_count": len(source_rows),
        "final_row_count": len(rows_60),
        "contributing_direction_count": len({str(row.get("方向词", "")).strip() for row in rows_60 if str(row.get("方向词", "")).strip()}),
        "blocked_rows": blocked_rows,
    }

    write_json_atomic(summary_path, summary)
    write_markdown(final_md_path, markdown_summary(summary, rows_60))
    persist_logs(log_dir, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
