#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pipeline_common import (
    Artifact,
    bounded_score,
    build_run_context,
    dump_log,
    load_config_bundle,
    load_table,
    make_run_id,
    now_local,
    path_flag,
    path_policy_mode,
    profile_weights,
    quantile_value,
    ratio_in_unit_interval,
    scan_latest_m02,
    stage_dirs,
    status_value,
    summary_dir,
    to_float,
    unique_join,
    write_csv,
    write_json,
    write_workbook,
)


STEP_NAME = "step1"
OUTPUT_PREFIX = "M03_niche_shortlist"
QUEUE_PREFIX = "benchmark_asin_download_queue"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Advance M02 market cleaned files into M03 niche shortlist.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--mode", default="balanced")
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--m02-file", default="")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def resolve_step1_config(config: dict[str, Any]) -> dict[str, Any]:
    step_cfg = deepcopy(config["step1"])
    preferred_overrides = step_cfg.pop("preferred_window_overrides", {})
    score_overrides = step_cfg.pop("score_threshold_overrides", {})
    if preferred_overrides:
        for metric, overrides in preferred_overrides.items():
            current = step_cfg["preferred_window"].setdefault(metric, {})
            current.update(overrides)
    if score_overrides:
        step_cfg["score_thresholds"].update(score_overrides)
    return step_cfg


def batch_quantile_snapshot(frame: pd.DataFrame, metrics: list[str]) -> dict[str, dict[str, float | None]]:
    snapshot: dict[str, dict[str, float | None]] = {}
    for metric in metrics:
        values = frame[metric] if metric in frame.columns else pd.Series(dtype=float)
        snapshot[metric] = {
            "q25": quantile_value(values, 0.25),
            "q50": quantile_value(values, 0.50),
            "q75": quantile_value(values, 0.75),
        }
    return snapshot


def path_scope_snapshot(frame: pd.DataFrame, metrics: list[str], group_fields: list[str]) -> dict[str, dict[str, dict[str, float | None]]]:
    snapshot: dict[str, dict[str, dict[str, float | None]]] = {}
    if not group_fields or any(field not in frame.columns for field in group_fields):
        return snapshot
    grouped = frame.groupby(group_fields, dropna=False)
    for keys, group in grouped:
        if not isinstance(keys, tuple):
            keys = (keys,)
        group_key = " > ".join(str(value or "").strip() for value in keys if str(value or "").strip())
        group_key = group_key or "UNSPECIFIED"
        snapshot[group_key] = batch_quantile_snapshot(group, metrics)
    return snapshot


def resolve_window(
    metric: str,
    spec: dict[str, Any],
    batch_stats: dict[str, dict[str, float | None]],
    path_stats: dict[str, dict[str, dict[str, float | None]]],
    path_scope_key: str,
) -> dict[str, float | None]:
    resolved = {
        "hard_min": spec.get("hard_min"),
        "hard_max": spec.get("hard_max"),
        "preferred_min": spec.get("preferred_min"),
        "preferred_max": spec.get("preferred_max"),
    }

    def apply_quantile(mode: str | None, stats: dict[str, float | None]) -> None:
        if not mode:
            return
        quantile_key = mode.split("_", 1)[0]
        metric_value = stats.get(quantile_key)
        if metric_value is None:
            return
        if mode.endswith("_floor"):
            current = resolved.get("preferred_min")
            resolved["preferred_min"] = metric_value if current is None else max(current, metric_value)
        elif mode.endswith("_ceiling"):
            current = resolved.get("preferred_max")
            resolved["preferred_max"] = metric_value if current is None else min(current, metric_value)

    apply_quantile(spec.get("batch_quantile_mode"), batch_stats.get(metric, {}))
    apply_quantile(spec.get("path_scope_quantile_mode"), path_stats.get(path_scope_key, {}).get(metric, {}))
    return resolved


def check_required_columns(frame: pd.DataFrame, required_fields: list[str]) -> list[str]:
    return [field for field in required_fields if field not in frame.columns]


def preflight_issues(row: pd.Series, step_cfg: dict[str, Any], missing_columns: list[str]) -> list[str]:
    issues: list[str] = []
    if missing_columns:
        issues.append(f"MISSING_COLUMNS:{','.join(missing_columns)}")
    for field in ("dept_l1", "parent_l2", "niche_leaf", "path_key"):
        if not str(row.get(field, "") or "").strip():
            issues.append(f"MISSING_PATH_FIELD:{field}")
    for field in (
        "monthly_sales_units",
        "avg_price_usd",
        "product_concentration",
        "new_product_share",
        "avg_gross_margin",
        "return_rate",
    ):
        if to_float(row.get(field)) is None:
            issues.append(f"MISSING_NUMERIC:{field}")
    for field in step_cfg.get("ratio_fields", []):
        if field in row.index and not ratio_in_unit_interval(row.get(field)):
            issues.append(f"INVALID_RATIO_SCALE:{field}")
    data_quality_flag = str(row.get("data_quality_flag", "") or "")
    if "FAIL" in data_quality_flag.upper() or "ERROR" in data_quality_flag.upper():
        issues.append(f"DATA_QUALITY_FLAG:{data_quality_flag}")
    return issues


def evaluate_hard_gate(row: pd.Series, step_cfg: dict[str, Any]) -> tuple[list[str], list[str]]:
    hits: list[str] = []
    misses: list[str] = []
    for metric, spec in step_cfg["hard_gate"].items():
        value = to_float(row.get(metric))
        hard_min = spec.get("hard_min")
        hard_max = spec.get("hard_max")
        if value is None:
            misses.append(f"{metric}:missing")
            continue
        if hard_min is not None and value < hard_min:
            misses.append(f"{metric}:lt:{hard_min}")
        elif hard_max is not None and value > hard_max:
            misses.append(f"{metric}:gt:{hard_max}")
        else:
            hits.append(metric)
    return hits, misses


def preferred_window_hits(
    row: pd.Series,
    step_cfg: dict[str, Any],
    batch_stats: dict[str, dict[str, float | None]],
    path_stats: dict[str, dict[str, dict[str, float | None]]],
) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    hits: list[str] = []
    misses: list[str] = []
    resolved_rows: list[dict[str, Any]] = []
    path_scope_key = " > ".join(str(row.get(field, "") or "").strip() for field in step_cfg.get("path_scope_group_fields", []))
    path_scope_key = path_scope_key or "UNSPECIFIED"
    for metric, spec in step_cfg["preferred_window"].items():
        resolved = resolve_window(metric, spec, batch_stats, path_stats, path_scope_key)
        value = to_float(row.get(metric))
        if value is None:
            misses.append(f"{metric}:missing")
        else:
            preferred_min = resolved.get("preferred_min")
            preferred_max = resolved.get("preferred_max")
            if preferred_min is not None and value < preferred_min:
                misses.append(f"{metric}:lt_pref:{round(preferred_min, 4)}")
            elif preferred_max is not None and value > preferred_max:
                misses.append(f"{metric}:gt_pref:{round(preferred_max, 4)}")
            else:
                hits.append(metric)
        resolved_rows.append(
            {
                "metric": metric,
                "hard_min": resolved.get("hard_min"),
                "hard_max": resolved.get("hard_max"),
                "preferred_min": resolved.get("preferred_min"),
                "preferred_max": resolved.get("preferred_max"),
            }
        )
    return hits, misses, resolved_rows


def score_step1_row(
    row: pd.Series,
    step_cfg: dict[str, Any],
    weights: dict[str, float],
    batch_stats: dict[str, dict[str, float | None]],
    path_stats: dict[str, dict[str, dict[str, float | None]]],
    path_fit_flag: str,
) -> float:
    path_scope_key = " > ".join(str(row.get(field, "") or "").strip() for field in step_cfg.get("path_scope_group_fields", []))
    path_scope_key = path_scope_key or "UNSPECIFIED"
    total_weight = 0.0
    weighted_score = 0.0
    for metric, weight in weights.items():
        if metric == "path_fit_flag":
            score = 0.0 if path_fit_flag.startswith("BLACKLIST") else 1.0 if path_fit_flag.startswith("ALLOW") else 0.4
        else:
            resolved = resolve_window(metric, step_cfg["preferred_window"].get(metric, {}), batch_stats, path_stats, path_scope_key)
            score = bounded_score(
                to_float(row.get(metric)),
                preferred_min=resolved.get("preferred_min"),
                preferred_max=resolved.get("preferred_max"),
                hard_min=resolved.get("hard_min"),
                hard_max=resolved.get("hard_max"),
            )
        total_weight += weight
        weighted_score += weight * score
    if not total_weight:
        return 0.0
    return round(weighted_score / total_weight, 4)


def build_path_summary(frame: pd.DataFrame) -> pd.DataFrame:
    summary_frames: list[pd.DataFrame] = []
    full = (
        frame.groupby(["dept_l1", "parent_l2", "parent_l3", "path_key"], dropna=False)
        .agg(
            niche_count=("niche_leaf", "nunique"),
            row_count=("niche_leaf", "size"),
            avg_step1_score=("step1_score", "mean"),
            total_monthly_sales_units=("monthly_sales_units_num", "sum"),
            avg_price_usd=("avg_price_usd_num", "mean"),
            avg_product_concentration=("product_concentration_num", "mean"),
            avg_new_product_share=("new_product_share_num", "mean"),
            pass_to_step2_count=("route_status", lambda series: int((series == "PASS_TO_STEP2").sum())),
            review_buffer_count=("route_status", lambda series: int((series == "REVIEW_BUFFER").sum())),
            drop_count=("route_status", lambda series: int((series == "DROP").sum())),
        )
        .reset_index()
    )
    full["summary_level"] = "full_path"
    summary_frames.append(full)

    parent = (
        frame.groupby(["dept_l1", "parent_l2"], dropna=False)
        .agg(
            niche_count=("niche_leaf", "nunique"),
            row_count=("niche_leaf", "size"),
            avg_step1_score=("step1_score", "mean"),
            total_monthly_sales_units=("monthly_sales_units_num", "sum"),
            avg_price_usd=("avg_price_usd_num", "mean"),
            avg_product_concentration=("product_concentration_num", "mean"),
            avg_new_product_share=("new_product_share_num", "mean"),
            pass_to_step2_count=("route_status", lambda series: int((series == "PASS_TO_STEP2").sum())),
            review_buffer_count=("route_status", lambda series: int((series == "REVIEW_BUFFER").sum())),
            drop_count=("route_status", lambda series: int((series == "DROP").sum())),
        )
        .reset_index()
    )
    parent["parent_l3"] = ""
    parent["path_key"] = parent["dept_l1"].fillna("") + " > " + parent["parent_l2"].fillna("")
    parent["summary_level"] = "dept_l1_parent_l2"
    summary_frames.append(parent)

    dept = (
        frame.groupby(["dept_l1"], dropna=False)
        .agg(
            niche_count=("niche_leaf", "nunique"),
            row_count=("niche_leaf", "size"),
            avg_step1_score=("step1_score", "mean"),
            total_monthly_sales_units=("monthly_sales_units_num", "sum"),
            avg_price_usd=("avg_price_usd_num", "mean"),
            avg_product_concentration=("product_concentration_num", "mean"),
            avg_new_product_share=("new_product_share_num", "mean"),
            pass_to_step2_count=("route_status", lambda series: int((series == "PASS_TO_STEP2").sum())),
            review_buffer_count=("route_status", lambda series: int((series == "REVIEW_BUFFER").sum())),
            drop_count=("route_status", lambda series: int((series == "DROP").sum())),
        )
        .reset_index()
    )
    dept["parent_l2"] = ""
    dept["parent_l3"] = ""
    dept["path_key"] = dept["dept_l1"]
    dept["summary_level"] = "dept_l1"
    summary_frames.append(dept)

    output = pd.concat(summary_frames, ignore_index=True)
    return output.sort_values(["summary_level", "total_monthly_sales_units"], ascending=[True, False]).reset_index(drop=True)


def build_window_snapshot(
    frame: pd.DataFrame,
    step_cfg: dict[str, Any],
    batch_stats: dict[str, dict[str, float | None]],
    run_id: str,
    mode: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for metric, spec in step_cfg["preferred_window"].items():
        rows.append(
            {
                "run_id": run_id,
                "mode": mode,
                "metric": metric,
                "hard_min": step_cfg["hard_gate"].get(metric, {}).get("hard_min"),
                "hard_max": step_cfg["hard_gate"].get(metric, {}).get("hard_max"),
                "preferred_min": spec.get("preferred_min"),
                "preferred_max": spec.get("preferred_max"),
                "batch_q25": batch_stats.get(metric, {}).get("q25"),
                "batch_q50": batch_stats.get(metric, {}).get("q50"),
                "batch_q75": batch_stats.get(metric, {}).get("q75"),
                "batch_quantile_mode": spec.get("batch_quantile_mode", ""),
                "path_scope_quantile_mode": spec.get("path_scope_quantile_mode", ""),
                "row_count": len(frame),
            }
        )
    return pd.DataFrame(rows)


def build_queue(frame: pd.DataFrame, step_cfg: dict[str, Any]) -> pd.DataFrame:
    eligible = frame[frame["route_status"] == "PASS_TO_STEP2"].copy()
    queue = eligible[
        ["batch_id", "marketplace", "dept_l1", "parent_l2", "parent_l3", "niche_leaf", "path_key"]
    ].drop_duplicates()
    queue["download_type"] = step_cfg["queue"]["download_type"]
    queue["expected_input_folder"] = step_cfg["queue"]["expected_input_folder"]
    queue["next_step"] = step_cfg["queue"]["next_step"]
    return queue.reset_index(drop=True)


def artifact_from_m02_file(path: Path) -> Artifact:
    if not path.exists():
        raise FileNotFoundError(f"M02 input file was not found: {path}")
    batch_id = path.stem.split("__", 2)[-1]
    run_id = path.parents[1].name if len(path.parents) >= 2 else "manual"
    return Artifact(batch_id=batch_id, run_id=run_id, path=path, format_name=path.suffix.lower().lstrip("."))


def process_m02_artifact(
    artifact: Artifact,
    run_ctx,
    config: dict[str, Any],
    weights_profile: dict[str, Any],
    path_policy: dict[str, Any],
    overwrite: bool,
) -> dict[str, Any]:
    step_cfg = resolve_step1_config(config)
    policy_mode = path_policy_mode(path_policy)
    step_dirs = stage_dirs(run_ctx, STEP_NAME)
    frame = load_table(artifact.path, sheet_name="market_cleaned")
    missing_columns = check_required_columns(frame, step_cfg["required_fields"])
    numeric_helper_fields = {
        "monthly_sales_units_num": "monthly_sales_units",
        "avg_price_usd_num": "avg_price_usd",
        "product_concentration_num": "product_concentration",
        "new_product_share_num": "new_product_share",
    }
    for helper_name, source_name in numeric_helper_fields.items():
        frame[helper_name] = frame[source_name].map(to_float) if source_name in frame.columns else None

    preferred_metrics = sorted(set(step_cfg["preferred_window"]).union(step_cfg["hard_gate"]))
    batch_stats = batch_quantile_snapshot(frame, preferred_metrics)
    path_stats = path_scope_snapshot(frame, preferred_metrics, step_cfg.get("path_scope_group_fields", []))

    output_records: list[dict[str, Any]] = []
    window_snapshot_rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        row_dict = row.to_dict()
        issues = preflight_issues(row, step_cfg, missing_columns)
        hard_hits, hard_misses = evaluate_hard_gate(row, step_cfg)
        preferred_hits, preferred_misses, resolved_rows = preferred_window_hits(row, step_cfg, batch_stats, path_stats)
        path_fit = path_flag(row.get("path_key", ""), row.get("dept_l1", ""), row.get("parent_l2", ""), path_policy)
        score = score_step1_row(row, step_cfg, weights_profile["step1"], batch_stats, path_stats, path_fit)

        if issues:
            route_status = status_value(config, "drop")
            drop_reason = unique_join(issues)
            pass_reason = ""
        elif policy_mode == "strict_include_only" and not path_fit.startswith("ALLOW"):
            route_status = status_value(config, "drop")
            drop_reason = unique_join(["DROP__PATH_POLICY", path_fit])
            pass_reason = ""
        elif hard_misses:
            route_status = status_value(config, "drop")
            drop_reason = unique_join(hard_misses)
            pass_reason = ""
        elif score >= step_cfg["score_thresholds"]["pass_to_step2"] and not path_fit.startswith("BLACKLIST"):
            route_status = status_value(config, "pass_to_step2")
            drop_reason = ""
            pass_reason = unique_join(["HARD_GATE_PASS", f"SCORE>={step_cfg['score_thresholds']['pass_to_step2']}"])
        elif config["pipeline"].get("review_buffer_enabled", True) and score >= step_cfg["score_thresholds"]["review_buffer"]:
            route_status = status_value(config, "review_buffer")
            drop_reason = ""
            pass_reason = "REVIEW_BUFFER_SCORE"
        else:
            route_status = status_value(config, "drop")
            drop_reason = unique_join(preferred_misses or ["LOW_SCORE"])
            pass_reason = ""

        next_action = {
            "PASS_TO_STEP2": "QUEUE_BENCHMARK_ASIN_DOWNLOAD",
            "REVIEW_BUFFER": "MANUAL_REVIEW_STEP1",
            "DROP": "HOLD",
        }.get(route_status, "HOLD")
        next_queue_required = route_status == "PASS_TO_STEP2"

        row_dict["step1_score"] = score
        row_dict["step1_status"] = route_status
        row_dict["step1_drop_reason"] = drop_reason
        row_dict["step1_pass_reason"] = pass_reason
        row_dict["path_fit_flag"] = path_fit
        row_dict["window_hits"] = unique_join(hard_hits + preferred_hits)
        row_dict["window_misses"] = unique_join(issues + hard_misses + preferred_misses)
        row_dict["next_action"] = next_action
        row_dict["next_queue_required"] = next_queue_required
        row_dict["route_status"] = route_status
        row_dict["pipeline_run_id"] = run_ctx.run_id
        output_records.append(row_dict)
        window_snapshot_rows.extend(resolved_rows)

    output_frame = pd.DataFrame(output_records)
    output_frame["step1_score"] = pd.to_numeric(output_frame["step1_score"], errors="coerce")
    output_frame["monthly_sales_units_num"] = pd.to_numeric(output_frame["monthly_sales_units_num"], errors="coerce")
    output_frame["avg_price_usd_num"] = pd.to_numeric(output_frame["avg_price_usd_num"], errors="coerce")
    output_frame["product_concentration_num"] = pd.to_numeric(output_frame["product_concentration_num"], errors="coerce")
    output_frame["new_product_share_num"] = pd.to_numeric(output_frame["new_product_share_num"], errors="coerce")

    queue_frame = build_queue(output_frame, step_cfg)
    path_summary_frame = build_path_summary(output_frame)
    window_snapshot_frame = build_window_snapshot(output_frame, step_cfg, batch_stats, run_ctx.run_id, run_ctx.mode)
    run_log_frame = pd.DataFrame(
        [
            {
                "run_id": run_ctx.run_id,
                "started_at": now_local(),
                "finished_at": now_local(),
                "mode": run_ctx.mode,
                "input_m02": str(artifact.path),
                "input_rows": len(frame),
                "output_rows": len(output_frame),
                "pass_to_step2_count": int((output_frame["route_status"] == "PASS_TO_STEP2").sum()),
                "review_buffer_count": int((output_frame["route_status"] == "REVIEW_BUFFER").sum()),
                "drop_count": int((output_frame["route_status"] == "DROP").sum()),
                "queue_rows": len(queue_frame),
                "missing_required_columns": unique_join(missing_columns),
                "path_policy_mode": policy_mode,
            }
        ]
    )

    batch_id = artifact.batch_id
    xlsx_path = step_dirs["xlsx"] / f"{OUTPUT_PREFIX}__{batch_id}.xlsx"
    csv_path = step_dirs["csv"] / f"{OUTPUT_PREFIX}__{batch_id}.csv"
    queue_path = step_dirs["queues"] / f"{QUEUE_PREFIX}__{batch_id}.csv"
    manifest_path = step_dirs["json"] / f"step1_manifest__{batch_id}.json"
    log_path = run_ctx.logs_root / f"step1_run_log__{batch_id}.json"

    workbook_frame = output_frame.drop(
        columns=["monthly_sales_units_num", "avg_price_usd_num", "product_concentration_num", "new_product_share_num"],
        errors="ignore",
    )
    write_workbook(
        xlsx_path,
        {
            "niche_candidates": workbook_frame,
            "path_summary": path_summary_frame,
            "window_snapshot": window_snapshot_frame,
            "step1_run_log": run_log_frame,
        },
        overwrite=overwrite,
    )
    write_csv(csv_path, workbook_frame, overwrite=overwrite)
    write_csv(queue_path, queue_frame, overwrite=overwrite)

    manifest = {
        "run_id": run_ctx.run_id,
        "step": STEP_NAME,
        "mode": run_ctx.mode,
        "batch_id": batch_id,
        "started_at": now_local(),
        "finished_at": now_local(),
        "input_m02": str(artifact.path),
        "outputs": {
            "m03_xlsx": str(xlsx_path),
            "m03_csv": str(csv_path),
            "benchmark_queue_csv": str(queue_path),
            "log_file": str(log_path),
        },
        "row_input": len(frame),
        "row_output": len(output_frame),
        "status_counts": output_frame["route_status"].value_counts(dropna=False).to_dict(),
        "missing_required_columns": missing_columns,
        "path_policy_mode": policy_mode,
        "path_summary_levels": sorted(path_summary_frame["summary_level"].dropna().unique().tolist()),
    }
    write_json(manifest_path, manifest)
    dump_log(
        log_path,
        {
            "run_id": run_ctx.run_id,
            "batch_id": batch_id,
            "missing_required_columns": missing_columns,
            "status_counts": manifest["status_counts"],
            "queue_rows": len(queue_frame),
            "path_fit_flags": output_frame["path_fit_flag"].value_counts(dropna=False).to_dict(),
        },
    )
    return {
        "batch_id": batch_id,
        "manifest": manifest,
        "m03_xlsx": str(xlsx_path),
        "m03_csv": str(csv_path),
        "queue_csv": str(queue_path),
        "log_file": str(log_path),
        "status_counts": manifest["status_counts"],
        "queue_rows": len(queue_frame),
    }


def run_step1(
    root: Path,
    run_id: str | None = None,
    mode: str = "balanced",
    batch_id: str | None = None,
    m02_file: Path | None = None,
    overwrite: bool = False,
    debug: bool = False,
) -> dict[str, Any]:
    skill_root = SCRIPT_DIR.parent
    bundle = load_config_bundle(skill_root, mode)
    config = bundle["config"]
    weights_profile = profile_weights(bundle["weights"], mode)
    selected_run_id = run_id or make_run_id()
    run_ctx = build_run_context(skill_root, root.resolve(), selected_run_id, mode, config)
    artifacts = [artifact_from_m02_file(m02_file.resolve())] if m02_file else scan_latest_m02(root.resolve(), config, batch_id=batch_id or None)
    results: list[dict[str, Any]] = []
    warnings: list[str] = []
    for artifact in artifacts:
        results.append(
            process_m02_artifact(
                artifact=artifact,
                run_ctx=run_ctx,
                config=config,
                weights_profile=weights_profile,
                path_policy=bundle["path_policy"],
                overwrite=overwrite,
            )
        )
    if not results:
        warnings.append("No upstream M02 files were found.")

    summary_path = summary_dir(run_ctx) / f"step1_summary__{run_ctx.run_id}.json"
    summary = {
        "run_id": run_ctx.run_id,
        "step": STEP_NAME,
        "mode": mode,
        "input_root": str(root.resolve()),
        "explicit_m02_file": str(m02_file.resolve()) if m02_file else "",
        "matched_m02_files": [str(artifact.path) for artifact in artifacts],
        "result_count": len(results),
        "warnings": warnings,
        "results": results,
    }
    write_json(summary_path, summary)
    write_json(run_ctx.manifest_root / f"step1_summary__{run_ctx.run_id}.json", summary)
    if debug:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    args = parse_args()
    summary = run_step1(
        root=Path(args.root),
        run_id=args.run_id or None,
        mode=args.mode,
        batch_id=args.batch_id or None,
        m02_file=Path(args.m02_file) if args.m02_file else None,
        overwrite=args.overwrite,
        debug=args.debug,
    )
    print(f"[step1] run_id={summary['run_id']} matched={len(summary['matched_m02_files'])} results={summary['result_count']}")
    for result in summary["results"]:
        print(f"[step1] batch={result['batch_id']} queue_rows={result['queue_rows']} m03={result['m03_xlsx']}")


if __name__ == "__main__":
    main()
