from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from keyword_chain_common import (
    OUTPUTS_ROOT,
    ROOT,
    ensure_within_repo,
    iso_now,
    load_csv_rows,
    timestamp_slug,
    write_csv_atomic,
    write_json_atomic,
)


DEFAULT_LOG_DIR = ROOT / "logs" / "sif_enrichment"
STANDARD_90_PATH = ROOT / "templates" / "selection_canonical_standards" / "90_下推参数表.csv"
STANDARD_99_PATH = ROOT / "templates" / "selection_canonical_standards" / "99_字段数据标准总表.csv"

FILE_50 = "50_SIF流量结构补强.csv"
FILE_51 = "51_SIF关键词价值补强.csv"
FILE_52 = "52_SIF广告结构补强.csv"
FILE_53 = "53_SIF补强下推结果.csv"
FILE_61 = "61_待供应链核利清单.csv"
FILE_61_MD = "61_待供应链核利清单.md"
FILE_SUMMARY_JSON = "sif_enrichment_daytime_pack_summary.json"

RUN_LATEST = "latest_run.json"
RUN_HISTORY = "sif_enrichment_runs.jsonl"
RUN_FAILURES = "sif_enrichment_failures.jsonl"


class SIFEnrichmentError(RuntimeError):
    def __init__(self, message: str, reason_code: str = "SIF_ENRICHMENT_ERROR") -> None:
        super().__init__(message)
        self.reason_code = reason_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Align structured SIF outputs onto the candidate pool and build the fail-closed daytime package."
    )
    parser.add_argument("--candidate-pool-csv", default=None)
    parser.add_argument("--candidate-pool-summary", default=None)
    parser.add_argument("--detail-csv", default=None)
    parser.add_argument("--detail-json", default=None)
    parser.add_argument("--search-51-csv", default=None)
    parser.add_argument("--search-52-csv", default=None)
    parser.add_argument("--search-json", default=None)
    parser.add_argument("--queue-csv", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--batch-id", default=None)
    return parser.parse_args()


def repo_path(raw_path: str | None, label: str) -> Path:
    if not raw_path:
        raise SIFEnrichmentError(f"Missing path for {label}.", "PATH_MISSING")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return ensure_within_repo(path, label)


def latest_path(pattern: str, label: str, exclude_root: Path | None = None) -> Path:
    matches: list[Path] = []
    for path in ROOT.glob(pattern):
        resolved = ensure_within_repo(path, label)
        if exclude_root is not None and resolved.is_relative_to(exclude_root.resolve()):
            continue
        matches.append(resolved)
    matches.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    if not matches:
        raise SIFEnrichmentError(f"No repo-local file matched {pattern!r} for {label}.", "LATEST_FILE_MISSING")
    return matches[0]


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
    fields = [row["field_name"] for row in rows if row["file_name"] == file_name]
    if not fields:
        raise SIFEnrichmentError(f"No field order found in 99 master for {file_name}.", "STANDARD_99_FILE_MISSING")
    return fields


def load_step_rules(step_code: str) -> list[dict[str, str]]:
    rows = list(csv.DictReader(STANDARD_90_PATH.read_text(encoding="utf-8-sig").splitlines()))
    filtered = [row for row in rows if row.get("step_code") == step_code and row.get("enabled") == "TRUE"]
    filtered.sort(key=lambda row: int(row.get("tie_breaker_rank") or 999))
    return filtered


def normalize_status(value: str | None, default: str = "HOLD") -> str:
    text = str(value or "").strip().upper()
    if text in {"PASS", "FAIL", "HOLD"}:
        return text
    if text == "BLOCKED":
        return "HOLD"
    return default


def split_multi(value: str | None) -> list[str]:
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def join_unique(values: list[str]) -> str:
    ordered: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in ordered:
            ordered.append(text)
    return "; ".join(ordered)


def default_output_dir(batch_id: str) -> Path:
    return ensure_within_repo(OUTPUTS_ROOT / batch_id / "02_generated_outputs", "output_dir")


def index_by_sample(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        sample_id = str(row.get("样品ID", "")).strip()
        asin = str(row.get("样品ASIN", "")).strip().upper()
        if sample_id and sample_id not in indexed:
            indexed[sample_id] = row
        if asin and asin not in indexed:
            indexed[asin] = row
    return indexed


def first_match(candidate_row: dict[str, str], indexed_rows: dict[str, dict[str, str]]) -> dict[str, str]:
    keys = [
        str(candidate_row.get("样品ID", "")).strip(),
        str(candidate_row.get("样品ASIN", "")).strip().upper(),
    ]
    for key in keys:
        if key and key in indexed_rows:
            return indexed_rows[key]
    return {}


def matched_summary(summary_payload: dict[str, Any], candidate_row: dict[str, str]) -> bool:
    context = summary_payload.get("context", {})
    if not isinstance(context, dict):
        return False
    sample_id = str(candidate_row.get("样品ID", "")).strip()
    asin = str(candidate_row.get("样品ASIN", "")).strip().upper()
    return (
        str(context.get("sample_id", "")).strip() == sample_id
        or str(context.get("sample_asin", "")).strip().upper() == asin
    )


def candidate_keyword(candidate_row: dict[str, str]) -> str:
    keywords = split_multi(candidate_row.get("核心关键词", ""))
    if keywords:
        return keywords[0]
    direction_words = split_multi(candidate_row.get("方向词", ""))
    if direction_words:
        return direction_words[0]
    return ""


def aligned_50_row(candidate_row: dict[str, str], source_row: dict[str, str] | None) -> dict[str, str]:
    base = {
        "运行名称": candidate_row.get("运行名称", "").strip(),
        "方向ID": candidate_row.get("方向ID", "").strip(),
        "关键词": candidate_keyword(candidate_row),
        "样品ID": candidate_row.get("样品ID", "").strip(),
        "样品ASIN": candidate_row.get("样品ASIN", "").strip().upper(),
        "主流量词列表": "",
        "自然流量占比_pct": "",
        "广告流量占比_pct": "",
        "推荐流量占比_pct": "",
        "Deal流量占比_pct": "",
        "变体主推款": "",
        "变体流量分布摘要": "",
        "核心流量结构状态": "HOLD",
        "抓取时间": iso_now(),
        "来源模块": "SIF_查流量结构/反查流量词",
    }
    if source_row:
        for field in base:
            if field in source_row and str(source_row.get(field, "")).strip():
                base[field] = str(source_row.get(field, "")).strip()
        base["运行名称"] = candidate_row.get("运行名称", "").strip()
        base["方向ID"] = candidate_row.get("方向ID", "").strip()
        base["关键词"] = candidate_keyword(candidate_row)
        base["样品ID"] = candidate_row.get("样品ID", "").strip()
        base["样品ASIN"] = candidate_row.get("样品ASIN", "").strip().upper()
    return base


def aligned_51_row(candidate_row: dict[str, str], source_row: dict[str, str] | None) -> dict[str, str]:
    base = {
        "运行名称": candidate_row.get("运行名称", "").strip(),
        "方向ID": candidate_row.get("方向ID", "").strip(),
        "关键词": candidate_keyword(candidate_row),
        "样品ID": candidate_row.get("样品ID", "").strip(),
        "样品ASIN": candidate_row.get("样品ASIN", "").strip().upper(),
        "核心关键词": candidate_row.get("核心关键词", "").strip(),
        "长尾关键词": candidate_row.get("长尾关键词", "").strip(),
        "关键词数量": "",
        "高价值关键词数": "",
        "建议竞价中位数": "",
        "高竞价关键词数": "",
        "关键词价值状态": "HOLD",
        "抓取时间": iso_now(),
        "来源模块": "SIF_选词/查竞价",
    }
    if source_row:
        for field in base:
            if field in source_row and str(source_row.get(field, "")).strip():
                base[field] = str(source_row.get(field, "")).strip()
        base["运行名称"] = candidate_row.get("运行名称", "").strip()
        base["方向ID"] = candidate_row.get("方向ID", "").strip()
        base["关键词"] = candidate_keyword(candidate_row)
        base["样品ID"] = candidate_row.get("样品ID", "").strip()
        base["样品ASIN"] = candidate_row.get("样品ASIN", "").strip().upper()
    return base


def aligned_52_row(candidate_row: dict[str, str], source_row: dict[str, str] | None) -> dict[str, str]:
    base = {
        "运行名称": candidate_row.get("运行名称", "").strip(),
        "方向ID": candidate_row.get("方向ID", "").strip(),
        "关键词": candidate_keyword(candidate_row),
        "样品ID": candidate_row.get("样品ID", "").strip(),
        "样品ASIN": candidate_row.get("样品ASIN", "").strip().upper(),
        "广告词数量": "",
        "广告活动结构摘要": "",
        "广告依赖状态": "HOLD",
        "自然位趋势摘要": "",
        "广告位趋势摘要": "",
        "坑位稳定性状态": "HOLD",
        "抓取时间": iso_now(),
        "来源模块": "SIF_广告透视仪/查坑位",
    }
    if source_row:
        for field in base:
            if field in source_row and str(source_row.get(field, "")).strip():
                base[field] = str(source_row.get(field, "")).strip()
        base["运行名称"] = candidate_row.get("运行名称", "").strip()
        base["方向ID"] = candidate_row.get("方向ID", "").strip()
        base["关键词"] = candidate_keyword(candidate_row)
        base["样品ID"] = candidate_row.get("样品ID", "").strip()
        base["样品ASIN"] = candidate_row.get("样品ASIN", "").strip().upper()
    return base


def compare_metric(rule: dict[str, str], value: str) -> bool | None:
    comparator = str(rule.get("comparator", "")).strip()
    threshold = str(rule.get("threshold_value", "")).strip()
    if comparator in {">=", "<=", ">", "<"}:
        try:
            metric = float(str(value).strip())
            target = float(threshold)
        except ValueError:
            return None
        if comparator == ">=":
            return metric >= target
        if comparator == "<=":
            return metric <= target
        if comparator == ">":
            return metric > target
        if comparator == "<":
            return metric < target
    if comparator == "==":
        text_value = str(value or "").strip().upper()
        if not text_value:
            return None
        return text_value == threshold.strip().upper()
    raise SIFEnrichmentError(f"Unsupported comparator in 90 table: {comparator}", "UNSUPPORTED_COMPARATOR")


def reason_with_prefix(prefix: str, reasons: list[str]) -> str:
    cleaned = [reason for reason in reasons if str(reason or "").strip()]
    cleaned = split_multi(join_unique(cleaned))
    if not cleaned:
        return prefix
    return prefix + "__" + "__".join(cleaned)


def evaluate_step5_row(
    candidate_row: dict[str, str],
    row_50: dict[str, str],
    row_51: dict[str, str],
    row_52: dict[str, str],
    matched_50: bool,
    matched_51: bool,
    matched_52: bool,
    detail_summary: dict[str, Any],
    search_summary: dict[str, Any],
    step5_rules: list[dict[str, str]],
    batch_id: str,
) -> dict[str, str]:
    core_status = normalize_status(row_50.get("核心流量结构状态"))
    keyword_status = normalize_status(row_51.get("关键词价值状态"))
    ad_status = normalize_status(row_52.get("广告依赖状态"))
    pit_status = normalize_status(row_52.get("坑位稳定性状态"))

    blocked_reasons: list[str] = []
    detail_reason = str(detail_summary.get("reason_code", "")).strip() if detail_summary else ""
    search_reason = str(search_summary.get("reason_code", "")).strip() if search_summary else ""

    if normalize_status(candidate_row.get("当前下推状态", "")) != "PASS":
        blocked_reasons.append("CANDIDATE_POOL_NOT_READY")
    if not matched_50:
        blocked_reasons.append("SIF_DETAIL_SURFACE_NOT_COLLECTED")
    if not matched_51 or not matched_52:
        blocked_reasons.append("SIF_SEARCH_SURFACE_NOT_COLLECTED")
    if detail_reason and detail_reason != "DETAIL_SURFACE_VISIBLE":
        blocked_reasons.append(detail_reason)
    if search_reason and search_reason != "SEARCH_SURFACE_VISIBLE":
        blocked_reasons.append(search_reason)

    metric_source = {
        "自然流量占比_pct": row_50.get("自然流量占比_pct", ""),
        "广告流量占比_pct": row_50.get("广告流量占比_pct", ""),
        "高价值关键词数": row_51.get("高价值关键词数", ""),
        "建议竞价中位数": row_51.get("建议竞价中位数", ""),
        "坑位稳定性状态": row_52.get("坑位稳定性状态", ""),
    }

    pass_count = 0
    fail_count = 0
    fail_reasons: list[str] = []
    hold_reasons: list[str] = []
    alignment_blocked = bool(blocked_reasons)

    for rule in step5_rules:
        metric_name = str(rule.get("metric_name", "")).strip()
        rule_id = str(rule.get("rule_id", "")).strip()
        metric_value = str(metric_source.get(metric_name, "")).strip()
        comparator_result = compare_metric(rule, metric_value)
        if comparator_result is True:
            pass_count += 1
            continue
        if comparator_result is False:
            fail_count += 1
            if str(rule.get("hard_fail", "")).strip().upper() == "TRUE":
                fail_reasons.append(rule_id)
            else:
                hold_reasons.append(rule_id)
            continue
        if alignment_blocked:
            continue
        blank_action = normalize_status(rule.get("blank_action", ""), default="HOLD")
        if blank_action == "FAIL":
            fail_count += 1
            fail_reasons.append(rule_id)
        elif blank_action == "HOLD":
            hold_reasons.append(rule_id)

    if any(status == "FAIL" for status in [core_status, keyword_status, ad_status, pit_status]) or fail_reasons:
        overall_status = "FAIL"
    elif alignment_blocked or any(status == "HOLD" for status in [core_status, keyword_status, ad_status, pit_status]) or hold_reasons:
        overall_status = "HOLD"
    else:
        overall_status = "PASS"

    if overall_status == "FAIL":
        reason_code = join_unique(fail_reasons or ["STEP5_COMPONENT_STATUS_FAIL"])
    elif overall_status == "HOLD":
        base_reasons = blocked_reasons or hold_reasons or ["STEP5_COMPONENT_STATUS_HOLD"]
        reason_code = reason_with_prefix("BLOCKED_BY_SIF_OR_POOL_ALIGNMENT", base_reasons) if blocked_reasons else join_unique(base_reasons)
    else:
        reason_code = "PASS"

    return {
        "运行名称": candidate_row.get("运行名称", "").strip(),
        "方向ID": candidate_row.get("方向ID", "").strip(),
        "关键词": candidate_keyword(candidate_row),
        "样品ID": candidate_row.get("样品ID", "").strip(),
        "样品ASIN": candidate_row.get("样品ASIN", "").strip().upper(),
        "核心流量结构状态": core_status,
        "关键词价值状态": keyword_status,
        "广告依赖状态": ad_status,
        "坑位稳定性状态": pit_status,
        "命中规则数": str(pass_count),
        "失败规则数": str(fail_count),
        "整体状态": overall_status,
        "失败原因代码": reason_code if reason_code != "PASS" else "",
        "是否下推到Step6": "是" if overall_status == "PASS" else "否",
        "下推批次号": batch_id,
    }


def lookup_stage_status(
    queue_rows: list[dict[str, str]],
    candidate_row: dict[str, str],
    stage_code: str,
) -> str:
    direction_ids = split_multi(candidate_row.get("方向ID", ""))
    keywords = split_multi(candidate_row.get("核心关键词", "")) or [candidate_keyword(candidate_row)]
    sample_keys = {
        str(candidate_row.get("样品ID", "")).strip(),
        str(candidate_row.get("样品ASIN", "")).strip().upper(),
    }
    for queue_row in queue_rows:
        if str(queue_row.get("stage_code", "")).strip() != stage_code:
            continue
        if direction_ids and str(queue_row.get("方向ID", "")).strip() not in direction_ids:
            continue
        queue_keyword = str(queue_row.get("关键词", "")).strip()
        if keywords and queue_keyword not in keywords:
            continue
        return normalize_status(queue_row.get("status", "HOLD"))
    for queue_row in queue_rows:
        if str(queue_row.get("stage_code", "")).strip() != stage_code:
            continue
        snapshot = str(queue_row.get("data_snapshot", "")).strip()
        if any(key and key in snapshot for key in sample_keys):
            return normalize_status(queue_row.get("status", "HOLD"))
    return "HOLD"


def build_daytime_row(candidate_row: dict[str, str]) -> dict[str, str]:
    return {
        "运行名称": candidate_row.get("运行名称", "").strip(),
        "方向ID": candidate_row.get("方向ID", "").strip(),
        "样品ID": candidate_row.get("样品ID", "").strip(),
        "样品ASIN": candidate_row.get("样品ASIN", "").strip().upper(),
        "样品标题": candidate_row.get("样品标题", "").strip(),
        "核心关键词": candidate_row.get("核心关键词", "").strip(),
        "长尾关键词": candidate_row.get("长尾关键词", "").strip(),
        "目标售价": "",
        "目标MOQ": "",
        "供应商名称": "",
        "供应商链接": "",
        "出厂价": "",
        "包装成本": "",
        "头程成本": "",
        "平台费预估": "",
        "仓储费预估": "",
        "利润核价": "",
        "合规": "",
        "改良点": "",
        "最终解释": "",
        "最终GoNoGo": "",
        "人工处理状态": "PENDING",
        "备注": "",
    }


def count_pass_steps(queue_rows: list[dict[str, str]], candidate_row: dict[str, str], row_53: dict[str, str]) -> int:
    statuses = [
        lookup_stage_status(queue_rows, candidate_row, "STEP1_DIRECTION_GATE"),
        lookup_stage_status(queue_rows, candidate_row, "STEP2_KEYWORD_GATE"),
        lookup_stage_status(queue_rows, candidate_row, "STEP3_MARKET_GATE"),
        lookup_stage_status(queue_rows, candidate_row, "STEP4_BENCHMARK_GATE"),
        normalize_status(row_53.get("整体状态", "")),
    ]
    return sum(1 for status in statuses if status == "PASS")


def markdown_summary(summary: dict[str, Any]) -> str:
    reason_counts = summary.get("reason_counts", {})
    lines = [
        "# 61 待供应链核利清单",
        "",
        f"- batch_id: `{summary['batch_id']}`",
        f"- status: `{summary['status']}`",
        f"- reason_code: `{summary['reason_code']}`",
        f"- candidate_pool_path: `{summary['candidate_pool_path']}`",
        f"- aligned_50_rows: `{summary['aligned_50_rows']}`",
        f"- aligned_51_rows: `{summary['aligned_51_rows']}`",
        f"- aligned_52_rows: `{summary['aligned_52_rows']}`",
        f"- step5_gate_rows: `{summary['step5_gate_rows']}`",
        f"- daytime_rows: `{summary['daytime_rows']}`",
        "",
        "## Counts",
        "",
        f"- matched_detail_rows: `{summary['matched_detail_rows']}`",
        f"- matched_search_rows: `{summary['matched_search_rows']}`",
        f"- step5_pass_rows: `{summary['step5_status_counts'].get('PASS', 0)}`",
        f"- step5_hold_rows: `{summary['step5_status_counts'].get('HOLD', 0)}`",
        f"- step5_fail_rows: `{summary['step5_status_counts'].get('FAIL', 0)}`",
        "",
        "## Top Reasons",
        "",
    ]
    if reason_counts:
        lines.append("| reason_code | count |")
        lines.append("| --- | --- |")
        for reason_code, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"| {reason_code} | {count} |")
    else:
        lines.append("- `PASS`")

    lines.extend(
        [
            "",
            "## Manual Fields",
            "",
            "- `合规` 保持留空",
            "- `改良点` 保持留空",
            "- `最终解释` 保持留空",
            "- `利润核价` 保持留空",
            "- `最终GoNoGo` 保持留空",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    batch_id = str(args.batch_id or f"STEP5_STEP6_{timestamp_slug()}")
    output_dir = repo_path(args.output_dir, "output_dir") if args.output_dir else default_output_dir(batch_id)
    log_dir = repo_path(args.log_dir, "log_dir")
    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    candidate_pool_path = repo_path(args.candidate_pool_csv, "candidate_pool_csv") if args.candidate_pool_csv else latest_path("outputs/selection_runs/*/02_generated_outputs/60_候选样品池.csv", "candidate_pool_csv", exclude_root=output_dir)
    candidate_pool_summary_path = (
        repo_path(args.candidate_pool_summary, "candidate_pool_summary")
        if args.candidate_pool_summary
        else ensure_within_repo(candidate_pool_path.with_name("candidate_pool_summary.json"), "candidate_pool_summary")
    )
    detail_csv_path = repo_path(args.detail_csv, "detail_csv") if args.detail_csv else latest_path("outputs/selection_runs/*/02_generated_outputs/50_SIF流量结构补强.csv", "detail_csv", exclude_root=output_dir)
    detail_json_path = repo_path(args.detail_json, "detail_json") if args.detail_json else latest_path("outputs/selection_runs/*/02_generated_outputs/sif_detail_surface_probe.json", "detail_json", exclude_root=output_dir)
    search_51_path = repo_path(args.search_51_csv, "search_51_csv") if args.search_51_csv else latest_path("outputs/selection_runs/*/02_generated_outputs/51_SIF关键词价值补强.csv", "search_51_csv", exclude_root=output_dir)
    search_52_path = repo_path(args.search_52_csv, "search_52_csv") if args.search_52_csv else latest_path("outputs/selection_runs/*/02_generated_outputs/52_SIF广告结构补强.csv", "search_52_csv", exclude_root=output_dir)
    search_json_path = repo_path(args.search_json, "search_json") if args.search_json else latest_path("outputs/selection_runs/*/02_generated_outputs/sif_search_surface_probe.json", "search_json", exclude_root=output_dir)

    candidate_rows = load_dict_rows(candidate_pool_path)
    if not candidate_rows:
        raise SIFEnrichmentError(f"Candidate pool has no data rows: {candidate_pool_path}", "CANDIDATE_POOL_EMPTY")

    candidate_summary: dict[str, Any] = {}
    if candidate_pool_summary_path.exists():
        candidate_summary = json.loads(candidate_pool_summary_path.read_text(encoding="utf-8"))
    detail_summary = json.loads(detail_json_path.read_text(encoding="utf-8"))
    search_summary = json.loads(search_json_path.read_text(encoding="utf-8"))

    queue_path = repo_path(args.queue_csv, "queue_csv") if args.queue_csv else None
    if queue_path is None:
        queue_hint = str(candidate_summary.get("queue_path", "")).strip()
        if queue_hint:
            queue_path = repo_path(queue_hint, "queue_csv")
        else:
            queue_path = latest_path("outputs/selection_runs/*/02_generated_outputs/batch_queue_status.csv", "queue_csv")
    queue_rows = load_dict_rows(queue_path)

    detail_rows = load_dict_rows(detail_csv_path)
    rows_51_source = load_dict_rows(search_51_path)
    rows_52_source = load_dict_rows(search_52_path)

    detail_index = index_by_sample(detail_rows)
    rows_51_index = index_by_sample(rows_51_source)
    rows_52_index = index_by_sample(rows_52_source)
    step5_rules = load_step_rules("STEP5")
    step6_rules = load_step_rules("STEP6")
    step6_threshold = int(step6_rules[0]["threshold_value"]) if step6_rules else 5

    aligned_50: list[dict[str, str]] = []
    aligned_51: list[dict[str, str]] = []
    aligned_52: list[dict[str, str]] = []
    rows_53: list[dict[str, str]] = []
    rows_61: list[dict[str, str]] = []

    matched_detail_rows = 0
    matched_search_rows = 0
    reason_counts: dict[str, int] = {}
    step5_status_counts = {"PASS": 0, "FAIL": 0, "HOLD": 0}

    for candidate_row in candidate_rows:
        matched_50_row = first_match(candidate_row, detail_index)
        matched_51_row = first_match(candidate_row, rows_51_index)
        matched_52_row = first_match(candidate_row, rows_52_index)
        if matched_50_row:
            matched_detail_rows += 1
        if matched_51_row or matched_52_row:
            matched_search_rows += 1

        detail_payload = detail_summary if matched_50_row and matched_summary(detail_summary, candidate_row) else {}
        search_payload = search_summary if (matched_51_row or matched_52_row) and matched_summary(search_summary, candidate_row) else {}

        row_50 = aligned_50_row(candidate_row, matched_50_row or None)
        row_51 = aligned_51_row(candidate_row, matched_51_row or None)
        row_52 = aligned_52_row(candidate_row, matched_52_row or None)
        row_53 = evaluate_step5_row(
            candidate_row=candidate_row,
            row_50=row_50,
            row_51=row_51,
            row_52=row_52,
            matched_50=bool(matched_50_row),
            matched_51=bool(matched_51_row),
            matched_52=bool(matched_52_row),
            detail_summary=detail_payload,
            search_summary=search_payload,
            step5_rules=step5_rules,
            batch_id=batch_id,
        )

        aligned_50.append(row_50)
        aligned_51.append(row_51)
        aligned_52.append(row_52)
        rows_53.append(row_53)

        step5_status = normalize_status(row_53.get("整体状态", "HOLD"))
        step5_status_counts[step5_status] = step5_status_counts.get(step5_status, 0) + 1
        reason_key = row_53.get("失败原因代码", "").strip() or "PASS"
        reason_counts[reason_key] = reason_counts.get(reason_key, 0) + 1

        pass_steps = count_pass_steps(queue_rows, candidate_row, row_53)
        if pass_steps >= step6_threshold and step5_status == "PASS":
            rows_61.append(build_daytime_row(candidate_row))

    path_50 = ensure_within_repo(output_dir / FILE_50, "path_50")
    path_51 = ensure_within_repo(output_dir / FILE_51, "path_51")
    path_52 = ensure_within_repo(output_dir / FILE_52, "path_52")
    path_53 = ensure_within_repo(output_dir / FILE_53, "path_53")
    path_61 = ensure_within_repo(output_dir / FILE_61, "path_61")
    path_61_md = ensure_within_repo(output_dir / FILE_61_MD, "path_61_md")
    path_summary = ensure_within_repo(output_dir / FILE_SUMMARY_JSON, "path_summary")

    for file_name, path, rows in [
        (FILE_50, path_50, aligned_50),
        (FILE_51, path_51, aligned_51),
        (FILE_52, path_52, aligned_52),
        (FILE_53, path_53, rows_53),
        (FILE_61, path_61, rows_61),
    ]:
        fields = load_field_order(file_name)
        write_csv_atomic(path, fields, [[str(row.get(field, "")).strip() for field in fields] for row in rows])

    status = "PASS" if rows_53 and all(row["整体状态"] == "PASS" for row in rows_53) and rows_61 else "HOLD"
    non_pass_reasons = [reason for reason in reason_counts if reason != "PASS"]
    non_pass_reasons.sort(key=lambda item: (-reason_counts[item], item))
    summary_reason = "PASS" if status == "PASS" else join_unique(non_pass_reasons[:2]) or "BLOCKED_BY_SIF_OR_POOL_ALIGNMENT"

    summary = {
        "timestamp": iso_now(),
        "module": "sif_enrichment_daytime_pack",
        "batch_id": batch_id,
        "status": status,
        "reason_code": summary_reason,
        "candidate_pool_path": str(candidate_pool_path),
        "candidate_pool_summary_path": str(candidate_pool_summary_path),
        "queue_path": str(queue_path),
        "detail_csv_path": str(detail_csv_path),
        "detail_json_path": str(detail_json_path),
        "search_51_path": str(search_51_path),
        "search_52_path": str(search_52_path),
        "search_json_path": str(search_json_path),
        "aligned_50_path": str(path_50),
        "aligned_51_path": str(path_51),
        "aligned_52_path": str(path_52),
        "step5_gate_path": str(path_53),
        "daytime_csv_path": str(path_61),
        "daytime_md_path": str(path_61_md),
        "candidate_pool_row_count": len(candidate_rows),
        "aligned_50_rows": len(aligned_50),
        "aligned_51_rows": len(aligned_51),
        "aligned_52_rows": len(aligned_52),
        "step5_gate_rows": len(rows_53),
        "daytime_rows": len(rows_61),
        "matched_detail_rows": matched_detail_rows,
        "matched_search_rows": matched_search_rows,
        "step5_status_counts": step5_status_counts,
        "reason_counts": reason_counts,
        "step6_threshold": step6_threshold,
        "candidate_pool_status": str(candidate_summary.get("status", "")).strip(),
        "candidate_pool_reason": str(candidate_summary.get("reason_code", "")).strip(),
        "detail_probe_status": str(detail_summary.get("status", "")).strip(),
        "detail_probe_reason": str(detail_summary.get("reason_code", "")).strip(),
        "search_probe_status": str(search_summary.get("status", "")).strip(),
        "search_probe_reason": str(search_summary.get("reason_code", "")).strip(),
    }

    write_json_atomic(path_summary, summary)
    path_61_md.write_text(markdown_summary(summary), encoding="utf-8")
    write_json_atomic(log_dir / RUN_LATEST, summary)
    append_jsonl(log_dir / RUN_HISTORY, summary)
    if status != "PASS":
        append_jsonl(log_dir / RUN_FAILURES, summary)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
