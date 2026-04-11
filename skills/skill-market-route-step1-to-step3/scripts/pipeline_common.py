#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


@dataclass
class Artifact:
    batch_id: str
    run_id: str
    path: Path
    format_name: str
    manifest_path: Path | None = None


@dataclass
class RunContext:
    skill_root: Path
    root: Path
    run_id: str
    mode: str
    outputs_root: Path
    logs_root: Path
    archive_root: Path
    manifest_root: Path
    inbox_benchmark_root: Path
    inbox_keyword_root: Path


INPUT_FORMAT_PRIORITY = {"csv": 0, "xlsx": 1, "jsonl": 2}


def make_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def slugify(value: Any, separator: str = "_") -> str:
    text = str(value or "").strip()
    text = re.sub(r"[^A-Za-z0-9]+", separator, text)
    text = re.sub(fr"{re.escape(separator)}+", separator, text)
    return text.strip(separator).lower() or "unknown"


def normalize_text(value: Any) -> str:
    text = str(value or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_token(value: Any) -> str:
    text = normalize_text(value).casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return normalize_text(value).casefold() in {"1", "true", "yes", "y"}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def deep_update(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = deepcopy(value)
    return base


def load_config_bundle(skill_root: Path, mode: str) -> dict[str, Any]:
    config = read_yaml(skill_root / "configs" / "market_route_pipeline_config.yaml")
    weights = read_yaml(skill_root / "configs" / "score_weights.yaml")
    path_policy = read_yaml(skill_root / "configs" / "path_policy.yaml")
    merged = deepcopy(config)
    mode_updates = config.get("modes", {}).get(mode, {})
    if mode_updates:
        deep_update(merged, mode_updates)
    return {"config": merged, "weights": weights, "path_policy": path_policy}


def profile_weights(weights_config: dict[str, Any], mode: str) -> dict[str, Any]:
    profiles = weights_config.get("profiles", {})
    return deepcopy(profiles.get(mode) or profiles.get("balanced") or {})


def build_run_context(skill_root: Path, root: Path, run_id: str, mode: str, config: dict[str, Any]) -> RunContext:
    pipeline = config["pipeline"]
    outputs_root = ensure_dir(skill_root / pipeline.get("outputs_dir", "outputs") / run_id)
    logs_root = ensure_dir(skill_root / pipeline.get("logs_dir", "logs") / run_id)
    archive_root = ensure_dir(skill_root / pipeline.get("archive_dir", "archive") / run_id)
    manifest_root = ensure_dir(archive_root / "manifests")
    inbox_benchmark_root = ensure_dir(skill_root / pipeline["inbox"]["benchmark_raw"])
    inbox_keyword_root = ensure_dir(skill_root / pipeline["inbox"]["keyword_raw"])
    return RunContext(
        skill_root=skill_root,
        root=root,
        run_id=run_id,
        mode=mode,
        outputs_root=outputs_root,
        logs_root=logs_root,
        archive_root=archive_root,
        manifest_root=manifest_root,
        inbox_benchmark_root=inbox_benchmark_root,
        inbox_keyword_root=inbox_keyword_root,
    )


def stage_dirs(run_ctx: RunContext, step_name: str) -> dict[str, Path]:
    base = ensure_dir(run_ctx.outputs_root / step_name)
    return {
        "base": base,
        "xlsx": ensure_dir(base / "xlsx"),
        "csv": ensure_dir(base / "csv"),
        "json": ensure_dir(base / "json"),
        "queues": ensure_dir(base / "queues"),
    }


def summary_dir(run_ctx: RunContext) -> Path:
    return ensure_dir(run_ctx.outputs_root / "summaries")


def status_value(config: dict[str, Any], key: str) -> str:
    return config["pipeline"]["statuses"][key]


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = normalize_text(value)
    if not text:
        return None
    for token in (",", "$", "%", "\u00a0", "\u00a5", "\uffe5", "\u00a3", "\u20ac"):
        text = text.replace(token, "")
    try:
        return float(text)
    except ValueError:
        return None


def ratio_in_unit_interval(value: Any) -> bool:
    parsed = to_float(value)
    if parsed is None:
        return True
    return 0.0 <= parsed <= 1.0


def parse_ratio(value: Any) -> float | None:
    parsed = to_float(value)
    if parsed is None:
        return None
    if parsed > 1 and parsed <= 100:
        return parsed / 100.0
    return parsed


def unique_join(values: list[Any], separator: str = " | ") -> str:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = normalize_text(value)
        if text and text not in seen:
            seen.add(text)
            cleaned.append(text)
    return separator.join(cleaned)


def unique_list(values: list[Any]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = normalize_text(value)
        if text and text not in seen:
            seen.add(text)
            cleaned.append(text)
    return cleaned


def load_table(path: Path, sheet_name: str | int | None = None) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    elif suffix == ".xlsx":
        frame = pd.read_excel(path, sheet_name=sheet_name or 0, dtype=str)
    elif suffix == ".jsonl":
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if text:
                    rows.append(json.loads(text))
        frame = pd.DataFrame(rows)
    else:
        raise ValueError(f"Unsupported input format: {path}")
    frame = frame.replace({pd.NA: None})
    frame = frame.where(pd.notnull(frame), None)
    for column in frame.columns:
        frame[column] = frame[column].map(lambda value: normalize_text(value) if isinstance(value, str) else value)
    return frame


def write_workbook(path: Path, sheets: dict[str, pd.DataFrame], overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists and --overwrite was not set: {path}")
    ensure_dir(path.parent)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)


def write_csv(path: Path, frame: pd.DataFrame, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists and --overwrite was not set: {path}")
    ensure_dir(path.parent)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_jsonl(path: Path, frame: pd.DataFrame, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists and --overwrite was not set: {path}")
    ensure_dir(path.parent)
    frame.to_json(path, orient="records", lines=True, force_ascii=False)


def batch_id_from_output_name(path: Path, prefix: str) -> str:
    stem = path.stem
    if stem.startswith(prefix):
        return stem[len(prefix) :]
    return slugify(stem)


def prefer_latest_artifacts(candidates: list[Artifact]) -> list[Artifact]:
    selected: dict[str, Artifact] = {}
    for artifact in candidates:
        current = selected.get(artifact.batch_id)
        if current is None:
            selected[artifact.batch_id] = artifact
            continue
        current_key = (current.run_id, -INPUT_FORMAT_PRIORITY.get(current.format_name, 9))
        artifact_key = (artifact.run_id, -INPUT_FORMAT_PRIORITY.get(artifact.format_name, 9))
        if artifact_key > current_key:
            selected[artifact.batch_id] = artifact
    return [selected[key] for key in sorted(selected)]


def manifest_approved_m02_candidates(root: Path, config: dict[str, Any], batch_id: str | None = None) -> list[Artifact]:
    upstream = config["pipeline"]["upstream"]
    skill_root = root / upstream["m02_skill_dir"]
    processed_root = skill_root / "archive" / "processed"
    if not processed_root.exists():
        return []
    candidates: list[Artifact] = []
    for manifest_path in processed_root.glob("*/manifests/run_manifest.json"):
        manifest = read_json(manifest_path)
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
            parsed_batch_id = str(file_record.get("batch_id") or output_path.stem.split("__", 2)[-1])
            if batch_id and parsed_batch_id != batch_id:
                continue
            candidates.append(
                Artifact(
                    batch_id=parsed_batch_id,
                    run_id=run_id,
                    path=output_path,
                    format_name=output_path.suffix.lower().lstrip("."),
                    manifest_path=manifest_path,
                )
            )
    return prefer_latest_artifacts(candidates)


def scan_latest_m02(root: Path, config: dict[str, Any], batch_id: str | None = None) -> list[Artifact]:
    manifest_candidates = manifest_approved_m02_candidates(root, config, batch_id=batch_id)
    if manifest_candidates:
        return manifest_candidates

    upstream = config["pipeline"]["upstream"]
    outputs_root = root / upstream["m02_skill_dir"] / upstream.get("m02_outputs_dir", "outputs")
    if not outputs_root.exists():
        return []
    candidates: list[Artifact] = []
    for run_dir in sorted([item for item in outputs_root.iterdir() if item.is_dir()], key=lambda p: p.name):
        run_id = run_dir.name
        for format_name, suffix in (("csv", ".csv"), ("xlsx", ".xlsx"), ("jsonl", ".jsonl")):
            format_dir = run_dir / format_name
            if not format_dir.exists():
                continue
            for path in format_dir.glob(f"M02_market_cleaned__*__*{suffix}"):
                parsed_batch_id = path.stem.split("__", 2)[-1]
                if batch_id and parsed_batch_id != batch_id:
                    continue
                candidates.append(
                    Artifact(
                        batch_id=parsed_batch_id,
                        run_id=run_id,
                        path=path,
                        format_name=format_name,
                    )
                )
    return prefer_latest_artifacts(candidates)


def scan_latest_stage_outputs(skill_root: Path, stage_prefix: str, batch_id: str | None = None) -> list[Artifact]:
    outputs_root = skill_root / "outputs"
    if not outputs_root.exists():
        return []
    candidates: list[Artifact] = []
    for run_dir in sorted([item for item in outputs_root.iterdir() if item.is_dir()], key=lambda p: p.name):
        run_id = run_dir.name
        for step_name, format_name, suffix in (
            ("step1", "csv", ".csv"),
            ("step1", "xlsx", ".xlsx"),
            ("step2", "csv", ".csv"),
            ("step2", "xlsx", ".xlsx"),
            ("step3", "csv", ".csv"),
            ("step3", "xlsx", ".xlsx"),
        ):
            format_dir = run_dir / step_name / format_name
            if not format_dir.exists():
                continue
            for path in format_dir.glob(f"{stage_prefix}__*{suffix}"):
                parsed_batch_id = batch_id_from_output_name(path, f"{stage_prefix}__")
                if batch_id and parsed_batch_id != batch_id:
                    continue
                candidates.append(
                    Artifact(
                        batch_id=parsed_batch_id,
                        run_id=run_id,
                        path=path,
                        format_name=format_name,
                    )
                )
    return prefer_latest_artifacts(candidates)


def find_inbox_raw_files(inbox_root: Path, batch_id: str | None = None) -> list[Path]:
    if not inbox_root.exists():
        return []
    candidates = [path for path in inbox_root.iterdir() if path.is_file() and path.suffix.lower() in {".csv", ".xlsx"}]
    if batch_id:
        matched = [path for path in candidates if batch_id.casefold() in path.stem.casefold()]
        if matched:
            return sorted(matched)
    return sorted(candidates)


def quantile_value(values: pd.Series, q: float) -> float | None:
    series = pd.to_numeric(values, errors="coerce").dropna()
    if series.empty:
        return None
    return float(series.quantile(q))


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def bounded_score(
    value: float | None,
    preferred_min: float | None = None,
    preferred_max: float | None = None,
    hard_min: float | None = None,
    hard_max: float | None = None,
) -> float:
    if value is None:
        return 0.0
    if hard_min is not None and value < hard_min:
        return 0.0
    if hard_max is not None and value > hard_max:
        return 0.0
    if preferred_min is not None and preferred_max is not None:
        if preferred_min <= value <= preferred_max:
            return 1.0
        if value < preferred_min:
            return 0.0 if preferred_min == 0 else max(0.0, value / preferred_min)
        return 0.0 if preferred_max == 0 else max(0.0, preferred_max / value)
    if preferred_min is not None:
        return min(1.0, value / preferred_min) if preferred_min else 1.0
    if preferred_max is not None:
        return min(1.0, preferred_max / value) if value else 0.0
    return 1.0


def choose_sheet_name(path: Path, default: str) -> str:
    return default if path.suffix.lower() == ".xlsx" else default


def path_flag(path_key: str, dept_l1: str, parent_l2: str, path_policy: dict[str, Any]) -> str:
    policy = path_policy.get("path_policy", {})
    whitelist = policy.get("whitelist", {})
    blacklist = policy.get("blacklist", {})
    normalized_path = normalize_token(path_key)
    normalized_dept = normalize_token(dept_l1)
    normalized_parent = normalize_token(parent_l2)
    normalized_pair = normalize_token(f"{dept_l1} > {parent_l2}".strip())

    def has_match(bucket: list[str], subject: str, prefix: bool = False) -> bool:
        normalized_bucket = [normalize_token(value) for value in bucket if normalize_text(value)]
        if not normalized_bucket:
            return False
        if prefix:
            return any(subject.startswith(item) for item in normalized_bucket)
        return subject in normalized_bucket

    if has_match(blacklist.get("full_path_prefix", []), normalized_path, prefix=True):
        return "BLACKLIST_PATH"
    if has_match(blacklist.get("dept_l1_parent_l2", []), normalized_pair):
        return "BLACKLIST_PARENT"
    if has_match(blacklist.get("parent_l2", []), normalized_parent):
        return "BLACKLIST_PARENT_L2"
    if has_match(blacklist.get("dept_l1", []), normalized_dept):
        return "BLACKLIST_DEPT"

    whitelist_defined = any(
        bool(whitelist.get(bucket))
        for bucket in ("dept_l1", "parent_l2", "dept_l1_parent_l2", "full_path_prefix")
    )
    if not whitelist_defined:
        return "ALLOW_DEFAULT"
    if has_match(whitelist.get("full_path_prefix", []), normalized_path, prefix=True):
        return "ALLOW_PATH"
    if has_match(whitelist.get("dept_l1_parent_l2", []), normalized_pair):
        return "ALLOW_PARENT"
    if has_match(whitelist.get("parent_l2", []), normalized_parent):
        return "ALLOW_PARENT_L2"
    if has_match(whitelist.get("dept_l1", []), normalized_dept):
        return "ALLOW_DEPT"
    return "REVIEW_NO_WHITELIST_MATCH"


def path_policy_mode(path_policy: dict[str, Any]) -> str:
    policy = path_policy.get("path_policy", {})
    return str(policy.get("mode") or policy.get("include_mode") or "advisory")


def dataframe_to_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    safe_frame = frame.where(pd.notnull(frame), None)
    return json.loads(safe_frame.to_json(orient="records", force_ascii=False))


def alias_lookup(frame: pd.DataFrame, aliases: dict[str, list[str]]) -> tuple[pd.DataFrame, dict[str, str | None], list[str]]:
    normalized = {normalize_token(column): column for column in frame.columns}
    rename_map: dict[str, str] = {}
    matched: dict[str, str | None] = {}
    missing: list[str] = []
    for target, options in aliases.items():
        found = None
        for option in options:
            actual = normalized.get(normalize_token(option))
            if actual:
                found = actual
                break
        matched[target] = found
        if found:
            rename_map[found] = target
        else:
            missing.append(target)
    standardized = frame.rename(columns=rename_map).copy()
    return standardized, matched, missing


def infer_asin_from_text(value: Any) -> str:
    match = re.search(r"\b([A-Z0-9]{10})\b", str(value or "").upper())
    return match.group(1) if match else ""


def dump_log(path: Path, payload: Any) -> None:
    write_json(path, payload)
