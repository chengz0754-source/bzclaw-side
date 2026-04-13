#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pipeline_common import (
    alias_lookup,
    bounded_score,
    build_run_context,
    dump_log,
    find_inbox_raw_files,
    infer_asin_from_text,
    load_config_bundle,
    load_table,
    make_run_id,
    now_local,
    profile_weights,
    scan_latest_stage_outputs,
    stage_dirs,
    status_value,
    summary_dir,
    to_float,
    unique_join,
    write_csv,
    write_json,
    write_workbook,
)


STEP_NAME = "step2"
INPUT_PREFIX = "M03_niche_shortlist"
OUTPUT_PREFIX = "M04_benchmark_asin_scored"
QUEUE_PREFIX = "reverse_keyword_download_queue"

BENCHMARK_ALIASES = {
    "asin": ["asin", "parent asin", "父asin", "商品asin"],
    "monthly_sales_units": ["monthly sales", "monthly_sales_units", "月销量", "月总销量", "estimated monthly sales"],
    "monthly_revenue": ["monthly revenue", "monthly_revenue", "月销售额", "销售额($)", "estimated monthly revenue"],
    "price": ["price", "价格", "售价", "sale price"],
    "review_count": ["review count", "reviews", "评论数", "rating count"],
    "star_rating": ["star rating", "rating", "评分", "星级"],
    "brand": ["brand", "品牌"],
    "seller": ["seller", "seller name", "卖家", "店铺"],
    "listed_days": ["listed days", "days listed", "上架天数", "listing age"],
    "listed_date": ["listed date", "launch date", "上架时间", "发布时间"],
    "path_key": ["path key", "market path", "市场路径", "类目路径"],
    "niche_leaf": ["niche leaf", "niche", "细分市场", "市场"],
    "marketplace": ["marketplace", "站点"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Advance M03 niche shortlist into M04 benchmark ASIN scoring.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--mode", default="balanced")
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def parse_listed_days(row: pd.Series) -> float | None:
    listed_days = to_float(row.get("listed_days"))
    if listed_days is not None:
        return listed_days
    text = str(row.get("listed_date", "") or "").strip()
    if not text:
        return None
    for date_format in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            delta = datetime.now() - datetime.strptime(text[:19], date_format)
            return float(delta.days)
        except ValueError:
            continue
    return None


def standardize_benchmark_raw(path: Path) -> tuple[pd.DataFrame, list[str]]:
    frame = load_table(path)
    standardized, _, missing = alias_lookup(frame, BENCHMARK_ALIASES)
    if "asin" not in standardized.columns:
        standardized["asin"] = standardized.apply(lambda row: infer_asin_from_text(" ".join(str(value or "") for value in row.values)), axis=1)
    standardized["raw_source_file"] = path.name
    return standardized, missing


def wait_outputs(
    shortlist: pd.DataFrame,
    run_ctx,
    overwrite: bool,
    batch_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    step_dirs = stage_dirs(run_ctx, STEP_NAME)
    pass_rows = shortlist[shortlist["route_status"] == "PASS_TO_STEP2"].copy()
    placeholder = pass_rows[
        ["batch_id", "marketplace", "dept_l1", "parent_l2", "parent_l3", "niche_leaf", "path_key"]
    ].drop_duplicates()
    placeholder["asin"] = ""
    placeholder["benchmark_cohort"] = ""
    placeholder["step2_score"] = 0.0
    placeholder["step2_status"] = status_value(config, "wait_benchmark_raw")
    placeholder["step2_reason"] = "MISSING_BENCHMARK_RAW"
    placeholder["listed_days"] = None
    placeholder["monthly_sales_units"] = None
    placeholder["monthly_revenue"] = None
    placeholder["price"] = None
    placeholder["review_count"] = None
    placeholder["star_rating"] = None
    placeholder["brand"] = ""
    placeholder["seller"] = ""
    placeholder["is_new_winner"] = False
    placeholder["is_underserved_signal"] = False
    placeholder["route_status"] = status_value(config, "wait_benchmark_raw")

    by_niche = placeholder[
        ["batch_id", "marketplace", "dept_l1", "parent_l2", "parent_l3", "niche_leaf", "path_key", "route_status"]
    ].copy()
    by_niche["incumbent_count"] = 0
    by_niche["new_winner_count"] = 0
    by_niche["underserved_count"] = 0
    by_niche["coverage_status"] = status_value(config, "wait_benchmark_raw")
    by_niche["coverage_reason"] = "MISSING_BENCHMARK_RAW"

    queue_frame = pd.DataFrame(
        columns=[
            "batch_id",
            "marketplace",
            "asin",
            "benchmark_cohort",
            "niche_leaf",
            "path_key",
            "download_type",
            "expected_input_folder",
            "next_step",
        ]
    )

    run_log = pd.DataFrame(
        [
            {
                "run_id": run_ctx.run_id,
                "started_at": now_local(),
                "finished_at": now_local(),
                "batch_id": batch_id,
                "input_m03_rows": len(shortlist),
                "benchmark_raw_count": 0,
                "status": status_value(config, "wait_benchmark_raw"),
                "reason": "No benchmark raw file matched the batch.",
            }
        ]
    )

    xlsx_path = step_dirs["xlsx"] / f"{OUTPUT_PREFIX}__{batch_id}.xlsx"
    csv_path = step_dirs["csv"] / f"{OUTPUT_PREFIX}__{batch_id}.csv"
    queue_path = step_dirs["queues"] / f"{QUEUE_PREFIX}__{batch_id}.csv"
    manifest_path = step_dirs["json"] / f"step2_manifest__{batch_id}.json"
    log_path = run_ctx.logs_root / f"step2_run_log__{batch_id}.json"

    write_workbook(
        xlsx_path,
        {
            "benchmark_asin_candidates": placeholder,
            "benchmark_by_niche": by_niche,
            "step2_run_log": run_log,
        },
        overwrite=overwrite,
    )
    write_csv(csv_path, placeholder, overwrite=overwrite)
    write_csv(queue_path, queue_frame, overwrite=overwrite)

    manifest = {
        "run_id": run_ctx.run_id,
        "step": STEP_NAME,
        "mode": run_ctx.mode,
        "batch_id": batch_id,
        "started_at": now_local(),
        "finished_at": now_local(),
        "status": status_value(config, "wait_benchmark_raw"),
        "input_rows": len(shortlist),
        "output_rows": len(placeholder),
        "outputs": {
            "m04_xlsx": str(xlsx_path),
            "m04_csv": str(csv_path),
            "reverse_keyword_queue": str(queue_path),
            "log_file": str(log_path),
        },
        "benchmark_raw_files": [],
        "reason": "No benchmark raw file matched the batch.",
    }
    write_json(manifest_path, manifest)
    dump_log(log_path, manifest)
    return {
        "batch_id": batch_id,
        "manifest": manifest,
        "m04_xlsx": str(xlsx_path),
        "m04_csv": str(csv_path),
        "queue_csv": str(queue_path),
        "log_file": str(log_path),
        "status_counts": {status_value(config, "wait_benchmark_raw"): len(placeholder)},
    }


def process_benchmark_raw(
    shortlist: pd.DataFrame,
    raw_files: list[Path],
    run_ctx,
    overwrite: bool,
    batch_id: str,
    config: dict[str, Any],
    weights_profile: dict[str, Any],
) -> dict[str, Any]:
    step_dirs = stage_dirs(run_ctx, STEP_NAME)
    required_paths = shortlist[shortlist["route_status"] == "PASS_TO_STEP2"].copy()
    raw_frames: list[pd.DataFrame] = []
    missing_aliases: list[str] = []
    for path in raw_files:
        standardized, missing = standardize_benchmark_raw(path)
        raw_frames.append(standardized)
        missing_aliases.extend(missing)
    combined = pd.concat(raw_frames, ignore_index=True) if raw_frames else pd.DataFrame()
    if combined.empty:
        return wait_outputs(shortlist, run_ctx, overwrite, batch_id, config)

    if "asin" not in combined.columns:
        combined["asin"] = ""
    combined["asin"] = combined["asin"].map(lambda value: str(value or "").upper())
    combined = combined[combined["asin"].astype(str).str.len() > 0].copy()

    if "path_key" not in combined.columns and len(required_paths["path_key"].dropna().unique()) == 1:
        combined["path_key"] = required_paths["path_key"].dropna().iloc[0]
    if "niche_leaf" not in combined.columns and len(required_paths["niche_leaf"].dropna().unique()) == 1:
        combined["niche_leaf"] = required_paths["niche_leaf"].dropna().iloc[0]
    if "marketplace" not in combined.columns and len(required_paths["marketplace"].dropna().unique()) == 1:
        combined["marketplace"] = required_paths["marketplace"].dropna().iloc[0]

    for field in ("monthly_sales_units", "monthly_revenue", "price", "review_count", "star_rating"):
        combined[f"{field}_num"] = combined[field].map(to_float) if field in combined.columns else None
    combined["listed_days_num"] = combined.apply(parse_listed_days, axis=1)

    if "path_key" in combined.columns:
        shortlist_map = required_paths[
            ["path_key", "batch_id", "marketplace", "dept_l1", "parent_l2", "parent_l3", "niche_leaf"]
        ].drop_duplicates()
        combined = combined.merge(shortlist_map, on="path_key", how="left", suffixes=("", "_m03"))
        for field in ("batch_id", "marketplace", "dept_l1", "parent_l2", "parent_l3", "niche_leaf"):
            if f"{field}_m03" in combined.columns:
                combined[field] = combined[field].where(combined[field].astype(str).str.strip() != "", combined[f"{field}_m03"])
                combined.drop(columns=[f"{field}_m03"], inplace=True)

    combined["batch_id"] = combined.get("batch_id", batch_id)
    combined["marketplace"] = combined.get("marketplace", required_paths["marketplace"].iloc[0] if not required_paths.empty else "")
    combined["niche_leaf"] = combined.get("niche_leaf", "")
    combined["path_key"] = combined.get("path_key", "")
    combined["dept_l1"] = combined.get("dept_l1", "")
    combined["parent_l2"] = combined.get("parent_l2", "")
    combined["parent_l3"] = combined.get("parent_l3", "")

    if "path_key" in combined.columns and combined["path_key"].astype(str).str.strip().any():
        combined["sales_rank_bucket"] = combined.groupby("path_key")["monthly_sales_units_num"].rank(method="first", ascending=False, pct=True)
    else:
        combined["sales_rank_bucket"] = combined["monthly_sales_units_num"].rank(method="first", ascending=False, pct=True)

    step2_cfg = config["step2"]
    price_pref = config["step1"]["preferred_window"].get("avg_price_usd", {})
    coverage_cfg = step2_cfg["coverage_requirement"]

    cohort_rows: list[dict[str, Any]] = []
    for _, row in combined.iterrows():
        sales = row.get("monthly_sales_units_num")
        reviews = row.get("review_count_num")
        price = row.get("price_num")
        stars = row.get("star_rating_num")
        listed_days = row.get("listed_days_num")
        rank_bucket = row.get("sales_rank_bucket")

        is_incumbent = bool(
            (sales is not None and sales >= step2_cfg["incumbent"]["monthly_sales_units"]["hard_min"])
            and (reviews is not None and reviews >= step2_cfg["incumbent"]["review_count"]["hard_min"])
            and (rank_bucket is not None and rank_bucket <= step2_cfg["incumbent"]["rank_quantile"])
        )
        is_new_winner = bool(
            (listed_days is not None and listed_days <= step2_cfg["new_winner"]["listed_within_days"]["hard_max"])
            and (sales is not None and sales >= step2_cfg["new_winner"]["monthly_sales_units"]["hard_min"])
            and (reviews is not None and reviews <= step2_cfg["new_winner"]["review_count"]["hard_max"])
            and (
                price is None
                or (
                    price_pref.get("preferred_min", 0) <= price <= price_pref.get("preferred_max", float("inf"))
                )
            )
        )
        is_underserved = bool(
            (sales is not None and sales >= step2_cfg["underserved_signal"]["monthly_sales_units"]["hard_min"])
            and (stars is not None and stars <= step2_cfg["underserved_signal"]["star_rating"]["hard_max"])
        )
        if is_new_winner:
            cohort = "NEW_WINNER"
        elif is_underserved:
            cohort = "UNDERSERVED_SIGNAL"
        elif is_incumbent:
            cohort = "INCUMBENT"
        else:
            cohort = "REVIEW"

        price_fit_score = 1.0 if price is None else bounded_score(
            price,
            preferred_min=price_pref.get("preferred_min"),
            preferred_max=price_pref.get("preferred_max"),
        )
        review_score = 0.0 if reviews is None else min(1.0, reviews / 300.0)
        star_score = 0.0 if stars is None else min(1.0, stars / 5.0)
        listed_score = 0.0 if listed_days is None else min(1.0, 180 / max(listed_days, 1))
        cohort_bonus = {"INCUMBENT": 0.8, "NEW_WINNER": 1.0, "UNDERSERVED_SIGNAL": 0.9, "REVIEW": 0.3}[cohort]

        weights = weights_profile["step2"]
        weighted = (
            weights["monthly_sales_units"] * bounded_score(sales, preferred_min=300)
            + weights["monthly_revenue"] * bounded_score(row.get("monthly_revenue_num"), preferred_min=3000)
            + weights["price_fit"] * price_fit_score
            + weights["review_count"] * review_score
            + weights["star_rating"] * star_score
            + weights["listed_days"] * listed_score
            + weights["cohort_bonus"] * cohort_bonus
        )
        total_weight = sum(weights.values())
        step2_score = round(weighted / total_weight, 4) if total_weight else 0.0

        row_dict = row.to_dict()
        row_dict["benchmark_cohort"] = cohort
        row_dict["step2_score"] = step2_score
        row_dict["step2_reason"] = unique_join(
            [
                "INCUMBENT_MATCH" if is_incumbent else "",
                "NEW_WINNER_MATCH" if is_new_winner else "",
                "UNDERSERVED_SIGNAL_MATCH" if is_underserved else "",
            ]
        )
        row_dict["is_new_winner"] = is_new_winner
        row_dict["is_underserved_signal"] = is_underserved
        row_dict["route_status"] = status_value(config, "pass_to_step3") if cohort != "REVIEW" else status_value(config, "review_buffer")
        row_dict["step2_status"] = row_dict["route_status"]
        row_dict["listed_days"] = listed_days
        cohort_rows.append(row_dict)

    candidates = pd.DataFrame(cohort_rows)
    candidates["step2_score"] = pd.to_numeric(candidates["step2_score"], errors="coerce")
    candidates["monthly_sales_units"] = candidates["monthly_sales_units_num"]
    candidates["monthly_revenue"] = candidates["monthly_revenue_num"]
    candidates["price"] = candidates["price_num"]
    candidates["review_count"] = candidates["review_count_num"]
    candidates["star_rating"] = candidates["star_rating_num"]

    by_niche = (
        candidates.groupby(["batch_id", "marketplace", "dept_l1", "parent_l2", "parent_l3", "niche_leaf", "path_key"], dropna=False)
        .agg(
            incumbent_count=("benchmark_cohort", lambda s: int((s == "INCUMBENT").sum())),
            new_winner_count=("benchmark_cohort", lambda s: int((s == "NEW_WINNER").sum())),
            underserved_count=("benchmark_cohort", lambda s: int((s == "UNDERSERVED_SIGNAL").sum())),
            candidate_count=("asin", "nunique"),
            avg_step2_score=("step2_score", "mean"),
        )
        .reset_index()
    )
    by_niche["coverage_status"] = by_niche["incumbent_count"].map(
        lambda value: status_value(config, "pass_to_step3") if value >= coverage_cfg["incumbent_min"] else status_value(config, "review_buffer")
    )
    by_niche["coverage_reason"] = by_niche["incumbent_count"].map(
        lambda value: "SUFFICIENT_BENCHMARK_COVERAGE" if value >= coverage_cfg["incumbent_min"] else "INSUFFICIENT_BENCHMARK_COVERAGE"
    )

    coverage_map = dict(zip(by_niche["path_key"], by_niche["coverage_status"]))
    reason_map = dict(zip(by_niche["path_key"], by_niche["coverage_reason"]))
    candidates["route_status"] = candidates["path_key"].map(coverage_map).fillna(status_value(config, "review_buffer"))
    candidates["step2_status"] = candidates["route_status"]
    candidates["step2_reason"] = candidates["path_key"].map(reason_map).fillna(candidates["step2_reason"])

    queue = candidates[candidates["route_status"] == "PASS_TO_STEP3"][
        ["batch_id", "marketplace", "asin", "benchmark_cohort", "niche_leaf", "path_key"]
    ].drop_duplicates()
    queue["download_type"] = step2_cfg["queue"]["download_type"]
    queue["expected_input_folder"] = step2_cfg["queue"]["expected_input_folder"]
    queue["next_step"] = step2_cfg["queue"]["next_step"]

    run_log = pd.DataFrame(
        [
            {
                "run_id": run_ctx.run_id,
                "started_at": now_local(),
                "finished_at": now_local(),
                "batch_id": batch_id,
                "input_m03_rows": len(shortlist),
                "benchmark_raw_count": len(raw_files),
                "candidate_rows": len(candidates),
                "pass_to_step3_rows": int((candidates["route_status"] == "PASS_TO_STEP3").sum()),
                "review_buffer_rows": int((candidates["route_status"] == "REVIEW_BUFFER").sum()),
                "missing_aliases": unique_join(missing_aliases),
            }
        ]
    )

    xlsx_path = step_dirs["xlsx"] / f"{OUTPUT_PREFIX}__{batch_id}.xlsx"
    csv_path = step_dirs["csv"] / f"{OUTPUT_PREFIX}__{batch_id}.csv"
    queue_path = step_dirs["queues"] / f"{QUEUE_PREFIX}__{batch_id}.csv"
    manifest_path = step_dirs["json"] / f"step2_manifest__{batch_id}.json"
    log_path = run_ctx.logs_root / f"step2_run_log__{batch_id}.json"

    workbook_frame = candidates[
        [
            "batch_id",
            "marketplace",
            "dept_l1",
            "parent_l2",
            "parent_l3",
            "niche_leaf",
            "path_key",
            "asin",
            "benchmark_cohort",
            "step2_score",
            "step2_status",
            "step2_reason",
            "listed_days",
            "monthly_sales_units",
            "monthly_revenue",
            "price",
            "review_count",
            "star_rating",
            "brand",
            "seller",
            "is_new_winner",
            "is_underserved_signal",
            "route_status",
            "raw_source_file",
        ]
    ].copy()

    write_workbook(
        xlsx_path,
        {
            "benchmark_asin_candidates": workbook_frame,
            "benchmark_by_niche": by_niche,
            "step2_run_log": run_log,
        },
        overwrite=overwrite,
    )
    write_csv(csv_path, workbook_frame, overwrite=overwrite)
    write_csv(queue_path, queue, overwrite=overwrite)

    manifest = {
        "run_id": run_ctx.run_id,
        "step": STEP_NAME,
        "mode": run_ctx.mode,
        "batch_id": batch_id,
        "started_at": now_local(),
        "finished_at": now_local(),
        "input_m03": str(shortlist.attrs.get("source_path", "")),
        "benchmark_raw_files": [str(path) for path in raw_files],
        "outputs": {
            "m04_xlsx": str(xlsx_path),
            "m04_csv": str(csv_path),
            "reverse_keyword_queue": str(queue_path),
            "log_file": str(log_path),
        },
        "row_input": len(shortlist),
        "row_output": len(workbook_frame),
        "status_counts": workbook_frame["route_status"].value_counts(dropna=False).to_dict(),
        "coverage_status_counts": by_niche["coverage_status"].value_counts(dropna=False).to_dict(),
        "missing_aliases": sorted(set(filter(None, missing_aliases))),
    }
    write_json(manifest_path, manifest)
    dump_log(log_path, manifest)
    return {
        "batch_id": batch_id,
        "manifest": manifest,
        "m04_xlsx": str(xlsx_path),
        "m04_csv": str(csv_path),
        "queue_csv": str(queue_path),
        "log_file": str(log_path),
        "status_counts": manifest["status_counts"],
    }


def run_step2(
    root: Path,
    run_id: str | None = None,
    mode: str = "balanced",
    batch_id: str | None = None,
    overwrite: bool = False,
    debug: bool = False,
) -> dict[str, Any]:
    skill_root = SCRIPT_DIR.parent
    bundle = load_config_bundle(skill_root, mode)
    config = bundle["config"]
    weights_profile = profile_weights(bundle["weights"], mode)
    selected_run_id = run_id or make_run_id()
    run_ctx = build_run_context(skill_root, root.resolve(), selected_run_id, mode, config)

    artifacts = scan_latest_stage_outputs(skill_root, INPUT_PREFIX, batch_id=batch_id or None)
    results: list[dict[str, Any]] = []
    warnings: list[str] = []
    for artifact in artifacts:
        shortlist = load_table(artifact.path, sheet_name="niche_candidates")
        shortlist.attrs["source_path"] = str(artifact.path)
        raw_files = find_inbox_raw_files(run_ctx.inbox_benchmark_root, batch_id=artifact.batch_id)
        if raw_files:
            results.append(process_benchmark_raw(shortlist, raw_files, run_ctx, overwrite, artifact.batch_id, config, weights_profile))
        else:
            results.append(wait_outputs(shortlist, run_ctx, overwrite, artifact.batch_id, config))
    if not results:
        warnings.append("No M03 shortlist files were found.")

    summary_path = summary_dir(run_ctx) / f"step2_summary__{run_ctx.run_id}.json"
    summary = {
        "run_id": run_ctx.run_id,
        "step": STEP_NAME,
        "mode": mode,
        "input_root": str(root.resolve()),
        "matched_m03_files": [str(artifact.path) for artifact in artifacts],
        "result_count": len(results),
        "warnings": warnings,
        "results": results,
    }
    write_json(summary_path, summary)
    write_json(run_ctx.manifest_root / f"step2_summary__{run_ctx.run_id}.json", summary)
    if debug:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    args = parse_args()
    summary = run_step2(
        root=Path(args.root),
        run_id=args.run_id or None,
        mode=args.mode,
        batch_id=args.batch_id or None,
        overwrite=args.overwrite,
        debug=args.debug,
    )
    print(f"[step2] run_id={summary['run_id']} matched={len(summary['matched_m03_files'])} results={summary['result_count']}")
    for result in summary["results"]:
        print(f"[step2] batch={result['batch_id']} m04={result['m04_xlsx']}")


if __name__ == "__main__":
    main()
