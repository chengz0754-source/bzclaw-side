from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from keyword_chain_common import (
    KeywordChainError,
    KeywordContext,
    bool_cn,
    ensure_within_repo,
    format_number,
    iso_now,
    load_field_order,
    load_step2_rules,
    log_dir_from_namespace,
    normalize_keyword_text,
    output_dir_from_namespace,
    persist_run_summary,
    resolve_context_from_namespace,
    safe_float,
    timestamp_slug,
    write_csv_atomic,
)


RAW_FILE = "20_关键词证据词池原始结果.csv"
CLEANED_FILE = "21_关键词证据词池清洗结果.csv"
GATE_FILE = "22_关键词证据词池下推结果.csv"
OUTPUT_INDEX_CSV = "keyword_chain_output_index.csv"
OUTPUT_INDEX_MD = "keyword_chain_output_index.md"

NOISE_EXACT_TERMS = {"amazon", "tiktok", "temu", "shein"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build canonical STEP2 keyword evidence pool outputs from repo-local raw collection artifacts.",
    )
    parser.add_argument("--context-row-index", type=int, default=1)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--direction-id", default=None)
    parser.add_argument("--keyword", default=None)
    parser.add_argument("--category-hint", default=None)
    parser.add_argument("--site", default=None)
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--sample-top-n", type=int, default=None)
    parser.add_argument("--max-push-keywords", type=int, default=None)
    parser.add_argument("--keyword-research-run", default=None)
    parser.add_argument("--keyword-trend-run", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--log-dir", default=None)
    parser.add_argument("--batch-id", default=None)
    return parser.parse_args()


def latest_run_path(log_dir: Path, latest_name: str) -> Path:
    return ensure_within_repo(log_dir / latest_name, "latest_run_path")


def load_raw_payload(run_path: Path) -> dict[str, Any] | None:
    if not run_path.exists():
        return None
    run_summary = json.loads(run_path.read_text(encoding="utf-8"))
    if run_summary.get("status") != "PASS":
        return {"summary": run_summary, "artifact": None}
    raw_artifact_path = Path(run_summary["raw_artifact_path"])
    if not raw_artifact_path.exists():
        raise KeywordChainError(
            f"Latest successful raw artifact is missing on disk: {raw_artifact_path}",
            "RAW_ARTIFACT_MISSING",
        )
    artifact = json.loads(raw_artifact_path.read_text(encoding="utf-8"))
    return {"summary": run_summary, "artifact": artifact}


def derive_tags(monthly_searches: str, growth_pct: str, click_concentration_pct: str, traffic_cost_index: str) -> tuple[str, str]:
    search_value = safe_float(monthly_searches) or 0.0
    growth_value = safe_float(growth_pct) or 0.0
    click_value = safe_float(click_concentration_pct) or 999.0
    cost_value = safe_float(traffic_cost_index) or 999.0

    opportunity_tags: list[str] = []
    trend_tags: list[str] = []
    if search_value >= 1000 and click_value <= 45 and cost_value <= 70:
        opportunity_tags.append("Opportunities")
    elif search_value >= 500 and click_value <= 45:
        opportunity_tags.append("Potential")

    if growth_value >= 30:
        trend_tags.append("RapidGrowth")
    elif growth_value >= 10:
        trend_tags.append("Trending")

    return ";".join(opportunity_tags), ";".join(trend_tags)


def canonical_raw_rows(context: KeywordContext, raw_sources: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source in raw_sources:
        artifact = source["artifact"]
        if artifact is None:
            continue
        artifact_path = source["summary"]["raw_artifact_path"]
        for item in artifact.get("rows", []):
            monthly_searches = format_number(safe_float(item.get("monthly_searches")))
            growth_pct = format_number(safe_float(item.get("growth_pct")))
            click_concentration = format_number(safe_float(item.get("click_concentration_pct")))
            traffic_cost_index = format_number(safe_float(item.get("traffic_cost_index")))
            opportunity_tags, trend_tags = derive_tags(monthly_searches, growth_pct, click_concentration, traffic_cost_index)
            rows.append(
                {
                    "运行名称": context.run_name,
                    "方向ID": context.direction_id,
                    "方向词": context.keyword,
                    "关键词来源模块": item.get("source_module", artifact.get("module", "")),
                    "关键词": str(item.get("keyword", "")).strip(),
                    "站点": item.get("site", context.site),
                    "主类目": item.get("main_category", context.category_hint),
                    "月搜索量": monthly_searches,
                    "搜索频率排名": format_number(safe_float(item.get("search_frequency_rank"))),
                    "搜索量增长率_pct": growth_pct,
                    "点击集中度_pct": click_concentration,
                    "流量成本指数": traffic_cost_index,
                    "机会标签": item.get("opportunity_tag", "") or opportunity_tags,
                    "趋势标签": item.get("trend_tag", "") or trend_tags,
                    "抓取时间": item.get("captured_at", artifact.get("timestamp", iso_now())),
                    "来源查询词": item.get("source_query", context.keyword),
                    "来源文件": item.get("source_file", artifact_path),
                }
            )
    return rows


def keyword_role(normalized_keyword: str, direction_normalized: str) -> str:
    if normalized_keyword == direction_normalized:
        return "核心词"
    direction_tokens = set(direction_normalized.split())
    keyword_tokens = normalized_keyword.split()
    if direction_tokens and direction_tokens.issubset(set(keyword_tokens)) and len(keyword_tokens) <= max(3, len(direction_tokens) + 2):
        return "次级核心词"
    return "长尾词"


def exclusion_reason(normalized_keyword: str) -> str:
    if not normalized_keyword:
        return "NO_SIGNAL_KEYWORD"
    if normalized_keyword in NOISE_EXACT_TERMS:
        return "NOISE_PLATFORM_TERM"
    if normalized_keyword.isdigit():
        return "NOISE_NUMERIC_ONLY"
    if normalized_keyword.startswith("b0") and len(normalized_keyword.replace(" ", "")) == 10:
        return "NOISE_ASIN_TOKEN"
    if len(normalized_keyword) < 3:
        return "TOO_SHORT"
    return ""


def sort_score(row: dict[str, str]) -> str:
    score = 0.0
    score += min(100.0, safe_float(row.get("月搜索量")) or 0.0) / 10.0
    score += safe_float(row.get("搜索量增长率_pct")) or 0.0
    score -= safe_float(row.get("点击集中度_pct")) or 0.0
    score -= safe_float(row.get("流量成本指数")) or 0.0
    return format_number(score)


def build_cleaned_rows(context: KeywordContext, raw_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in raw_rows:
        grouped[normalize_keyword_text(row.get("关键词"))].append(row)

    cleaned_rows: list[dict[str, str]] = []
    for normalized_keyword, rows in grouped.items():
        representative = rows[0]
        monthly_searches = max((safe_float(row.get("月搜索量")) for row in rows if safe_float(row.get("月搜索量")) is not None), default=None)
        growth_pct = max((safe_float(row.get("搜索量增长率_pct")) for row in rows if safe_float(row.get("搜索量增长率_pct")) is not None), default=None)
        click_concentration = max((safe_float(row.get("点击集中度_pct")) for row in rows if safe_float(row.get("点击集中度_pct")) is not None), default=None)
        traffic_cost = max((safe_float(row.get("流量成本指数")) for row in rows if safe_float(row.get("流量成本指数")) is not None), default=None)
        exclusion_code = exclusion_reason(normalized_keyword)
        excluded = bool(exclusion_code)
        cleaned = {
            "运行名称": context.run_name,
            "方向ID": context.direction_id,
            "方向词": context.keyword,
            "关键词": representative.get("关键词", ""),
            "标准化关键词": normalized_keyword,
            "关键词角色": "噪音词" if excluded else keyword_role(normalized_keyword, normalize_keyword_text(context.keyword)),
            "去重组ID": f"KWD_{abs(hash((context.site, normalized_keyword))) % 10_000_000:07d}" if normalized_keyword else "",
            "排除标记": bool_cn(excluded),
            "排除原因代码": exclusion_code,
            "月搜索量": format_number(monthly_searches),
            "搜索量增长率_pct": format_number(growth_pct),
            "点击集中度_pct": format_number(click_concentration),
            "流量成本指数": format_number(traffic_cost),
            "排序分值": "",
            "抓取时间": max((row.get("抓取时间", "") for row in rows), default=iso_now()),
            "机会标签": ";".join(sorted({tag for row in rows for tag in str(row.get("机会标签", "")).split(";") if tag})),
            "趋势标签": ";".join(sorted({tag for row in rows for tag in str(row.get("趋势标签", "")).split(";") if tag})),
            "站点": representative.get("站点", context.site),
        }
        cleaned["排序分值"] = sort_score(cleaned)
        cleaned_rows.append(cleaned)

    cleaned_rows.sort(key=lambda row: (row["排除标记"], -(safe_float(row["排序分值"]) or 0.0), row["标准化关键词"]))
    return cleaned_rows


def evaluate_rule(row: dict[str, str], rule: dict[str, str]) -> tuple[str, str]:
    metric_name = rule["metric_name"]
    comparator = rule["comparator"]
    blank_action = rule["blank_action"]
    hard_fail = rule["hard_fail"] == "TRUE"

    if comparator == "in":
        candidates = {item.strip() for item in rule["threshold_value"].split(";") if item.strip()}
        values = {item.strip() for item in f"{row.get('机会标签', '')};{row.get('趋势标签', '')}".split(";") if item.strip()}
        if not values:
            return blank_action, f"blank->{blank_action}"
        if values & candidates:
            return "PASS", "tag_match"
        return ("FAIL" if hard_fail else "HOLD"), "tag_miss"

    metric_value = safe_float(row.get(metric_name))
    threshold_value = safe_float(rule["threshold_value"])
    if metric_value is None or threshold_value is None:
        return blank_action, f"blank->{blank_action}"

    passed = False
    if comparator == ">=":
        passed = metric_value >= threshold_value
    elif comparator == "<=":
        passed = metric_value <= threshold_value
    elif comparator == "==":
        passed = metric_value == threshold_value
    else:
        raise KeywordChainError(f"Unsupported STEP2 comparator: {comparator}", "UNSUPPORTED_COMPARATOR")

    if passed:
        return "PASS", "comparison_pass"
    return ("FAIL" if hard_fail else "HOLD"), "threshold_miss"


def build_gate_rows(cleaned_rows: list[dict[str, str]], rules: list[dict[str, str]], batch_id: str) -> tuple[list[dict[str, str]], dict[str, int]]:
    gate_rows: list[dict[str, str]] = []
    summary = {"PASS": 0, "FAIL": 0, "HOLD": 0}
    for row in cleaned_rows:
        if row["排除标记"] == "是":
            gate_rows.append(
                {
                    "运行名称": row["运行名称"],
                    "方向ID": row["方向ID"],
                    "关键词": row["标准化关键词"],
                    "站点": row.get("站点", ""),
                    "月搜索量": row["月搜索量"],
                    "搜索量增长率_pct": row["搜索量增长率_pct"],
                    "点击集中度_pct": row["点击集中度_pct"],
                    "流量成本指数": row["流量成本指数"],
                    "机会标签": row.get("机会标签", ""),
                    "趋势标签": row.get("趋势标签", ""),
                    "命中规则数": "0",
                    "失败规则数": "1",
                    "整体状态": "FAIL",
                    "失败原因代码": f"CLEANED_EXCLUSION:{row['排除原因代码']}",
                    "是否下推到Step3": "否",
                    "下推批次号": batch_id,
                }
            )
            summary["FAIL"] += 1
            continue

        non_pass_codes: list[str] = []
        pass_count = 0
        fail_count = 0
        overall_status = "PASS"
        for rule in rules:
            outcome, _detail = evaluate_rule(row, rule)
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
                "关键词": row["标准化关键词"],
                "站点": row.get("站点", ""),
                "月搜索量": row["月搜索量"],
                "搜索量增长率_pct": row["搜索量增长率_pct"],
                "点击集中度_pct": row["点击集中度_pct"],
                "流量成本指数": row["流量成本指数"],
                "机会标签": row.get("机会标签", ""),
                "趋势标签": row.get("趋势标签", ""),
                "命中规则数": str(pass_count),
                "失败规则数": str(fail_count),
                "整体状态": overall_status,
                "失败原因代码": ";".join(non_pass_codes),
                "是否下推到Step3": bool_cn(overall_status == "PASS"),
                "下推批次号": batch_id,
            }
        )
    return gate_rows, summary


def write_ordered_csv(path: Path, file_name: str, rows: list[dict[str, str]]) -> None:
    field_order = load_field_order(file_name)
    csv_rows = [[row.get(field, "") for field in field_order] for row in rows]
    write_csv_atomic(path, field_order, csv_rows)


def output_index_rows(output_dir: Path, raw_path: Path, cleaned_path: Path, gate_path: Path, raw_sources: list[dict[str, Any]], summary: dict[str, int]) -> list[dict[str, str]]:
    return [
        {
            "artifact_id": "STEP2_RAW",
            "layer": "raw_layer",
            "artifact_path": str(raw_path),
            "status": "CREATED",
            "notes": f"Canonical raw keyword evidence layer built from {len(raw_sources)} source module(s).",
        },
        {
            "artifact_id": "STEP2_CLEANED",
            "layer": "cleaned_layer",
            "artifact_path": str(cleaned_path),
            "status": "CREATED",
            "notes": "Canonical cleaned keyword evidence layer with deterministic dedupe and exclusion flags.",
        },
        {
            "artifact_id": "STEP2_GATE",
            "layer": "gate_result_layer",
            "artifact_path": str(gate_path),
            "status": "CREATED",
            "notes": f"Gate summary PASS={summary['PASS']} FAIL={summary['FAIL']} HOLD={summary['HOLD']}.",
        },
        {
            "artifact_id": "OUTPUT_DIR",
            "layer": "run_output_layer",
            "artifact_path": str(output_dir),
            "status": "CREATED",
            "notes": "Ignored runtime output directory for this keyword evidence build.",
        },
    ]


def output_index_markdown(context: KeywordContext, raw_sources: list[dict[str, Any]], artifacts: list[dict[str, str]], summary: dict[str, int]) -> str:
    lines = [
        "# SellerSprite Keyword Chain Output Index",
        "",
        f"- Context source: `{context.context_source}`",
        f"- 运行名称: `{context.run_name}`",
        f"- 方向ID: `{context.direction_id}`",
        f"- 方向词: `{context.keyword}`",
        f"- 站点: `{context.site}`",
        f"- Raw source modules: `{', '.join(source['summary']['module'] for source in raw_sources)}`",
        f"- Gate summary: `PASS={summary['PASS']} FAIL={summary['FAIL']} HOLD={summary['HOLD']}`",
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
    batch_id = args.batch_id or f"STEP2_GATE_{timestamp_slug()}"
    summary: dict[str, Any] = {
        "timestamp": iso_now(),
        "module": "keyword_chain_build",
        "status": "BLOCKED",
        "reason_code": "",
        "message": "",
        "运行名称": context.run_name,
        "方向ID": context.direction_id,
        "方向词": context.keyword,
        "站点": context.site,
        "output_dir": str(output_dir),
        "raw_sources": [],
        "raw_row_count": 0,
        "cleaned_row_count": 0,
        "gate_summary": {},
    }

    try:
        keyword_research_run = Path(args.keyword_research_run) if args.keyword_research_run else latest_run_path(log_dir, "latest_keyword_research_run.json")
        keyword_trend_run = Path(args.keyword_trend_run) if args.keyword_trend_run else latest_run_path(log_dir, "latest_keyword_trend_run.json")
        keyword_research_run = ensure_within_repo(keyword_research_run, "keyword_research_run")
        keyword_trend_run = ensure_within_repo(keyword_trend_run, "keyword_trend_run")

        raw_sources: list[dict[str, Any]] = []
        for run_path in (keyword_research_run, keyword_trend_run):
            payload = load_raw_payload(run_path)
            if payload is not None:
                raw_sources.append(payload)

        if not raw_sources:
            raise KeywordChainError(
                "No keyword raw run metadata was found. Run export_keyword_research.py and export_keyword_trend.py first.",
                "STEP2_RAW_RUNS_MISSING",
            )

        summary["raw_sources"] = [
            {
                "module": source["summary"].get("module"),
                "status": source["summary"].get("status"),
                "reason_code": source["summary"].get("reason_code"),
                "raw_artifact_path": source["summary"].get("raw_artifact_path", ""),
            }
            for source in raw_sources
        ]
        successful_sources = [source for source in raw_sources if source["artifact"] is not None]
        if not successful_sources:
            raise KeywordChainError(
                "All available keyword collection runs are blocked. Current repo-local SellerSprite auth cannot produce live raw keyword rows.",
                "STEP2_ALL_RAW_RUNS_BLOCKED",
            )

        raw_rows = canonical_raw_rows(context, successful_sources)
        if not raw_rows:
            raise KeywordChainError(
                "Successful raw artifacts were found, but they did not contain any keyword rows.",
                "STEP2_RAW_ROWS_EMPTY",
            )

        cleaned_rows = build_cleaned_rows(context, raw_rows)
        rules = load_step2_rules()
        gate_rows, gate_summary = build_gate_rows(cleaned_rows, rules, batch_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_path = output_dir / RAW_FILE
        cleaned_path = output_dir / CLEANED_FILE
        gate_path = output_dir / GATE_FILE
        write_ordered_csv(raw_path, RAW_FILE, raw_rows)

        cleaned_field_order = load_field_order(CLEANED_FILE)
        cleaned_output_rows = []
        for row in cleaned_rows:
            cleaned_output_rows.append(
                {
                    "运行名称": row["运行名称"],
                    "方向ID": row["方向ID"],
                    "方向词": row["方向词"],
                    "关键词": row["关键词"],
                    "标准化关键词": row["标准化关键词"],
                    "关键词角色": row["关键词角色"],
                    "去重组ID": row["去重组ID"],
                    "排除标记": row["排除标记"],
                    "排除原因代码": row["排除原因代码"],
                    "月搜索量": row["月搜索量"],
                    "搜索量增长率_pct": row["搜索量增长率_pct"],
                    "点击集中度_pct": row["点击集中度_pct"],
                    "流量成本指数": row["流量成本指数"],
                    "排序分值": row["排序分值"],
                    "抓取时间": row["抓取时间"],
                }
            )
        write_csv_atomic(cleaned_path, cleaned_field_order, [[row.get(field, "") for field in cleaned_field_order] for row in cleaned_output_rows])
        write_ordered_csv(gate_path, GATE_FILE, gate_rows)

        artifacts = output_index_rows(output_dir, raw_path, cleaned_path, gate_path, successful_sources, gate_summary)
        output_index_path = output_dir / OUTPUT_INDEX_CSV
        output_index_md_path = output_dir / OUTPUT_INDEX_MD
        write_csv_atomic(
            output_index_path,
            ["artifact_id", "layer", "artifact_path", "status", "notes"],
            [[artifact["artifact_id"], artifact["layer"], artifact["artifact_path"], artifact["status"], artifact["notes"]] for artifact in artifacts],
        )
        output_index_md_path.write_text(output_index_markdown(context, successful_sources, artifacts, gate_summary), encoding="utf-8")

        summary["status"] = "PASS"
        summary["reason_code"] = "PASS"
        summary["message"] = "Keyword evidence pool outputs were built successfully."
        summary["raw_row_count"] = len(raw_rows)
        summary["cleaned_row_count"] = len(cleaned_rows)
        summary["gate_summary"] = gate_summary
    except KeywordChainError as exc:
        summary["status"] = "BLOCKED"
        summary["reason_code"] = exc.reason_code
        summary["message"] = str(exc)
    except Exception as exc:
        summary["status"] = "BLOCKED"
        summary["reason_code"] = "STEP2_BUILD_UNHANDLED_ERROR"
        summary["message"] = str(exc)

    persist_run_summary(log_dir, "latest_keyword_build_run.json", "keyword_build_runs.jsonl", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
