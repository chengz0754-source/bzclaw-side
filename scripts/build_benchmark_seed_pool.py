from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from typing import Any

from benchmark_chain_common import (
    BENCHMARK_RAW_ARTIFACT,
    OUTPUT_INDEX_CSV,
    OUTPUT_INDEX_MD,
    STEP4_GATE_FILE,
    STEP4_RAW_FILE,
    STEP4_SEED_FILE,
    BenchmarkChainError,
    BenchmarkContext,
    bool_cn,
    clean_number,
    ensure_within_repo,
    format_number,
    iso_now,
    load_field_order,
    load_step4_rules,
    log_dir_from_namespace,
    output_dir_from_namespace,
    persist_run_summary,
    raw_output_index_rows,
    resolve_context_from_namespace,
    safe_float,
    stable_id,
    timestamp_slug,
    write_csv_atomic,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build canonical STEP4 benchmark seed-pool outputs from the latest successful raw benchmark artifact.",
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
    parser.add_argument("--benchmark-run", default=None, help="Path to a benchmark export run summary JSON. Defaults to latest_benchmark_export_run.json.")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--log-dir", default=None)
    parser.add_argument("--batch-id", default=None)
    return parser.parse_args()


def latest_benchmark_run_path(log_dir):
    return ensure_within_repo(log_dir / "latest_benchmark_export_run.json", "latest_benchmark_export_run")


def load_raw_payload(run_summary_path):
    if not run_summary_path.exists():
        raise BenchmarkChainError(
            f"Benchmark run summary is missing: {run_summary_path}. Run export_benchmark_competitors.py first.",
            "BENCHMARK_RUN_SUMMARY_MISSING",
        )
    summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "PASS":
        raise BenchmarkChainError(
            "Latest benchmark export run is not successful. Resolve the export blocker before building 40/41/42 outputs.",
            "BENCHMARK_EXPORT_NOT_PASS",
        )
    raw_artifact_path = ensure_within_repo(Path(summary.get("raw_artifact_path", "")), "raw_artifact_path")
    if not raw_artifact_path.exists():
        raise BenchmarkChainError(f"Raw benchmark artifact is missing on disk: {raw_artifact_path}", "BENCHMARK_RAW_ARTIFACT_MISSING")
    artifact = json.loads(raw_artifact_path.read_text(encoding="utf-8"))
    return summary, artifact, raw_artifact_path


def raw_rows(context: BenchmarkContext, raw_artifact: dict[str, Any], raw_artifact_path) -> list[dict[str, str]]:
    seed = raw_artifact.get("seed_context", {})
    candidate_market_name = str(seed.get("candidate_market_name", "") or seed.get("seed_keyword", "")).strip()
    rows: list[dict[str, str]] = []
    for item in raw_artifact.get("items", []):
        if not isinstance(item, dict):
            continue
        asin = str(item.get("asin", "")).strip().upper()
        title = str(item.get("title", "") or item.get("title0", "") or "").strip()
        if not asin or not title:
            continue
        rows.append(
            {
                "运行名称": context.run_name,
                "方向ID": context.direction_id,
                "关键词": str(seed.get("seed_keyword", "") or context.keyword).strip(),
                "站点": context.site,
                "候选市场名称": candidate_market_name,
                "样品ASIN": asin,
                "样品标题": title,
                "品牌": str(item.get("brand", "") or item.get("brand0", "") or item.get("brandShort", "") or "").strip(),
                "价格": clean_number(item.get("price")),
                "评分": clean_number(item.get("rating")),
                "评论数": clean_number(item.get("reviews")),
                "BSR": clean_number(item.get("bsrRank")),
                "父体ASIN": str(item.get("parent", "") or "").strip().upper(),
                "变体数": clean_number(item.get("variations")),
                "卖家类型": str(item.get("sellerType", "") or "").strip(),
                "抓取时间": str(raw_artifact.get("timestamp", iso_now())),
                "来源模块": "Benchmark",
                "来源文件": str(raw_artifact_path),
            }
        )
    if not rows:
        raise BenchmarkChainError("Raw benchmark artifact was found, but no canonical 40-row entries could be mapped.", "BENCHMARK_RAW_ROWS_EMPTY")
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


def deduped_seed_rows(context: BenchmarkContext, rows: list[dict[str, str]], raw_artifact: dict[str, Any], overall_status: str) -> list[dict[str, str]]:
    seed = raw_artifact.get("seed_context", {})
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(dedupe_group_key(row), []).append(row)

    deduped: list[dict[str, str]] = []
    for group_key, group_rows in grouped.items():
        representative = sorted(group_rows, key=score_for_seed, reverse=True)[0]
        sample_id = stable_id("SMP", context.site, representative.get("样品ASIN", ""), representative.get("样品标题", ""))
        group_id = stable_id("DEDUPE", context.site, group_key)
        deduped.append(
            {
                "运行名称": context.run_name,
                "方向ID": context.direction_id,
                "关键词": str(seed.get("seed_keyword", "") or context.keyword).strip(),
                "样品ID": sample_id,
                "样品ASIN": representative.get("样品ASIN", ""),
                "样品标题": representative.get("样品标题", ""),
                "品牌": representative.get("品牌", ""),
                "价格": representative.get("价格", ""),
                "评分": representative.get("评分", ""),
                "评论数": representative.get("评论数", ""),
                "父体ASIN": representative.get("父体ASIN", ""),
                "变体数": representative.get("变体数", ""),
                "市场路径": str(seed.get("market_path", "")).strip(),
                "候选市场名称": str(seed.get("candidate_market_name", "") or seed.get("seed_keyword", "")).strip(),
                "进入种子池状态": overall_status,
                "去重组ID": group_id,
                "去重说明": "KEEP_HIGHEST_REVIEWS_IN_PARENT_GROUP" if representative.get("父体ASIN", "") else "UNIQUE_ASIN",
                "是否下推到Step5": bool_cn(overall_status == "PASS"),
            }
        )

    deduped.sort(key=lambda row: score_for_seed(row), reverse=True)
    if context.max_candidate_samples is not None:
        deduped = deduped[: context.max_candidate_samples]
    return deduped


def sample_metric_summary(seed_rows: list[dict[str, str]]) -> dict[str, float | None]:
    ratings = [safe_float(row.get("评分")) for row in seed_rows if safe_float(row.get("评分")) is not None]
    reviews = [safe_float(row.get("评论数")) for row in seed_rows if safe_float(row.get("评论数")) is not None]
    prices = [safe_float(row.get("价格")) for row in seed_rows if safe_float(row.get("价格")) is not None]
    candidate_count = float(len([row for row in seed_rows if row.get("样品ASIN", "").strip()]))
    top_review_share = None
    if reviews and sum(reviews) > 0:
        top_review_share = max(reviews) / sum(reviews)
    price_spread = None
    if len(prices) >= 2:
        price_spread = max(prices) - min(prices)
    return {
        "候选ASIN数": candidate_count,
        "评分中位数": median(ratings) if ratings else None,
        "头部评论占比": top_review_share,
        "价格离散度": price_spread,
    }


def evaluate_rule(metric_value: float | None, rule: dict[str, str]) -> tuple[str, str]:
    comparator = rule["comparator"]
    blank_action = rule["blank_action"]
    hard_fail = rule["hard_fail"] == "TRUE"
    threshold_value = safe_float(rule["threshold_value"])

    if metric_value is None or threshold_value is None:
        return blank_action, f"blank->{blank_action}"

    if comparator == ">=":
        passed = metric_value >= threshold_value
    elif comparator == "<=":
        passed = metric_value <= threshold_value
    elif comparator == "==":
        passed = metric_value == threshold_value
    else:
        raise BenchmarkChainError(f"Unsupported STEP4 comparator: {comparator}", "STEP4_COMPARATOR_UNSUPPORTED")

    if passed:
        return "PASS", "comparison_pass"
    return ("FAIL" if hard_fail else "HOLD"), "threshold_miss"


def gate_decision(metrics: dict[str, float | None], rules: list[dict[str, str]]) -> tuple[str, int, int, str]:
    overall_status = "PASS"
    pass_count = 0
    fail_count = 0
    non_pass_codes: list[str] = []
    for rule in rules:
        metric_name = rule["metric_name"]
        outcome, _detail = evaluate_rule(metrics.get(metric_name), rule)
        if outcome == "PASS":
            pass_count += 1
            continue
        fail_count += 1
        non_pass_codes.append(f"{rule['rule_id']}:{outcome}")
        if outcome == "FAIL":
            overall_status = "FAIL"
        elif outcome == "HOLD" and overall_status != "FAIL":
            overall_status = "HOLD"
    return overall_status, pass_count, fail_count, ";".join(non_pass_codes)


def gate_rows(seed_rows: list[dict[str, str]], batch_id: str, overall_status: str, pass_count: int, fail_count: int, reason_codes: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in seed_rows:
        rows.append(
            {
                "运行名称": row["运行名称"],
                "方向ID": row["方向ID"],
                "关键词": row["关键词"],
                "样品ID": row["样品ID"],
                "样品ASIN": row["样品ASIN"],
                "评分": row.get("评分", ""),
                "评论数": row.get("评论数", ""),
                "价格": row.get("价格", ""),
                "变体数": row.get("变体数", ""),
                "命中规则数": str(pass_count),
                "失败规则数": str(fail_count),
                "整体状态": overall_status,
                "失败原因代码": reason_codes,
                "是否下推到Step5": bool_cn(overall_status == "PASS"),
                "下推批次号": batch_id,
            }
        )
    return rows


def ordered_csv(path, file_name: str, rows: list[dict[str, str]]) -> None:
    field_order = load_field_order(file_name)
    csv_rows = [[row.get(field, "") for field in field_order] for row in rows]
    write_csv_atomic(path, field_order, csv_rows)


def output_index_markdown(context: BenchmarkContext, raw_artifact: dict[str, Any], raw_artifact_path, raw_row_count: int, metrics: dict[str, float | None], artifacts: list[dict[str, str]], overall_status: str) -> str:
    seed_context = raw_artifact.get("seed_context", {})
    lines = [
        "# SellerSprite Benchmark Chain Output Index",
        "",
        f"- Context source: `{context.context_source}`",
        f"- 运行名称: `{context.run_name}`",
        f"- 方向ID: `{context.direction_id}`",
        f"- 站点: `{context.site}`",
        f"- Seed source step: `{seed_context.get('source_step', '')}`",
        f"- Seed keyword: `{seed_context.get('seed_keyword', '')}`",
        f"- Candidate market: `{seed_context.get('candidate_market_name', '')}`",
        f"- Market path: `{seed_context.get('market_path', '')}`",
        f"- Raw artifact: `{raw_artifact_path}`",
        f"- Raw source type: `{raw_artifact.get('source_type', '')}`",
        f"- Downloaded workbook: `{raw_artifact.get('workbook_path', '')}`",
        f"- Raw item count: `{raw_row_count}`",
        f"- Gate status: `{overall_status}`",
        f"- Candidate ASIN count: `{format_number(metrics.get('候选ASIN数'))}`",
        f"- Median rating: `{format_number(metrics.get('评分中位数'))}`",
        f"- Top1 review share: `{format_number(metrics.get('头部评论占比'))}`",
        f"- Price spread: `{format_number(metrics.get('价格离散度'))}`",
        "",
        "| artifact_id | layer | status | artifact_path | notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for artifact in artifacts:
        lines.append(
            f"| {artifact['artifact_id']} | {artifact['layer']} | {artifact['status']} | {artifact['artifact_path']} | {artifact['notes']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    context = resolve_context_from_namespace(args, require_direction_id=True)
    output_dir = output_dir_from_namespace(args)
    log_dir = log_dir_from_namespace(args)
    batch_id = args.batch_id or f"STEP4_GATE_{timestamp_slug()}"
    summary: dict[str, Any] = {
        "timestamp": iso_now(),
        "module": "benchmark_build",
        "status": "BLOCKED",
        "reason_code": "",
        "message": "",
        "运行名称": context.run_name,
        "方向ID": context.direction_id,
        "方向词": context.keyword,
        "站点": context.site,
        "output_dir": str(output_dir),
        "raw_item_count": 0,
        "seed_row_count": 0,
        "gate_status": "",
        "metrics": {},
    }

    try:
        run_summary_path = ensure_within_repo(Path(args.benchmark_run), "benchmark_run") if args.benchmark_run else latest_benchmark_run_path(log_dir)
        export_summary, raw_artifact, raw_artifact_path = load_raw_payload(run_summary_path)
        rows_40 = raw_rows(context, raw_artifact, raw_artifact_path)
        metrics = sample_metric_summary(
            deduped_seed_rows(context, rows_40, raw_artifact, overall_status="PASS")
        )
        rules = load_step4_rules()
        overall_status, pass_count, fail_count, reason_codes = gate_decision(metrics, rules)
        seed_rows = deduped_seed_rows(context, rows_40, raw_artifact, overall_status)
        gate_output_rows = gate_rows(seed_rows, batch_id, overall_status, pass_count, fail_count, reason_codes)

        output_dir.mkdir(parents=True, exist_ok=True)
        raw_csv_path = output_dir / STEP4_RAW_FILE
        seed_path = output_dir / STEP4_SEED_FILE
        gate_path = output_dir / STEP4_GATE_FILE
        ordered_csv(raw_csv_path, STEP4_RAW_FILE, rows_40)
        ordered_csv(seed_path, STEP4_SEED_FILE, seed_rows)
        ordered_csv(gate_path, STEP4_GATE_FILE, gate_output_rows)

        artifacts = raw_output_index_rows(output_dir, raw_artifact_path, raw_csv_path, seed_path, gate_path, len(rows_40), overall_status)
        output_index_path = output_dir / OUTPUT_INDEX_CSV
        output_index_md_path = output_dir / OUTPUT_INDEX_MD
        write_csv_atomic(
            output_index_path,
            ["artifact_id", "layer", "artifact_path", "status", "notes"],
            [[artifact["artifact_id"], artifact["layer"], artifact["artifact_path"], artifact["status"], artifact["notes"]] for artifact in artifacts],
        )
        write_markdown(
            output_index_md_path,
            output_index_markdown(context, raw_artifact, raw_artifact_path, len(rows_40), metrics, artifacts, overall_status),
        )

        summary["status"] = "PASS"
        summary["reason_code"] = "PASS"
        summary["message"] = "Benchmark seed-pool outputs were built successfully."
        summary["raw_item_count"] = len(rows_40)
        summary["seed_row_count"] = len(seed_rows)
        summary["gate_status"] = overall_status
        summary["metrics"] = {key: clean_number(value) for key, value in metrics.items()}
        summary["benchmark_run_summary"] = str(run_summary_path)
        summary["raw_artifact_path"] = str(raw_artifact_path)
        summary["workbook_path"] = str(raw_artifact.get("workbook_path", ""))
        summary["export_summary_status"] = export_summary.get("status", "")
        summary["seed_source_step"] = raw_artifact.get("seed_context", {}).get("source_step", "")
    except BenchmarkChainError as exc:
        summary["status"] = "BLOCKED"
        summary["reason_code"] = exc.reason_code
        summary["message"] = str(exc)
    except Exception as exc:
        summary["status"] = "BLOCKED"
        summary["reason_code"] = "BENCHMARK_BUILD_UNHANDLED_ERROR"
        summary["message"] = str(exc)

    persist_run_summary(log_dir, "latest_benchmark_build_run.json", "benchmark_build_runs.jsonl", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
