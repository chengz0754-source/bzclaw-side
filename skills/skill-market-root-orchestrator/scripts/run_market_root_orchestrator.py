#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from select_latest_valid_m02 import select_latest_valid_m02


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = SKILL_ROOT / "configs" / "orchestrator_config.yaml"


def load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def make_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def root_market_files(root: Path, glob_pattern: str) -> list[Path]:
    return sorted([path for path in root.glob(glob_pattern) if path.is_file()])


def latest_processed_run_id(skill_root: Path) -> str:
    processed_root = skill_root / "archive" / "processed"
    if not processed_root.exists():
        return ""
    run_dirs = sorted([item.name for item in processed_root.iterdir() if item.is_dir()])
    return run_dirs[-1] if run_dirs else ""


def latest_step_run_id(skill_root: Path) -> str:
    outputs_root = skill_root / "outputs"
    if not outputs_root.exists():
        return ""
    run_dirs = sorted([item.name for item in outputs_root.iterdir() if item.is_dir()])
    return run_dirs[-1] if run_dirs else ""


def write_text(path: Path, value: str) -> None:
    ensure_dir(path.parent)
    path.write_text(value, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def subprocess_log_paths(run_id: str) -> dict[str, Path]:
    log_root = ensure_dir(SKILL_ROOT / "logs" / run_id)
    return {
        "root": log_root,
        "m01_stdout": log_root / "m01_to_m02.stdout.log",
        "m01_stderr": log_root / "m01_to_m02.stderr.log",
        "step_stdout": log_root / "step1_to_step3.stdout.log",
        "step_stderr": log_root / "step1_to_step3.stderr.log",
    }


def final_root_remaining_files(root: Path) -> list[str]:
    return sorted([path.name for path in root.iterdir() if path.is_file()])


def final_root_clean_flag(root: Path) -> bool:
    remaining = final_root_remaining_files(root)
    return not any(name.startswith("Market-research") or name.startswith("M02_") for name in remaining)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the root-dropzone SellerSprite market orchestrator.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--mode", default="")
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    root = Path(args.root).resolve()
    run_id = make_run_id()
    started_at = now_local()
    output_root = ensure_dir(SKILL_ROOT / "outputs" / run_id)
    archive_root = ensure_dir(SKILL_ROOT / "archive" / run_id)
    log_paths = subprocess_log_paths(run_id)

    m01_skill_root = root / config["skills"]["m01_to_m02"]["skill_dir"]
    m01_script = m01_skill_root / config["skills"]["m01_to_m02"]["script"]
    step_skill_root = root / config["skills"]["step1_to_step3"]["skill_dir"]
    step_script = step_skill_root / config["skills"]["step1_to_step3"]["script"]
    step_mode = args.mode or config["skills"]["step1_to_step3"]["default_mode"]

    root_inputs = root_market_files(root, config["root_input_glob"])
    m01_before_run = latest_processed_run_id(m01_skill_root)
    step_before_run = latest_step_run_id(step_skill_root)

    m01_returncode = None
    m01_run_id = ""
    if root_inputs:
        result = subprocess.run(
            [sys.executable, str(m01_script), "--input-dir", str(root)] + (["--overwrite"] if args.overwrite else []),
            text=True,
            capture_output=True,
            cwd=str(root),
        )
        m01_returncode = result.returncode
        write_text(log_paths["m01_stdout"], result.stdout)
        write_text(log_paths["m01_stderr"], result.stderr)
        m01_run_id = latest_processed_run_id(m01_skill_root)
    else:
        write_text(log_paths["m01_stdout"], "No Market-research*.xlsx files were found in root.\n")
        write_text(log_paths["m01_stderr"], "")

    selection_result = select_latest_valid_m02(root, batch_id=args.batch_id or None, config=config)
    selected_m02_file = selection_result.get("selected_m02_file", "")
    selected_quality_status = selection_result.get("selected_m02_quality_status", "BLOCK")
    quality_report = selection_result.get("quality_report", {})
    write_json(output_root / "selected_m02_quality_report.json", quality_report or selection_result)

    step_returncode = None
    step_run_id = ""
    step_manifest_path = ""
    if selection_result.get("selection_status") == "SELECTED" and selected_m02_file:
        result = subprocess.run(
            [
                sys.executable,
                str(step_script),
                "--root",
                str(root),
                "--mode",
                step_mode,
                "--m02-file",
                selected_m02_file,
            ]
            + (["--batch-id", args.batch_id] if args.batch_id else [])
            + (["--overwrite"] if args.overwrite else []),
            text=True,
            capture_output=True,
            cwd=str(root),
        )
        step_returncode = result.returncode
        write_text(log_paths["step_stdout"], result.stdout)
        write_text(log_paths["step_stderr"], result.stderr)
        step_run_id = latest_step_run_id(step_skill_root)
        if step_run_id:
            step_manifest_path = str(step_skill_root / "archive" / step_run_id / "manifests" / f"run_market_route_pipeline__{step_run_id}.json")
    else:
        write_text(log_paths["step_stdout"], "Blocked before Step1 because the selected M02 was not valid.\n")
        write_text(log_paths["step_stderr"], "")

    finished_at = now_local()
    remaining_files = final_root_remaining_files(root)
    clean_flag = final_root_clean_flag(root)

    status = "SUCCESS"
    if selection_result.get("selection_status") != "SELECTED":
        status = "BLOCKED"
    elif m01_returncode not in (None, 0):
        status = "FAILED"
    elif step_returncode not in (None, 0):
        status = "FAILED"
    elif not clean_flag:
        status = "PARTIAL"
    elif step_manifest_path and Path(step_manifest_path).exists():
        step_manifest = json.loads(Path(step_manifest_path).read_text(encoding="utf-8"))
        if any("WAIT_" in json.dumps(step_info, ensure_ascii=False) for step_info in step_manifest.get("steps", {}).values()):
            status = "PARTIAL"

    manifest = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "root_input_files": [str(path) for path in root_inputs],
        "m01_to_m02_run_id": m01_run_id,
        "selected_m02_file": selected_m02_file,
        "selected_m02_quality_status": selected_quality_status,
        "step1_to_step3_run_id": step_run_id,
        "final_root_clean_flag": clean_flag,
        "final_root_remaining_files": remaining_files,
        "status": status,
        "selection_status": selection_result.get("selection_status", ""),
        "m01_to_m02_stdout_log": str(log_paths["m01_stdout"]),
        "m01_to_m02_stderr_log": str(log_paths["m01_stderr"]),
        "step1_to_step3_stdout_log": str(log_paths["step_stdout"]),
        "step1_to_step3_stderr_log": str(log_paths["step_stderr"]),
        "quality_report": quality_report,
        "step_manifest_path": step_manifest_path,
        "previous_m01_run_id": m01_before_run,
        "previous_step_run_id": step_before_run,
    }
    manifest_path = output_root / "orchestrator_manifest.json"
    write_json(manifest_path, manifest)
    write_json(archive_root / "orchestrator_manifest.json", manifest)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if status in {"SUCCESS", "PARTIAL"} else 1


if __name__ == "__main__":
    sys.exit(main())
