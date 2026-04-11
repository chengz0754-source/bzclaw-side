#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml
from openai import OpenAI


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = SKILL_ROOT / "configs" / "semantic_filter_config.yaml"


@dataclass
class Artifact:
    path: Path
    batch_id: str
    format_name: str
    modified_at: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter the latest M03 niche shortlist with local semantic denoising.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--batch-id", default="")
    parser.add_argument("--m03-file", default="")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


def now_local() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def make_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, frame: pd.DataFrame, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists and --overwrite was not set: {path}")
    ensure_dir(path.parent)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_workbook(path: Path, sheets: dict[str, pd.DataFrame], overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists and --overwrite was not set: {path}")
    ensure_dir(path.parent)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=sheet_name[:31], index=False)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", " | ", text)
    return text.strip()


def strip_frame_strings(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.replace({pd.NA: None})
    cleaned = cleaned.where(pd.notnull(cleaned), None)
    for column in cleaned.columns:
        cleaned[column] = cleaned[column].map(lambda value: normalize_text(value) if isinstance(value, str) else value)
    return cleaned


def status_key(value: Any) -> str:
    return normalize_text(value).upper()


def compact_token(value: Any) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", normalize_text(value).casefold())


def to_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return default
        return float(value)
    text = normalize_text(value)
    if not text:
        return default
    text = text.replace("%", "")
    text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def chunked(values: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def load_table(path: Path, sheet_name: str) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    elif suffix == ".xlsx":
        workbook = pd.ExcelFile(path)
        chosen_sheet = sheet_name if sheet_name in workbook.sheet_names else workbook.sheet_names[0]
        frame = pd.read_excel(path, sheet_name=chosen_sheet, dtype=str)
    else:
        raise ValueError(f"Unsupported input format: {path}")
    return strip_frame_strings(frame)


def batch_id_from_path(path: Path) -> str:
    stem = path.stem
    parts = stem.split("__", 1)
    return parts[1] if len(parts) == 2 else stem


def batch_id_from_frame(frame: pd.DataFrame, path: Path) -> str:
    if "batch_id" in frame.columns:
        values = [normalize_text(value) for value in frame["batch_id"].tolist()]
        values = [value for value in values if value]
        if values:
            return values[0]
    return batch_id_from_path(path)


def latest_m03_artifact(root: Path, config: dict[str, Any], batch_id: str | None = None) -> Artifact:
    preference_order = config["io"].get("input_preference_order", ["xlsx", "csv"])
    preference_rank = {name.lower(): len(preference_order) - index for index, name in enumerate(preference_order)}
    candidates: list[Artifact] = []
    for pattern in config["io"]["input_patterns"]:
        for path in root.rglob(pattern):
            if not path.is_file():
                continue
            if SKILL_ROOT in path.parents:
                continue
            parsed_batch_id = batch_id_from_path(path)
            if batch_id and parsed_batch_id != batch_id:
                continue
            stat = path.stat()
            candidates.append(
                Artifact(
                    path=path,
                    batch_id=parsed_batch_id,
                    format_name=path.suffix.lower().lstrip("."),
                    modified_at=stat.st_mtime,
                )
            )
    if not candidates:
        raise FileNotFoundError("No M03_niche_shortlist input was found under the selected root.")
    candidates.sort(
        key=lambda item: (
            item.modified_at,
            preference_rank.get(item.format_name.lower(), 0),
            str(item.path),
        ),
        reverse=True,
    )
    return candidates[0]


def validate_required_columns(frame: pd.DataFrame, required_fields: list[str]) -> list[str]:
    return [field for field in required_fields if field not in frame.columns]


def build_client(config: dict[str, Any]) -> OpenAI:
    runtime = config["runtime"]
    return OpenAI(
        base_url=runtime["base_url"],
        api_key=runtime["api_key"],
        timeout=runtime.get("timeout_seconds", 120),
    )


def build_record_payload(row_id: int, row: pd.Series, fields: list[str]) -> dict[str, Any]:
    payload = {"row_id": row_id}
    for field in fields:
        payload[field] = normalize_text(row.get(field))
    return payload


def build_messages(records: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, str]]:
    instructions = {
        "task": "Classify semantic alignment for Step1 PASS_TO_STEP2 rows only.",
        "allowed_labels": config["semantic"]["allowed_labels"],
        "records": records,
    }
    return [
        {"role": "system", "content": config["prompt"]["system_prompt"]},
        {"role": "user", "content": json.dumps(instructions, ensure_ascii=False, indent=2)},
    ]


def extract_message_text(response: Any) -> str:
    try:
        content = response.choices[0].message.content
    except Exception as exc:
        raise ValueError(f"Unexpected model response shape: {exc}") from exc
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        return "\n".join(parts)
    return str(content)


def extract_balanced_json(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    for opening, closing in (("[", "]"), ("{", "}")):
        start = cleaned.find(opening)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(cleaned)):
            char = cleaned[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
                continue
            if char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth == 0:
                    return cleaned[start : index + 1]
    return cleaned


def normalize_label(value: Any, config: dict[str, Any]) -> str:
    allowed = set(config["semantic"]["allowed_labels"])
    text = normalize_text(value).upper().replace("-", "_").replace(" ", "_")
    if text in allowed:
        return text
    if "DROP" in text:
        return config["semantic"]["drop_label"]
    if "KEEP" in text or "PASS" in text:
        return "KEEP"
    return config["semantic"]["conservative_default_label"]


def normalize_reason(value: Any, max_chars: int) -> str:
    text = normalize_text(value)
    if not text:
        return "No semantic reason was returned by the model."
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def normalize_confidence(value: Any) -> float:
    number = to_float(value, default=0.5)
    if number is None:
        number = 0.5
    if number > 1 and number <= 100:
        number = number / 100.0
    return round(clamp(float(number), 0.0, 1.0), 4)


def parse_batch_response(text: str, expected_ids: list[int], config: dict[str, Any]) -> dict[int, dict[str, Any]]:
    payload = json.loads(extract_balanced_json(text))
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("results") or payload.get("rows") or []
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValueError("Model response JSON was neither an array nor an object.")
    result_map: dict[int, dict[str, Any]] = {}
    max_reason_chars = config["semantic"]["max_reason_chars"]
    for item in items:
        if not isinstance(item, dict):
            continue
        row_id = int(to_float(item.get("row_id"), default=-1) or -1)
        if row_id not in expected_ids:
            continue
        result_map[row_id] = {
            "semantic_label": normalize_label(item.get("semantic_label"), config),
            "semantic_reason": normalize_reason(item.get("semantic_reason"), max_reason_chars),
            "semantic_confidence": normalize_confidence(item.get("semantic_confidence")),
            "semantic_error": "",
        }
    missing_ids = [row_id for row_id in expected_ids if row_id not in result_map]
    if missing_ids:
        raise ValueError(f"Model response did not return all expected row_ids: {missing_ids}")
    return result_map


def request_batch(
    client: OpenAI,
    records: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    runtime = config["runtime"]
    response = client.chat.completions.create(
        model=runtime["model"],
        temperature=runtime.get("temperature", 0.0),
        messages=build_messages(records, config),
    )
    content = extract_message_text(response)
    return parse_batch_response(content, [int(record["row_id"]) for record in records], config)


def has_direct_seed_match(record: dict[str, Any]) -> bool:
    seed = compact_token(record.get("query_seed"))
    if len(seed) < 6:
        return False
    for field in ("niche_leaf", "niche_en", "path_key", "market_path_raw"):
        subject = compact_token(record.get(field))
        if subject and seed in subject:
            return True
    return False


def fallback_result(record: dict[str, Any], message: str, config: dict[str, Any]) -> dict[int, dict[str, Any]]:
    row_id = int(record["row_id"])
    if has_direct_seed_match(record):
        return {
            row_id: {
                "semantic_label": "KEEP",
                "semantic_reason": "Direct lexical match between query_seed and niche/path.",
                "semantic_confidence": 0.99,
                "semantic_error": "FALLBACK_DIRECT_MATCH",
            }
        }
    return {
        row_id: {
            "semantic_label": config["semantic"]["conservative_default_label"],
            "semantic_reason": normalize_reason(message, config["semantic"]["max_reason_chars"]),
            "semantic_confidence": 0.35,
            "semantic_error": "FALLBACK_REVIEW",
        }
    }


def classify_records(
    client: OpenAI,
    records: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    try:
        return request_batch(client, records, config), errors
    except Exception as exc:
        errors.append(
            {
                "scope": "batch",
                "row_ids": [int(record["row_id"]) for record in records],
                "message": str(exc),
            }
        )
        if len(records) == 1:
            record = records[0]
            reason = f"Fallback REVIEW after local semantic batch failure: {exc}"
            return fallback_result(record, reason, config), errors

    results: dict[int, dict[str, Any]] = {}
    for record in records:
        try:
            results.update(request_batch(client, [record], config))
        except Exception as exc:
            errors.append(
                {
                    "scope": "row",
                    "row_ids": [int(record["row_id"])],
                    "message": str(exc),
                }
            )
            reason = f"Fallback REVIEW after local semantic row failure: {exc}"
            results.update(fallback_result(record, reason, config))
    return results, errors


def build_queue(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    queue_frame = frame[
        (frame["step1_status"].map(status_key) == "PASS_TO_STEP2") & (frame["final_keep_flag"] == True)
    ].copy()
    if queue_frame.empty:
        base_columns = [
            "batch_id",
            "marketplace",
            "dept_l1",
            "parent_l2",
            "parent_l3",
            "niche_leaf",
            "path_key",
            "query_seed",
            "step1_score",
            "semantic_label",
            "semantic_reason",
            "semantic_confidence",
            "download_type",
            "expected_input_folder",
            "next_step",
        ]
        return pd.DataFrame(columns=base_columns)
    if "parent_l3" not in queue_frame.columns:
        queue_frame["parent_l3"] = ""
    if "marketplace" not in queue_frame.columns:
        queue_frame["marketplace"] = ""
    queue_frame["download_type"] = config["queue"]["download_type"]
    queue_frame["expected_input_folder"] = config["queue"]["expected_input_folder"]
    queue_frame["next_step"] = config["queue"]["next_step"]
    queue_frame = queue_frame.drop_duplicates(subset=config["queue"]["dedupe_fields"])
    columns = [
        "batch_id",
        "marketplace",
        "dept_l1",
        "parent_l2",
        "parent_l3",
        "niche_leaf",
        "path_key",
        "query_seed",
        "step1_score",
        "semantic_label",
        "semantic_reason",
        "semantic_confidence",
        "download_type",
        "expected_input_folder",
        "next_step",
    ]
    return queue_frame[columns].reset_index(drop=True)


def run_semantic_filter(
    root: Path,
    config: dict[str, Any],
    run_id: str | None = None,
    batch_id: str | None = None,
    m03_file: Path | None = None,
    overwrite: bool = False,
    debug: bool = False,
) -> dict[str, Any]:
    selected_run_id = run_id or make_run_id()
    outputs_root = ensure_dir(SKILL_ROOT / config["io"]["outputs_dir"] / selected_run_id)
    logs_root = ensure_dir(SKILL_ROOT / config["io"]["logs_dir"] / selected_run_id)

    artifact = (
        Artifact(
            path=m03_file.resolve(),
            batch_id=batch_id_from_path(m03_file.resolve()),
            format_name=m03_file.suffix.lower().lstrip("."),
            modified_at=m03_file.resolve().stat().st_mtime,
        )
        if m03_file
        else latest_m03_artifact(root.resolve(), config, batch_id=batch_id or None)
    )

    started_at = now_local()
    frame = load_table(artifact.path, config["io"]["input_sheet_name"])
    missing_columns = validate_required_columns(frame, config["columns"]["required_fields"])
    if missing_columns:
        raise ValueError(f"M03 input is missing required columns: {', '.join(missing_columns)}")

    resolved_batch_id = batch_id_from_frame(frame, artifact.path)
    frame = frame.copy()
    frame["batch_id"] = resolved_batch_id
    frame["semantic_run_id"] = selected_run_id
    frame["semantic_model"] = config["runtime"]["model"]
    frame["semantic_applied"] = False
    frame["semantic_label"] = ""
    frame["semantic_reason"] = ""
    frame["semantic_confidence"] = None
    frame["final_keep_flag"] = False
    frame["semantic_error"] = ""

    pass_mask = frame["step1_status"].map(status_key) == "PASS_TO_STEP2"
    pass_indices = list(frame.index[pass_mask])
    payload_fields = config["columns"]["model_payload_fields"]
    client = build_client(config)

    progress: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if pass_indices:
        batch_size = int(config["semantic"]["batch_size"])
        total_batches = math.ceil(len(pass_indices) / batch_size)
        for batch_number, index_chunk in enumerate(chunked(pass_indices, batch_size), start=1):
            print(f"[semantic-filter] batch={batch_number}/{total_batches} rows={len(index_chunk)}")
            records = [build_record_payload(int(index_value), frame.loc[index_value], payload_fields) for index_value in index_chunk]
            batch_results, batch_errors = classify_records(client, records, config)
            errors.extend(batch_errors)
            for row_id, result in batch_results.items():
                label = result["semantic_label"]
                frame.at[row_id, "semantic_applied"] = True
                frame.at[row_id, "semantic_label"] = label
                frame.at[row_id, "semantic_reason"] = result["semantic_reason"]
                frame.at[row_id, "semantic_confidence"] = result["semantic_confidence"]
                frame.at[row_id, "final_keep_flag"] = label in set(config["semantic"]["keep_labels"])
                frame.at[row_id, "semantic_error"] = result.get("semantic_error", "")
            progress.append(
                {
                    "batch_number": batch_number,
                    "row_count": len(index_chunk),
                    "row_ids": [int(value) for value in index_chunk],
                }
            )

    passthrough_label = config["semantic"]["non_pass_passthrough_label"]
    for row_id in frame.index[~pass_mask]:
        current_status = normalize_text(frame.at[row_id, "step1_status"]) or "UNKNOWN"
        frame.at[row_id, "semantic_applied"] = False
        frame.at[row_id, "semantic_label"] = passthrough_label
        frame.at[row_id, "semantic_reason"] = (
            f"Skipped semantic filter because step1_status={current_status}; upstream Step1 result remains authoritative."
        )
        frame.at[row_id, "semantic_confidence"] = 1.0
        frame.at[row_id, "final_keep_flag"] = False
        frame.at[row_id, "semantic_error"] = ""

    frame["semantic_confidence"] = frame["semantic_confidence"].map(lambda value: normalize_confidence(value) if value is not None else None)

    queue_frame = build_queue(frame, config)
    run_log_frame = pd.DataFrame(
        [
            {
                "run_id": selected_run_id,
                "started_at": started_at,
                "finished_at": now_local(),
                "input_m03": str(artifact.path),
                "batch_id": resolved_batch_id,
                "total_rows": len(frame),
                "pass_to_step2_rows": int(pass_mask.sum()),
                "semantic_applied_rows": int(frame["semantic_applied"].sum()),
                "skipped_non_pass_rows": int((~pass_mask).sum()),
                "semantic_drop_rows": int(((frame["step1_status"].map(status_key) == "PASS_TO_STEP2") & (frame["final_keep_flag"] == False)).sum()),
                "queue_rows": len(queue_frame),
                "model": config["runtime"]["model"],
                "base_url": config["runtime"]["base_url"],
            }
        ]
    )

    xlsx_path = outputs_root / f"M03_semantic_filtered__{resolved_batch_id}.xlsx"
    csv_path = outputs_root / f"M03_semantic_filtered__{resolved_batch_id}.csv"
    queue_path = outputs_root / f"semantic_benchmark_queue__{resolved_batch_id}.csv"
    manifest_path = outputs_root / f"semantic_filter_manifest__{selected_run_id}.json"
    log_path = logs_root / f"semantic_filter_run_log__{selected_run_id}.json"

    write_workbook(
        xlsx_path,
        {
            config["io"]["filtered_sheet_name"]: frame,
            config["io"]["queue_sheet_name"]: queue_frame,
            config["io"]["run_log_sheet_name"]: run_log_frame,
        },
        overwrite=overwrite,
    )
    write_csv(csv_path, frame, overwrite=overwrite)
    write_csv(queue_path, queue_frame, overwrite=overwrite)

    label_distribution = {str(key): int(value) for key, value in frame["semantic_label"].value_counts(dropna=False).to_dict().items()}
    applied_distribution = {
        str(key): int(value)
        for key, value in frame.loc[frame["semantic_applied"], "semantic_label"].value_counts(dropna=False).to_dict().items()
    }
    manifest = {
        "run_id": selected_run_id,
        "started_at": started_at,
        "finished_at": now_local(),
        "input_root": str(root.resolve()),
        "input_m03": str(artifact.path),
        "input_format": artifact.format_name,
        "batch_id": resolved_batch_id,
        "row_input": len(frame),
        "pass_to_step2_rows": int(pass_mask.sum()),
        "semantic_applied_rows": int(frame["semantic_applied"].sum()),
        "skipped_non_pass_rows": int((~pass_mask).sum()),
        "semantic_label_distribution": label_distribution,
        "semantic_applied_label_distribution": applied_distribution,
        "final_keep_true_rows": int(frame["final_keep_flag"].sum()),
        "semantic_drop_rows": int(((frame["step1_status"].map(status_key) == "PASS_TO_STEP2") & (frame["final_keep_flag"] == False)).sum()),
        "queue_rows": len(queue_frame),
        "outputs": {
            "m03_semantic_filtered_xlsx": str(xlsx_path),
            "m03_semantic_filtered_csv": str(csv_path),
            "semantic_benchmark_queue_csv": str(queue_path),
            "run_log_json": str(log_path),
        },
        "runtime": {
            "base_url": config["runtime"]["base_url"],
            "api_key": config["runtime"]["api_key"],
            "model": config["runtime"]["model"],
        },
        "progress_batches": progress,
        "errors": errors,
    }
    write_json(manifest_path, manifest)
    write_json(log_path, manifest)

    summary = {
        "run_id": selected_run_id,
        "input_m03": str(artifact.path),
        "batch_id": resolved_batch_id,
        "outputs": manifest["outputs"],
        "semantic_label_distribution": label_distribution,
        "semantic_applied_label_distribution": applied_distribution,
        "queue_rows": len(queue_frame),
        "errors": errors,
    }
    if debug:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"[semantic-filter] run_id={selected_run_id} batch_id={resolved_batch_id}")
    print(f"[semantic-filter] input_m03={artifact.path}")
    print(f"[semantic-filter] filtered_xlsx={xlsx_path}")
    print(f"[semantic-filter] filtered_csv={csv_path}")
    print(f"[semantic-filter] queue_csv={queue_path} queue_rows={len(queue_frame)}")
    print(f"[semantic-filter] label_distribution={json.dumps(label_distribution, ensure_ascii=False)}")
    return summary


def main() -> None:
    args = parse_args()
    config = read_yaml(CONFIG_PATH)
    summary = run_semantic_filter(
        root=Path(args.root),
        config=config,
        run_id=args.run_id or None,
        batch_id=args.batch_id or None,
        m03_file=Path(args.m03_file) if args.m03_file else None,
        overwrite=args.overwrite,
        debug=args.debug,
    )
    if args.debug:
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[semantic-filter] ERROR: {exc}", file=sys.stderr)
        raise
