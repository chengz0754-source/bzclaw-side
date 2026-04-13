#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pipeline_common import (
    build_run_context,
    load_config_bundle,
    make_run_id,
    now_local,
    summary_dir,
    write_csv,
    write_json,
)
from run_step1_m03 import run_step1
from run_step2_benchmark import run_step2
from run_step3_keywords import run_step3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the SellerSprite market route pipeline from Step1 through Step3.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--start-step", choices=["step1", "step2", "step3"], default="step1")
    parser.add_argument("--mode", choices=["balanced", "new_seller", "low_competition", "opportunity", "manual_review_heavy"], default="balanced")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--m02-file", default="")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def summarize_outputs(run_id: str, step_summaries: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for step_name, summary in step_summaries.items():
        for result in summary.get("results", []):
            manifest = result.get("manifest", {})
            rows.append(
                {
                    "run_id": run_id,
                    "step": step_name,
                    "batch_id": result.get("batch_id", ""),
                    "status_counts": json.dumps(result.get("status_counts", {}), ensure_ascii=False),
                    "primary_output": result.get("m03_xlsx")
                    or result.get("m04_xlsx")
                    or result.get("k01_xlsx")
                    or "",
                    "secondary_output": result.get("queue_csv")
                    or result.get("k02_csv")
                    or "",
                    "log_file": result.get("log_file", ""),
                    "manifest_status": manifest.get("status", ""),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    skill_root = SCRIPT_DIR.parent
    bundle = load_config_bundle(skill_root, args.mode)
    config = bundle["config"]
    run_id = make_run_id()
    run_ctx = build_run_context(skill_root, root, run_id, args.mode, config)

    if args.dry_run:
        payload = {
            "run_id": run_id,
            "started_at": now_local(),
            "mode": args.mode,
            "root": str(root),
            "start_step": args.start_step,
            "batch_id": args.batch_id or "",
            "m02_file": args.m02_file or "",
            "note": "Dry run only. No step outputs were produced.",
        }
        write_json(summary_dir(run_ctx) / f"pipeline_dry_run__{run_id}.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    step_summaries: dict[str, dict[str, Any]] = {}
    started_at = now_local()

    if args.start_step == "step1":
        step_summaries["step1"] = run_step1(
            root=root,
            run_id=run_id,
            mode=args.mode,
            batch_id=args.batch_id or None,
            m02_file=Path(args.m02_file) if args.m02_file else None,
            overwrite=args.overwrite,
            debug=args.debug,
        )
        if step_summaries["step1"]["result_count"] > 0:
            step_summaries["step2"] = run_step2(
                root=root,
                run_id=run_id,
                mode=args.mode,
                batch_id=args.batch_id or None,
                overwrite=args.overwrite,
                debug=args.debug,
            )
            if step_summaries["step2"]["result_count"] > 0:
                step_summaries["step3"] = run_step3(
                    root=root,
                    run_id=run_id,
                    mode=args.mode,
                    batch_id=args.batch_id or None,
                    overwrite=args.overwrite,
                    debug=args.debug,
                )
    elif args.start_step == "step2":
        step_summaries["step2"] = run_step2(
            root=root,
            run_id=run_id,
            mode=args.mode,
            batch_id=args.batch_id or None,
            overwrite=args.overwrite,
            debug=args.debug,
        )
        if step_summaries["step2"]["result_count"] > 0:
            step_summaries["step3"] = run_step3(
                root=root,
                run_id=run_id,
                mode=args.mode,
                batch_id=args.batch_id or None,
                overwrite=args.overwrite,
                debug=args.debug,
            )
    else:
        step_summaries["step3"] = run_step3(
            root=root,
            run_id=run_id,
            mode=args.mode,
            batch_id=args.batch_id or None,
            overwrite=args.overwrite,
            debug=args.debug,
        )

    output_index = summarize_outputs(run_id, step_summaries)
    output_index_path = summary_dir(run_ctx) / "pipeline_output_index.csv"
    write_csv(output_index_path, output_index, overwrite=args.overwrite)

    finished_at = now_local()
    pipeline_manifest = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "root": str(root),
        "mode": args.mode,
        "start_step": args.start_step,
        "batch_id": args.batch_id or "",
        "selected_m02_file": args.m02_file or "",
        "output_index": str(output_index_path),
        "steps": step_summaries,
    }
    manifest_path = run_ctx.manifest_root / f"run_market_route_pipeline__{run_id}.json"
    write_json(manifest_path, pipeline_manifest)
    write_json(summary_dir(run_ctx) / f"run_market_route_pipeline__{run_id}.json", pipeline_manifest)

    print(f"[pipeline] run_id={run_id} mode={args.mode} start_step={args.start_step}")
    for step_name, summary in step_summaries.items():
        print(f"[pipeline] {step_name} matched={summary.get('result_count', 0)}")
    print(f"[pipeline] output_index={output_index_path}")
    print(f"[pipeline] manifest={manifest_path}")


if __name__ == "__main__":
    main()
