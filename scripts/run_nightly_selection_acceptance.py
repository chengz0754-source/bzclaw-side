from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from output_envelope_common import (
    write_artifact_index,
    write_evidence_pack,
    write_run_manifest,
    write_shadow_run_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = ROOT / "outputs" / "selection_runs"
CURRENT_INPUT_DIR = ROOT / "inputs" / "selection_run_current"
PYTHON_EXE = ROOT / ".venv" / "Scripts" / "python.exe"
GLOBAL_KEYWORD_LOG = ROOT / "logs" / "keyword_chain" / "latest_keyword_build_run.json"
GLOBAL_SIF_LOG_DIR = ROOT / "logs" / "sif_surfaces"
PROTECTED_INPUT_NAMES = {".gitkeep"}


class NightlyAcceptanceError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a non-destructive end-to-end nightly acceptance dry-run and assemble a full archive-shaped package."
    )
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--row-indices", default=None)
    return parser.parse_args()


def ensure_within_repo(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise NightlyAcceptanceError(f"{label} is outside the repo root: {resolved}")
    return resolved


def python_command() -> str:
    if PYTHON_EXE.exists():
        return str(PYTHON_EXE)
    return sys.executable


def run_python(args: list[str], timeout_seconds: int = 1200) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [python_command(), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        check=False,
    )


def copy_current_inputs(destination_dir: Path) -> list[str]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for item in sorted(CURRENT_INPUT_DIR.iterdir()):
        if item.name in PROTECTED_INPUT_NAMES:
            continue
        target = destination_dir / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
        copied.append(item.name)
    return copied


def latest_matching(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def copy_file_if_exists(source: Path, destination_dir: Path) -> str | None:
    if not source.exists():
        return None
    destination_dir.mkdir(parents=True, exist_ok=True)
    target = destination_dir / source.name
    shutil.copy2(source, target)
    return str(target)


def required_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise NightlyAcceptanceError(f"Missing required {label}: {path}")
    return path


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def summarize_step(step: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"- step: `{step['name']}`",
            f"  - exit_code: `{step['exit_code']}`",
            f"  - status: `{step['status']}`",
            f"  - reason_code: `{step['reason_code']}`",
            f"  - command: `{step['command']}`",
        ]
    )


def main() -> int:
    args = parse_args()
    batch_id = str(args.batch_id or f"{datetime.now().strftime('%Y%m%d')}_p10_acceptance")
    run_dir = ensure_within_repo(OUTPUTS_ROOT / batch_id, "run_dir")
    if run_dir.exists():
        raise NightlyAcceptanceError(f"Acceptance run dir already exists: {run_dir}")

    consumed_dir = ensure_within_repo(run_dir / "01_consumed_inputs", "consumed_dir")
    generated_dir = ensure_within_repo(run_dir / "02_generated_outputs", "generated_dir")
    logs_dir = ensure_within_repo(run_dir / "03_logs", "logs_dir")
    for path in (consumed_dir, generated_dir, logs_dir):
        path.mkdir(parents=True, exist_ok=True)

    copied_inputs = copy_current_inputs(consumed_dir)
    steps: list[dict[str, Any]] = []

    batch_command = [
        "scripts/run_selection_direction_batch.py",
        "--batch-id",
        batch_id,
        "--output-dir",
        str(generated_dir),
        "--log-dir",
        str(logs_dir / "direction_batch"),
        "--trigger-market-dry-run",
        "--trigger-benchmark-live",
        "--trigger-benchmark-build",
    ]
    if args.row_indices:
        batch_command.extend(["--row-indices", str(args.row_indices)])
    batch_completed = run_python(batch_command, timeout_seconds=1500)
    batch_summary_path = required_file(generated_dir / "batch_run_summary.json", "batch summary")
    batch_summary = json.loads(batch_summary_path.read_text(encoding="utf-8"))
    steps.append(
        {
            "name": "direction_batch",
            "command": " ".join(batch_command),
            "exit_code": batch_completed.returncode,
            "status": str(batch_summary.get("status", "")).strip(),
            "reason_code": str(batch_summary.get("reason_code", "")).strip(),
            "summary_path": str(batch_summary_path),
        }
    )

    candidate_command = [
        "scripts/build_candidate_pool.py",
        "--batch-id",
        batch_id,
        "--batch-summary",
        str(batch_summary_path),
        "--queue-csv",
        str(generated_dir / "batch_queue_status.csv"),
        "--output-dir",
        str(generated_dir),
        "--log-dir",
        str(logs_dir / "candidate_pool"),
    ]
    candidate_completed = run_python(candidate_command, timeout_seconds=600)
    candidate_summary_path = required_file(generated_dir / "candidate_pool_summary.json", "candidate pool summary")
    candidate_summary = json.loads(candidate_summary_path.read_text(encoding="utf-8"))
    candidate_pool_path = required_file(latest_matching(generated_dir, "60_*.csv") or generated_dir / "60_missing.csv", "candidate pool csv")
    steps.append(
        {
            "name": "candidate_pool",
            "command": " ".join(candidate_command),
            "exit_code": candidate_completed.returncode,
            "status": str(candidate_summary.get("status", "")).strip(),
            "reason_code": str(candidate_summary.get("reason_code", "")).strip(),
            "summary_path": str(candidate_summary_path),
        }
    )

    sif_detail_command = [
        "scripts/collect_sif_detail_surface.py",
        "--candidate-pool-csv",
        str(candidate_pool_path),
        "--candidate-index",
        "1",
        "--output-dir",
        str(generated_dir),
    ]
    sif_detail_completed = run_python(sif_detail_command, timeout_seconds=900)
    sif_detail_json = required_file(generated_dir / "sif_detail_surface_probe.json", "sif detail json")
    sif_detail_summary = json.loads(sif_detail_json.read_text(encoding="utf-8"))
    steps.append(
        {
            "name": "sif_detail_probe",
            "command": " ".join(sif_detail_command),
            "exit_code": sif_detail_completed.returncode,
            "status": str(sif_detail_summary.get("status", "")).strip(),
            "reason_code": str(sif_detail_summary.get("reason_code", "")).strip(),
            "summary_path": str(sif_detail_json),
        }
    )

    sif_search_command = [
        "scripts/collect_sif_search_surface.py",
        "--candidate-pool-csv",
        str(candidate_pool_path),
        "--candidate-index",
        "1",
        "--output-dir",
        str(generated_dir),
    ]
    sif_search_completed = run_python(sif_search_command, timeout_seconds=900)
    sif_search_json = required_file(generated_dir / "sif_search_surface_probe.json", "sif search json")
    sif_search_summary = json.loads(sif_search_json.read_text(encoding="utf-8"))
    steps.append(
        {
            "name": "sif_search_probe",
            "command": " ".join(sif_search_command),
            "exit_code": sif_search_completed.returncode,
            "status": str(sif_search_summary.get("status", "")).strip(),
            "reason_code": str(sif_search_summary.get("reason_code", "")).strip(),
            "summary_path": str(sif_search_json),
        }
    )

    copy_file_if_exists(GLOBAL_KEYWORD_LOG, logs_dir / "keyword_chain")
    for latest_name in ["latest_bootstrap_run.json", "latest_detail_run.json", "latest_search_run.json"]:
        copy_file_if_exists(GLOBAL_SIF_LOG_DIR / latest_name, logs_dir / "sif_surfaces")

    sif_enrichment_command = [
        "scripts/build_sif_enrichment_daytime_pack.py",
        "--batch-id",
        batch_id,
        "--candidate-pool-csv",
        str(candidate_pool_path),
        "--candidate-pool-summary",
        str(candidate_summary_path),
        "--detail-csv",
        str(required_file(generated_dir / "50_SIF流量结构补强.csv", "50 csv")),
        "--detail-json",
        str(sif_detail_json),
        "--search-51-csv",
        str(required_file(generated_dir / "51_SIF关键词价值补强.csv", "51 csv")),
        "--search-52-csv",
        str(required_file(generated_dir / "52_SIF广告结构补强.csv", "52 csv")),
        "--search-json",
        str(sif_search_json),
        "--queue-csv",
        str(required_file(generated_dir / "batch_queue_status.csv", "batch queue")),
        "--output-dir",
        str(generated_dir),
        "--log-dir",
        str(logs_dir / "sif_enrichment"),
    ]
    sif_enrichment_completed = run_python(sif_enrichment_command, timeout_seconds=900)
    sif_enrichment_summary_path = required_file(generated_dir / "sif_enrichment_daytime_pack_summary.json", "sif enrichment summary")
    sif_enrichment_summary = json.loads(sif_enrichment_summary_path.read_text(encoding="utf-8"))
    steps.append(
        {
            "name": "sif_enrichment",
            "command": " ".join(sif_enrichment_command),
            "exit_code": sif_enrichment_completed.returncode,
            "status": str(sif_enrichment_summary.get("status", "")).strip(),
            "reason_code": str(sif_enrichment_summary.get("reason_code", "")).strip(),
            "summary_path": str(sif_enrichment_summary_path),
        }
    )

    required_outputs = [
        "batch_queue_status.csv",
        "batch_run_summary.json",
        "03_候选市场与候选品初筛池.csv",
        "60_候选样品池.csv",
        "50_SIF流量结构补强.csv",
        "51_SIF关键词价值补强.csv",
        "52_SIF广告结构补强.csv",
        "53_SIF补强下推结果.csv",
        "61_待供应链核利清单.csv",
    ]
    output_presence = {name: (generated_dir / name).exists() for name in required_outputs}
    archive_structure = {
        "00_run_summary_md": False,
        "01_consumed_inputs": consumed_dir.exists(),
        "02_generated_outputs": generated_dir.exists(),
        "03_logs": logs_dir.exists(),
    }

    overall_status = "PASS"
    reason_codes: list[str] = []
    for step in steps:
        if step["status"] != "PASS":
            overall_status = "HOLD"
            reason_codes.append(str(step["reason_code"]))
    if not all(output_presence.values()):
        overall_status = "FAIL"
        reason_codes.append("REQUIRED_OUTPUT_MISSING")

    summary = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "module": "nightly_selection_acceptance",
        "batch_id": batch_id,
        "status": overall_status,
        "reason_code": "; ".join(dict.fromkeys(reason_codes)) or "PASS",
        "run_dir": str(run_dir),
        "copied_inputs": copied_inputs,
        "steps": steps,
        "required_outputs": output_presence,
        "archive_structure": archive_structure,
    }

    summary_md = [
        "# Nightly Selection Acceptance Run",
        "",
        f"- batch_id: `{batch_id}`",
        f"- status: `{summary['status']}`",
        f"- reason_code: `{summary['reason_code']}`",
        f"- run_dir: `{run_dir}`",
        "",
        "## Copied Inputs",
        "",
    ]
    summary_md.extend([f"- `{name}`" for name in copied_inputs] or ["- none"])
    summary_md.extend(["", "## Steps", ""])
    summary_md.extend([summarize_step(step) for step in steps])
    summary_md.extend(["", "## Required Outputs", ""])
    summary_md.extend([f"- `{name}` => `{present}`" for name, present in output_presence.items()])
    summary_md.extend(["", "## Archive Structure", ""])
    summary_md.extend([f"- `{name}` => `{present}`" for name, present in archive_structure.items()])

    write_json(logs_dir / "nightly_acceptance_summary.json", summary)
    write_text(run_dir / "00_run_summary.md", "\n".join(summary_md) + "\n")

    archive_structure["00_run_summary_md"] = True
    summary["archive_structure"] = archive_structure
    write_json(logs_dir / "nightly_acceptance_summary.json", summary)

    artifact_index_path, _ = write_artifact_index(
        run_dir,
        producer_script="scripts/run_nightly_selection_acceptance.py",
    )
    evidence_paths = [run_dir / "00_run_summary.md", logs_dir / "nightly_acceptance_summary.json"]
    evidence_paths.extend(
        path
        for path in generated_dir.rglob("*")
        if path.is_file()
    )
    evidence_paths.extend(
        path
        for path in logs_dir.rglob("*")
        if path.is_file() and path.name not in {"evidence_pack.json", "shadow_run_receipt.json"}
    )
    evidence_pack_path, _ = write_evidence_pack(
        run_dir,
        producer_script="scripts/run_nightly_selection_acceptance.py",
        evidence_paths=evidence_paths,
        status=summary["status"],
        reason_code=summary["reason_code"],
    )
    shadow_run_receipt_path = write_shadow_run_receipt(
        run_dir,
        producer_script="scripts/run_nightly_selection_acceptance.py",
        status=summary["status"],
        reason_code=summary["reason_code"],
        dispatch_mode="shadow",
        execution_class="dry_run",
    )
    write_run_manifest(
        run_dir,
        producer_script="scripts/run_nightly_selection_acceptance.py",
        dispatch_mode="shadow",
        execution_class="dry_run",
        status=summary["status"],
        reason_code=summary["reason_code"],
        artifact_index_path=artifact_index_path,
        evidence_pack_path=evidence_pack_path,
        shadow_run_receipt_path=shadow_run_receipt_path,
        notes=[
            "Nightly acceptance remains a dry-run package and is not business closure.",
            "ModelInferenceReceipt refs stay empty when no model call receipt was emitted.",
        ],
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if overall_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
