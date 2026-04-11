#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from validate_m02_quality import validate_m02_file


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR.parent / "configs" / "orchestrator_config.yaml"


def load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def collect_success_candidates(root: Path, config: dict[str, Any], batch_id: str | None = None) -> list[dict[str, Any]]:
    skill_dir = root / config["skills"]["m01_to_m02"]["skill_dir"]
    processed_root = skill_dir / "archive" / "processed"
    candidates: list[dict[str, Any]] = []
    for manifest_path in processed_root.glob("*/manifests/run_manifest.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        run_id = str(manifest.get("run_id") or manifest_path.parent.parent.name)
        for file_record in manifest.get("files", []):
            if file_record.get("status") != "success":
                continue
            output_csv = str(file_record.get("output_csv") or "")
            if not output_csv:
                continue
            output_path = Path(output_csv)
            if not output_path.exists():
                continue
            record_batch_id = str(file_record.get("batch_id") or output_path.stem.split("__", 2)[-1])
            if batch_id and record_batch_id != batch_id:
                continue
            candidates.append(
                {
                    "run_id": run_id,
                    "manifest_path": str(manifest_path),
                    "file_record": file_record,
                    "output_csv": str(output_path),
                    "batch_id": record_batch_id,
                }
            )
    return sorted(candidates, key=lambda item: (item["run_id"], item["output_csv"]), reverse=True)


def select_latest_valid_m02(root: Path, batch_id: str | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or load_config()
    candidates = collect_success_candidates(root.resolve(), config, batch_id=batch_id)
    if not candidates:
        return {
            "selection_status": "M02_NOT_FOUND",
            "selected_m02_file": "",
            "selected_m02_quality_status": "BLOCK",
            "block_reasons": ["NO_MANIFEST_APPROVED_M02_FOUND"],
        }

    latest_run_id = candidates[0]["run_id"]
    latest_candidates = [candidate for candidate in candidates if candidate["run_id"] == latest_run_id]
    if batch_id is None and len(latest_candidates) > 1:
        return {
            "selection_status": "M02_MULTI_FILE_LATEST_RUN",
            "selected_m02_file": "",
            "selected_m02_quality_status": "BLOCK",
            "latest_run_id": latest_run_id,
            "block_reasons": ["MULTIPLE_M02_FILES_IN_LATEST_RUN_USE_BATCH_ID"],
            "latest_candidates": latest_candidates,
        }

    candidate = latest_candidates[0]
    quality_report = validate_m02_file(Path(candidate["output_csv"]).resolve(), config=config)
    accepted_statuses = set(config["validation"]["accepted_quality_statuses"])
    if quality_report["quality_status"] not in accepted_statuses:
        return {
            "selection_status": "M02_QUALITY_BLOCK",
            "selected_m02_file": str(candidate["output_csv"]),
            "selected_m02_quality_status": quality_report["quality_status"],
            "latest_run_id": latest_run_id,
            "quality_report": quality_report,
            "block_reasons": quality_report["block_reasons"],
        }
    return {
        "selection_status": "SELECTED",
        "selected_m02_file": str(candidate["output_csv"]),
        "selected_m02_quality_status": quality_report["quality_status"],
        "latest_run_id": latest_run_id,
        "quality_report": quality_report,
        "manifest_path": candidate["manifest_path"],
        "batch_id": candidate["batch_id"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select the newest manifest-approved and quality-valid M02 file.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = select_latest_valid_m02(Path(args.root), batch_id=args.batch_id or None)
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
