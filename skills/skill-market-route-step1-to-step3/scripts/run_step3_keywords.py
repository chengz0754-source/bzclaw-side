#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
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
    normalize_token,
    normalize_text,
    now_local,
    parse_ratio,
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


STEP_NAME = "step3"
INPUT_PREFIX = "M04_benchmark_asin_scored"
OUTPUT_PREFIX = "K01_keyword_pool"
SHORTLIST_PREFIX = "K02_keyword_shortlist"

KEYWORD_ALIASES = {
    "keyword_raw": ["keyword", "search term", "关键词", "keyword text"],
    "search_volume": ["search volume", "searches", "月搜索量", "搜索量"],
    "traffic_share": ["traffic share", "traffic percentage", "流量占比"],
    "asin": ["asin", "parent asin", "父asin", "商品asin"],
    "source_tool": ["source tool", "tool", "数据源"],
    "path_key": ["path key", "market path", "市场路径", "类目路径"],
    "niche_leaf": ["niche leaf", "niche", "细分市场", "市场"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Advance benchmark ASIN evidence into keyword pool and shortlist.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--mode", default="balanced")
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def standardize_keyword_raw(path: Path) -> tuple[pd.DataFrame, list[str]]:
    frame = load_table(path)
    standardized, _, missing = alias_lookup(frame, KEYWORD_ALIASES)
    if "asin" not in standardized.columns:
        standardized["asin"] = standardized.apply(lambda row: infer_asin_from_text(" ".join(str(value or "") for value in row.values)), axis=1)
    if "source_tool" not in standardized.columns:
        source_tool = "reverse_asin" if "reverse" in path.stem.casefold() else "keyword_raw"
        standardized["source_tool"] = source_tool
    standardized["raw_source_file"] = path.name
    return standardized, missing


def keyword_normalized(value: Any) -> str:
    text = normalize_text(value).casefold()
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def infer_keyword_type(keyword: str, brand_risk: bool, niche_tokens: set[str]) -> str:
    if brand_risk:
        return "brand"
    words = keyword.split()
    if niche_tokens and any(token in niche_tokens for token in words):
        return "niche_core"
    if len(words) >= 3:
        return "long_tail"
    if len(words) == 2:
        return "mid_tail"
    return "head_term"


def wait_outputs(
    benchmark_frame: pd.DataFrame,
    run_ctx,
    overwrite: bool,
    batch_id: str,
    config: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    step_dirs = stage_dirs(run_ctx, STEP_NAME)
    wait_status = status_value(config, "wait_keyword_raw")
    placeholder = pd.DataFrame(
        [
            {
                "batch_id": batch_id,
                "keyword_raw": "",
                "keyword_normalized": "",
                "source_tools": "",
                "supporting_asin_count": 0,
                "supporting_incumbent_count": 0,
                "supporting_new_winner_count": 0,
                "supporting_underserved_count": 0,
                "niche_count": int(benchmark_frame["niche_leaf"].dropna().nunique()) if "niche_leaf" in benchmark_frame.columns else 0,
                "path_keys": unique_join(benchmark_frame.get("path_key", pd.Series(dtype=str)).dropna().tolist()) if not benchmark_frame.empty else "",
                "search_volume": None,
                "traffic_share_sum": None,
                "traffic_share_max": None,
                "has_brand_risk": False,
                "keyword_type": "",
                "exclude_flag": False,
                "exclude_reason": "",
                "step3_score": 0.0,
                "step3_status": wait_status,
                "step3_reason": reason,
                "route_status": wait_status,
            }
        ]
    )
    keyword_by_asin = pd.DataFrame(columns=["batch_id", "asin", "keyword_raw", "keyword_normalized", "source_tool", "path_key", "niche_leaf"])
    keyword_by_niche = pd.DataFrame(columns=["batch_id", "path_key", "niche_leaf", "keyword_count", "pass_ready_for_sif_count", "review_buffer_count", "drop_count"])
    shortlist = pd.DataFrame(columns=["batch_id", "keyword_normalized", "step3_score", "step3_status", "step3_reason", "route_status"])
    run_log = pd.DataFrame(
        [
            {
                "run_id": run_ctx.run_id,
                "started_at": now_local(),
                "finished_at": now_local(),
                "batch_id": batch_id,
                "input_m04_rows": len(benchmark_frame),
                "keyword_raw_count": 0,
                "status": wait_status,
                "reason": reason,
            }
        ]
    )

    xlsx_path = step_dirs["xlsx"] / f"{OUTPUT_PREFIX}__{batch_id}.xlsx"
    shortlist_path = step_dirs["csv"] / f"{SHORTLIST_PREFIX}__{batch_id}.csv"
    manifest_path = step_dirs["json"] / f"step3_manifest__{batch_id}.json"
    log_path = run_ctx.logs_root / f"step3_run_log__{batch_id}.json"

    write_workbook(
        xlsx_path,
        {
            "keyword_pool": placeholder,
            "keyword_by_asin": keyword_by_asin,
            "keyword_by_niche": keyword_by_niche,
            "step3_run_log": run_log,
        },
        overwrite=overwrite,
    )
    write_csv(shortlist_path, shortlist, overwrite=overwrite)

    manifest = {
        "run_id": run_ctx.run_id,
        "step": STEP_NAME,
        "mode": run_ctx.mode,
        "batch_id": batch_id,
        "started_at": now_local(),
        "finished_at": now_local(),
        "status": wait_status,
        "reason": reason,
        "outputs": {
            "k01_xlsx": str(xlsx_path),
            "k02_csv": str(shortlist_path),
            "log_file": str(log_path),
        },
        "keyword_raw_files": [],
    }
    write_json(manifest_path, manifest)
    dump_log(log_path, manifest)
    return {
        "batch_id": batch_id,
        "manifest": manifest,
        "k01_xlsx": str(xlsx_path),
        "k02_csv": str(shortlist_path),
        "log_file": str(log_path),
        "status_counts": {wait_status: 1},
    }


def process_keyword_raw(
    benchmark_frame: pd.DataFrame,
    raw_files: list[Path],
    run_ctx,
    overwrite: bool,
    batch_id: str,
    config: dict[str, Any],
    weights_profile: dict[str, Any],
) -> dict[str, Any]:
    step_dirs = stage_dirs(run_ctx, STEP_NAME)
    ready_asins = benchmark_frame[benchmark_frame["route_status"] == "PASS_TO_STEP3"].copy()
    raw_frames: list[pd.DataFrame] = []
    missing_aliases: list[str] = []
    for path in raw_files:
        standardized, missing = standardize_keyword_raw(path)
        raw_frames.append(standardized)
        missing_aliases.extend(missing)
    combined = pd.concat(raw_frames, ignore_index=True) if raw_frames else pd.DataFrame()
    if combined.empty or ready_asins.empty:
        reason = "NO_READY_BENCHMARK_ASINS" if ready_asins.empty else "MISSING_KEYWORD_RAW"
        return wait_outputs(benchmark_frame, run_ctx, overwrite, batch_id, config, reason)

    combined["asin"] = combined.get("asin", "").map(lambda value: str(value or "").upper())
    combined["keyword_normalized"] = combined.get("keyword_raw", "").map(keyword_normalized)
    combined["search_volume_num"] = combined.get("search_volume", "").map(to_float)
    combined["traffic_share_num"] = combined.get("traffic_share", "").map(parse_ratio)
    combined = combined[combined["keyword_normalized"].astype(str).str.len() > 0].copy()

    benchmark_map = ready_asins[
        ["asin", "benchmark_cohort", "brand", "path_key", "niche_leaf", "batch_id", "marketplace", "step2_status"]
    ].drop_duplicates()
    combined = combined.merge(benchmark_map, on="asin", how="left", suffixes=("", "_m04"))
    combined["batch_id"] = combined.get("batch_id", batch_id)
    combined["benchmark_cohort"] = combined.get("benchmark_cohort", "")
    combined["path_key"] = combined.get("path_key", "")
    combined["niche_leaf"] = combined.get("niche_leaf", "")

    brand_tokens: set[str] = set()
    for brand in ready_asins.get("brand", pd.Series(dtype=str)).fillna(""):
        for token in keyword_normalized(brand).split():
            if len(token) >= 3:
                brand_tokens.add(token)

    niche_tokens: set[str] = set()
    for text in ready_asins.get("niche_leaf", pd.Series(dtype=str)).fillna(""):
        for token in keyword_normalized(text).split():
            if len(token) >= 3:
                niche_tokens.add(token)

    min_len = config["step3"]["exclude"]["min_keyword_length"]
    combined["has_brand_risk"] = combined["keyword_normalized"].map(
        lambda value: any(token in brand_tokens for token in value.split())
    )
    combined["keyword_type"] = combined.apply(
        lambda row: infer_keyword_type(row["keyword_normalized"], bool(row["has_brand_risk"]), niche_tokens),
        axis=1,
    )
    combined["exclude_flag"] = combined["keyword_normalized"].map(lambda value: len(value) < min_len) | combined["has_brand_risk"]
    combined["exclude_reason"] = combined.apply(
        lambda row: unique_join(
            [
                "BRAND_RISK" if row["has_brand_risk"] else "",
                "TOO_SHORT" if len(row["keyword_normalized"]) < min_len else "",
                "NO_READY_ASIN_MATCH" if not str(row.get("asin", "")).strip() else "",
            ]
        ),
        axis=1,
    )

    keyword_by_asin = combined[
        [
            "batch_id",
            "asin",
            "keyword_raw",
            "keyword_normalized",
            "source_tool",
            "benchmark_cohort",
            "path_key",
            "niche_leaf",
            "search_volume_num",
            "traffic_share_num",
            "raw_source_file",
        ]
    ].copy()
    keyword_by_asin.rename(
        columns={"search_volume_num": "search_volume", "traffic_share_num": "traffic_share"},
        inplace=True,
    )

    grouped_rows: list[dict[str, Any]] = []
    for keyword, group in combined.groupby("keyword_normalized", dropna=False):
        supporting_asin_count = int(group["asin"].astype(str).str.strip().replace("", pd.NA).dropna().nunique())
        supporting_incumbent_count = int(group.loc[group["benchmark_cohort"] == "INCUMBENT", "asin"].nunique())
        supporting_new_winner_count = int(group.loc[group["benchmark_cohort"] == "NEW_WINNER", "asin"].nunique())
        supporting_underserved_count = int(group.loc[group["benchmark_cohort"] == "UNDERSERVED_SIGNAL", "asin"].nunique())
        search_volume = float(group["search_volume_num"].dropna().max()) if group["search_volume_num"].dropna().any() else None
        traffic_sum = float(group["traffic_share_num"].dropna().sum()) if group["traffic_share_num"].dropna().any() else None
        traffic_max = float(group["traffic_share_num"].dropna().max()) if group["traffic_share_num"].dropna().any() else None
        has_brand_risk = bool(group["has_brand_risk"].fillna(False).any())
        exclude_flag = bool(group["exclude_flag"].fillna(False).any())
        keyword_type = group["keyword_type"].dropna().astype(str).mode().iloc[0] if not group["keyword_type"].dropna().empty else ""
        weights = weights_profile["step3"]
        positive_weight_total = (
            weights["supporting_asin_count"]
            + weights["supporting_incumbent_count"]
            + weights["supporting_new_winner_count"]
            + weights["supporting_underserved_count"]
            + weights["search_volume"]
            + weights["traffic_share_sum"]
            + weights["traffic_share_max"]
            + weights["niche_count"]
        )
        raw_score = (
            weights["supporting_asin_count"] * min(1.0, supporting_asin_count / 3.0)
            + weights["supporting_incumbent_count"] * min(1.0, supporting_incumbent_count / 2.0)
            + weights["supporting_new_winner_count"] * min(1.0, supporting_new_winner_count / 2.0)
            + weights["supporting_underserved_count"] * min(1.0, supporting_underserved_count / 2.0)
            + weights["search_volume"] * bounded_score(search_volume, preferred_min=config["step3"]["shortlist_rules"]["search_volume_floor"])
            + weights["traffic_share_sum"] * bounded_score(traffic_sum, preferred_min=0.05)
            + weights["traffic_share_max"] * bounded_score(traffic_max, preferred_min=0.02)
            + weights["niche_count"] * bounded_score(float(group["niche_leaf"].dropna().nunique()), preferred_min=1.0, preferred_max=3.0)
        )
        if has_brand_risk:
            raw_score = max(0.0, raw_score - weights["brand_risk_penalty"])
        step3_score = round(raw_score / positive_weight_total, 4) if positive_weight_total else 0.0

        rule_cfg = config["step3"]["shortlist_rules"]
        passes_shortlist = (
            supporting_asin_count >= rule_cfg["supporting_asin_count_min"]
            or (supporting_incumbent_count >= 1 and supporting_new_winner_count >= 1)
            or ((search_volume or 0) >= rule_cfg["search_volume_floor"] and supporting_asin_count >= 1)
        )
        if exclude_flag:
            route_status = status_value(config, "drop")
            step3_reason = unique_join([group["exclude_reason"].iloc[0], "EXCLUDE"])
        elif passes_shortlist:
            route_status = status_value(config, "pass_ready_for_sif")
            step3_reason = "DATA_RULE_PASS"
        else:
            route_status = status_value(config, "review_buffer")
            step3_reason = "INSUFFICIENT_KEYWORD_SUPPORT"

        grouped_rows.append(
            {
                "batch_id": batch_id,
                "keyword_raw": group["keyword_raw"].dropna().astype(str).iloc[0] if not group["keyword_raw"].dropna().empty else "",
                "keyword_normalized": keyword,
                "source_tools": unique_join(group["source_tool"].tolist()),
                "supporting_asin_count": supporting_asin_count,
                "supporting_incumbent_count": supporting_incumbent_count,
                "supporting_new_winner_count": supporting_new_winner_count,
                "supporting_underserved_count": supporting_underserved_count,
                "niche_count": int(group["niche_leaf"].dropna().nunique()),
                "path_keys": unique_join(group["path_key"].tolist()),
                "search_volume": search_volume,
                "traffic_share_sum": traffic_sum,
                "traffic_share_max": traffic_max,
                "has_brand_risk": has_brand_risk,
                "keyword_type": keyword_type,
                "exclude_flag": exclude_flag,
                "exclude_reason": unique_join(group["exclude_reason"].tolist()),
                "step3_score": step3_score,
                "step3_status": route_status,
                "step3_reason": step3_reason,
                "route_status": route_status,
            }
        )

    keyword_pool = pd.DataFrame(grouped_rows).sort_values(["step3_score", "supporting_asin_count"], ascending=[False, False]).reset_index(drop=True)
    keyword_by_niche = (
        keyword_pool.assign(path_key=keyword_pool["path_keys"])
        .groupby(["batch_id", "path_key"], dropna=False)
        .agg(
            keyword_count=("keyword_normalized", "nunique"),
            pass_ready_for_sif_count=("route_status", lambda s: int((s == "PASS_READY_FOR_SIF").sum())),
            review_buffer_count=("route_status", lambda s: int((s == "REVIEW_BUFFER").sum())),
            drop_count=("route_status", lambda s: int((s == "DROP").sum())),
        )
        .reset_index()
    )
    keyword_by_niche["niche_leaf"] = ""

    shortlist = keyword_pool[keyword_pool["route_status"] == "PASS_READY_FOR_SIF"][
        ["batch_id", "keyword_normalized", "step3_score", "step3_status", "step3_reason", "route_status"]
    ].copy()

    run_log = pd.DataFrame(
        [
            {
                "run_id": run_ctx.run_id,
                "started_at": now_local(),
                "finished_at": now_local(),
                "batch_id": batch_id,
                "input_m04_rows": len(benchmark_frame),
                "keyword_raw_count": len(raw_files),
                "keyword_pool_rows": len(keyword_pool),
                "shortlist_rows": len(shortlist),
                "missing_aliases": unique_join(sorted(set(filter(None, missing_aliases)))),
            }
        ]
    )

    xlsx_path = step_dirs["xlsx"] / f"{OUTPUT_PREFIX}__{batch_id}.xlsx"
    shortlist_path = step_dirs["csv"] / f"{SHORTLIST_PREFIX}__{batch_id}.csv"
    manifest_path = step_dirs["json"] / f"step3_manifest__{batch_id}.json"
    log_path = run_ctx.logs_root / f"step3_run_log__{batch_id}.json"

    write_workbook(
        xlsx_path,
        {
            "keyword_pool": keyword_pool,
            "keyword_by_asin": keyword_by_asin,
            "keyword_by_niche": keyword_by_niche,
            "step3_run_log": run_log,
        },
        overwrite=overwrite,
    )
    write_csv(shortlist_path, shortlist, overwrite=overwrite)

    manifest = {
        "run_id": run_ctx.run_id,
        "step": STEP_NAME,
        "mode": run_ctx.mode,
        "batch_id": batch_id,
        "started_at": now_local(),
        "finished_at": now_local(),
        "input_m04": str(benchmark_frame.attrs.get("source_path", "")),
        "keyword_raw_files": [str(path) for path in raw_files],
        "outputs": {
            "k01_xlsx": str(xlsx_path),
            "k02_csv": str(shortlist_path),
            "log_file": str(log_path),
        },
        "row_input": len(benchmark_frame),
        "keyword_pool_rows": len(keyword_pool),
        "shortlist_rows": len(shortlist),
        "status_counts": keyword_pool["route_status"].value_counts(dropna=False).to_dict(),
        "missing_aliases": sorted(set(filter(None, missing_aliases))),
    }
    write_json(manifest_path, manifest)
    dump_log(log_path, manifest)
    return {
        "batch_id": batch_id,
        "manifest": manifest,
        "k01_xlsx": str(xlsx_path),
        "k02_csv": str(shortlist_path),
        "log_file": str(log_path),
        "status_counts": manifest["status_counts"],
    }


def run_step3(
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
        benchmark_frame = load_table(artifact.path, sheet_name="benchmark_asin_candidates")
        benchmark_frame.attrs["source_path"] = str(artifact.path)
        raw_files = find_inbox_raw_files(run_ctx.inbox_keyword_root, batch_id=artifact.batch_id)
        if raw_files:
            results.append(process_keyword_raw(benchmark_frame, raw_files, run_ctx, overwrite, artifact.batch_id, config, weights_profile))
        else:
            reason = "MISSING_KEYWORD_RAW" if not benchmark_frame.empty else "NO_STEP2_OUTPUT_ROWS"
            results.append(wait_outputs(benchmark_frame, run_ctx, overwrite, artifact.batch_id, config, reason))
    if not results:
        warnings.append("No M04 benchmark files were found.")

    summary_path = summary_dir(run_ctx) / f"step3_summary__{run_ctx.run_id}.json"
    summary = {
        "run_id": run_ctx.run_id,
        "step": STEP_NAME,
        "mode": mode,
        "input_root": str(root.resolve()),
        "matched_m04_files": [str(artifact.path) for artifact in artifacts],
        "result_count": len(results),
        "warnings": warnings,
        "results": results,
    }
    write_json(summary_path, summary)
    write_json(run_ctx.manifest_root / f"step3_summary__{run_ctx.run_id}.json", summary)
    if debug:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    args = parse_args()
    summary = run_step3(
        root=Path(args.root),
        run_id=args.run_id or None,
        mode=args.mode,
        batch_id=args.batch_id or None,
        overwrite=args.overwrite,
        debug=args.debug,
    )
    print(f"[step3] run_id={summary['run_id']} matched={len(summary['matched_m04_files'])} results={summary['result_count']}")
    for result in summary["results"]:
        print(f"[step3] batch={result['batch_id']} k01={result['k01_xlsx']}")


if __name__ == "__main__":
    main()
