from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_observed_runtime_root() -> str:
    config_path = ROOT / "configs" / "paths.json"
    if not config_path.exists():
        return str(ROOT)
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return str(ROOT)
    return str(payload.get("project_root") or ROOT)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_within(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def path_scope(path: Path, run_dir: Path) -> str:
    resolved = path.resolve()
    if is_within(resolved, run_dir):
        return "run_local"
    if is_within(resolved, ROOT):
        ignored_roots = [
            ROOT / "outputs",
            ROOT / "logs",
            ROOT / "runs",
            ROOT / "playwright",
        ]
        if any(is_within(resolved, item) for item in ignored_roots):
            return "repo_local_ignored"
        return "repo_local_tracked"
    return "external_local"


def sensitivity(path: Path) -> str:
    resolved = path.resolve()
    if is_within(resolved, ROOT / "playwright" / "auth") or is_within(resolved, ROOT / "playwright" / "profiles"):
        return "sensitive_auth"
    if path_scope(resolved, ROOT / "outputs" / "selection_runs") in {"repo_local_ignored", "run_local"}:
        return "ignored_local_runtime"
    return "tracked_safe"


def category(path: Path, run_dir: Path) -> str:
    resolved = path.resolve()
    name = resolved.name.lower()
    suffix = resolved.suffix.lower()
    if name == "00_run_manifest.json":
        return "manifest"
    if name == "artifact_index.json":
        return "index"
    if name.endswith("_receipt.json") or name == "shadow_run_receipt.json" or is_within(resolved, run_dir / "03_logs" / "model_inference_receipts"):
        return "receipt"
    if name == "evidence_pack.json":
        return "receipt"
    if suffix == ".png" or suffix == ".jpg" or suffix == ".jpeg":
        return "screenshot"
    if suffix == ".zip" and "trace" in str(resolved).lower():
        return "trace"
    if suffix == ".xlsx":
        return "workbook"
    if is_within(resolved, ROOT / "playwright" / "auth") or is_within(resolved, ROOT / "playwright" / "profiles"):
        return "auth_state"
    if is_within(resolved, run_dir / "01_consumed_inputs"):
        return "input_snapshot"
    if is_within(resolved, run_dir / "03_logs"):
        return "log"
    if is_within(resolved, run_dir / "02_generated_outputs"):
        return "generated_output"
    return "other"


def content_role(path: Path, run_dir: Path) -> str:
    resolved = path.resolve()
    name = resolved.name.lower()
    suffix = resolved.suffix.lower()
    if name in {
        "00_run_manifest.json",
        "artifact_index.json",
        "evidence_pack.json",
        "shadow_run_receipt.json",
    } or is_within(resolved, run_dir / "03_logs" / "model_inference_receipts"):
        return "ingest_ready"
    if is_within(resolved, ROOT / "playwright" / "screenshots") or suffix == ".md":
        return "reviewable"
    if is_within(resolved, ROOT / "runs" / "manual") or is_within(resolved, ROOT / "playwright" / "traces"):
        return "raw"
    if is_within(resolved, run_dir / "03_logs") or "summary" in name or name.startswith("latest_"):
        return "summarized"
    if suffix == ".xlsx" or "_raw" in name or "原始" in resolved.name:
        return "raw"
    return "summarized"


def state_token_for(path: Path, run_dir: Path) -> str:
    file_sensitivity = sensitivity(path)
    if file_sensitivity == "sensitive_auth":
        return "SENSITIVE_LOCAL_ONLY"
    role = content_role(path, run_dir)
    if role == "ingest_ready":
        return "INGEST_READY"
    if role == "reviewable":
        return "REVIEWABLE"
    if role == "raw":
        return "CAPTURED_RAW"
    return "SUMMARIZED"


def artifact_id(path: Path) -> str:
    return repo_relative(path).replace("/", "__")


def entry_status(path: Path, default_status: str = "OBSERVED") -> str:
    return default_status


def make_artifact_entry(
    path: Path,
    run_dir: Path,
    *,
    object_mapping: str = "UNMAPPED_SUPPORTING_ASSET",
    producer_script: str,
    status: str = "OBSERVED",
    reason_code: str = "",
    verify_linkage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = path.resolve()
    size_bytes = resolved.stat().st_size if resolved.is_file() else None
    captured_at = datetime.fromtimestamp(resolved.stat().st_mtime).astimezone().isoformat(timespec="seconds")
    role = content_role(resolved, run_dir)
    return {
        "artifact_id": artifact_id(resolved),
        "logical_name": resolved.name,
        "object_mapping": object_mapping,
        "relative_path": repo_relative(resolved),
        "observed_absolute_path": str(resolved),
        "path_scope": path_scope(resolved, run_dir),
        "content_role": role,
        "category": category(resolved, run_dir),
        "sensitivity": sensitivity(resolved),
        "status": entry_status(resolved, status),
        "reason_code": reason_code,
        "state_token": state_token_for(resolved, run_dir),
        "producer_script": producer_script,
        "captured_at": captured_at,
        "size_bytes": size_bytes,
        "sha256": None,
        "review_ready": role in {"reviewable", "summarized", "ingest_ready"},
        "ingest_ready": role == "ingest_ready",
        "verify_linkage": verify_linkage or {},
    }


def dedupe_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        resolved = str(path.resolve())
        if resolved in seen or not path.exists() or not path.is_file():
            continue
        seen.add(resolved)
        result.append(path)
    return result


def write_artifact_index(
    run_dir: Path,
    *,
    producer_script: str,
    extra_paths: Iterable[Path] = (),
) -> tuple[Path, list[dict[str, Any]]]:
    generated_dir = run_dir / "02_generated_outputs"
    generated_dir.mkdir(parents=True, exist_ok=True)
    base_files = [
        path
        for path in generated_dir.rglob("*")
        if path.is_file() and path.name != "artifact_index.json"
    ]
    files = dedupe_paths([*base_files, *extra_paths])
    entries = [
        make_artifact_entry(
            path,
            run_dir,
            producer_script=producer_script,
        )
        for path in sorted(files)
    ]
    payload = {
        "schema_version": "b-side-artifact-index.v1",
        "batch_id": run_dir.name,
        "produced_at": iso_now(),
        "producer_script": producer_script,
        "entries": entries,
    }
    artifact_index_path = generated_dir / "artifact_index.json"
    write_json(artifact_index_path, payload)
    return artifact_index_path, entries


def write_evidence_pack(
    run_dir: Path,
    *,
    producer_script: str,
    evidence_paths: Iterable[Path],
    status: str,
    reason_code: str,
) -> tuple[Path, list[dict[str, Any]]]:
    logs_dir = run_dir / "03_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    files = dedupe_paths(evidence_paths)
    entries = [
        make_artifact_entry(
            path,
            run_dir,
            object_mapping="EvidencePack",
            producer_script=producer_script,
            status=status,
            reason_code=reason_code,
        )
        for path in sorted(files)
    ]
    payload = {
        "schema_version": "b-side-evidence-pack.v1",
        "object_name": "EvidencePack",
        "batch_id": run_dir.name,
        "status": status,
        "reason_code": reason_code,
        "state_token": "INGEST_READY" if entries else "BLOCKED",
        "produced_at": iso_now(),
        "producer_script": producer_script,
        "item_count": len(entries),
        "items": entries,
    }
    evidence_pack_path = logs_dir / "evidence_pack.json"
    write_json(evidence_pack_path, payload)
    return evidence_pack_path, entries


def write_shadow_run_receipt(
    run_dir: Path,
    *,
    producer_script: str,
    status: str,
    reason_code: str,
    dispatch_mode: str,
    execution_class: str,
) -> Path:
    logs_dir = run_dir / "03_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = logs_dir / "shadow_run_receipt.json"
    payload = {
        "schema_version": "b-side-shadow-run-receipt.v1",
        "object_name": "ShadowRunReceipt",
        "receipt_id": f"{run_dir.name}__shadow_receipt",
        "batch_id": run_dir.name,
        "dispatch_mode": dispatch_mode,
        "execution_class": execution_class,
        "status": status,
        "reason_code": reason_code,
        "state_token": "INGEST_READY" if status != "FAIL" else "BLOCKED",
        "produced_at": iso_now(),
        "producer_script": producer_script,
        "summary_ref": repo_relative(run_dir / "00_run_summary.md"),
        "logs_ref": repo_relative(run_dir / "03_logs"),
    }
    write_json(receipt_path, payload)
    return receipt_path


def write_run_manifest(
    run_dir: Path,
    *,
    producer_script: str,
    dispatch_mode: str,
    execution_class: str,
    status: str,
    reason_code: str,
    artifact_index_path: Path,
    evidence_pack_path: Path | None,
    model_receipt_paths: Iterable[Path] = (),
    shadow_run_receipt_path: Path | None = None,
    decision_draft_ref: str | None = None,
    notes: list[str] | None = None,
) -> Path:
    manifest_path = run_dir / "00_run_manifest.json"
    model_receipt_paths = list(model_receipt_paths)
    run_files = [
        path
        for path in run_dir.rglob("*")
        if path.is_file() and path.name != manifest_path.name
    ]
    entries: list[dict[str, Any]] = []
    for path in sorted(dedupe_paths(run_files)):
        object_mapping = "UNMAPPED_SUPPORTING_ASSET"
        if path == artifact_index_path or path == run_dir / "00_run_summary.md" or path == evidence_pack_path:
            object_mapping = "ArtifactReturnEnvelope" if path != evidence_pack_path else "EvidencePack"
        if shadow_run_receipt_path and path == shadow_run_receipt_path:
            object_mapping = "ShadowRunReceipt"
        if path in model_receipt_paths:
            object_mapping = "ModelInferenceReceipt"
        entries.append(
            make_artifact_entry(
                path,
                run_dir,
                object_mapping=object_mapping,
                producer_script=producer_script,
                status=status,
                reason_code=reason_code,
                verify_linkage={
                    "artifact_return_envelope_ref": repo_relative(manifest_path),
                    "evidence_pack_ref": repo_relative(evidence_pack_path) if evidence_pack_path else None,
                    "shadow_run_receipt_ref": repo_relative(shadow_run_receipt_path) if shadow_run_receipt_path else None,
                    "decision_draft_ref": decision_draft_ref,
                },
            )
        )
    payload = {
        "schema_version": "b-side-run-manifest.v1",
        "object_name": "ArtifactReturnEnvelope",
        "envelope_id": f"ARE__{run_dir.name}",
        "batch_id": run_dir.name,
        "dispatch_mode": dispatch_mode,
        "execution_class": execution_class,
        "status": status,
        "reason_code": reason_code,
        "state_token": "INGEST_READY" if artifact_index_path.exists() else "BLOCKED",
        "repo_alias_root": str(ROOT),
        "observed_runtime_root": read_observed_runtime_root(),
        "started_at": None,
        "finished_at": iso_now(),
        "produced_at": iso_now(),
        "producer": {
            "repo_name": ROOT.name,
            "script_or_entrypoint": producer_script,
            "host_role": "b_sidecar",
            "provider_name": None,
            "model_name": None,
        },
        "paths": {
            "run_dir": repo_relative(run_dir),
            "summary_md": repo_relative(run_dir / "00_run_summary.md"),
            "manifest_json": repo_relative(manifest_path),
            "consumed_inputs_dir": repo_relative(run_dir / "01_consumed_inputs"),
            "generated_outputs_dir": repo_relative(run_dir / "02_generated_outputs"),
            "logs_dir": repo_relative(run_dir / "03_logs"),
            "artifact_index_json": repo_relative(artifact_index_path),
        },
        "object_refs": {
            "evidence_pack_ref": repo_relative(evidence_pack_path) if evidence_pack_path else None,
            "model_inference_receipt_refs": [repo_relative(path) for path in model_receipt_paths],
            "shadow_run_receipt_ref": repo_relative(shadow_run_receipt_path) if shadow_run_receipt_path else None,
            "decision_draft_ref": decision_draft_ref,
        },
        "metadata_policy": {
            "path_reference_policy": "repo_relative_first",
            "sensitive_material_policy": "reference_only",
            "absolute_path_policy": "debug_only_optional",
        },
        "artifacts": entries,
        "notes": notes or [],
    }
    write_json(manifest_path, payload)
    return manifest_path
