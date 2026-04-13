#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR.parent / "configs" / "orchestrator_config.yaml"


def load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def normalize_text(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def to_float(value: Any) -> float | None:
    text = normalize_text(value)
    if not text:
        return None
    for token in (",", "$", "%", "\u00a0", "\u00a5", "\uffe5", "\u00a3", "\u20ac"):
        text = text.replace(token, "")
    try:
        return float(text)
    except ValueError:
        return None


def load_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    elif path.suffix.lower() == ".xlsx":
        frame = pd.read_excel(path, sheet_name="market_cleaned", dtype=str)
    elif path.suffix.lower() == ".jsonl":
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        frame = pd.DataFrame(rows)
    else:
        raise ValueError(f"Unsupported M02 format: {path}")
    frame = frame.replace({pd.NA: None}).where(pd.notnull(frame), None)
    return frame


def count_ratio_out_of_range(frame: pd.DataFrame, ratio_fields: list[str]) -> int:
    bad_rows = 0
    for _, row in frame.iterrows():
        row_bad = False
        for field in ratio_fields:
            if field not in frame.columns:
                continue
            value = to_float(row.get(field))
            if value is not None and not (0.0 <= value <= 1.0):
                row_bad = True
                break
        if row_bad:
            bad_rows += 1
    return bad_rows


def validate_m02_file(m02_file: Path, config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or load_config()
    rules = config["validation"]
    frame = load_table(m02_file)
    row_count = len(frame)
    missing_required_fields = [field for field in rules["required_fields"] if field not in frame.columns]

    invalid_parse_rows = int((frame.get("seller_share_parse_flag", pd.Series(dtype=str)) == "INVALID_PARSE").sum())
    invalid_sum_rows = int((frame.get("seller_share_parse_flag", pd.Series(dtype=str)) == "INVALID_SUM").sum())
    seller_share_sum_series = frame.get("seller_share_sum", pd.Series(dtype=str)).map(to_float)
    seller_share_sum_gt_rows = int((seller_share_sum_series > 1.05).fillna(False).sum())
    seller_share_abnormal_rows = invalid_parse_rows + max(invalid_sum_rows, seller_share_sum_gt_rows)
    seller_share_abnormal_rate = (seller_share_abnormal_rows / row_count) if row_count else 0.0

    ratio_out_of_range_rows = count_ratio_out_of_range(frame, rules["ratio_fields"])
    ratio_out_of_range_rate = (ratio_out_of_range_rows / row_count) if row_count else 0.0

    path_missing_counts = {
        field: int(frame.get(field, pd.Series(dtype=str)).fillna("").astype(str).str.strip().eq("").sum())
        for field in rules["path_fields"]
    }
    critical_metric_missing_rows = 0
    if row_count:
        for _, row in frame.iterrows():
            if any(to_float(row.get(field)) is None for field in rules["critical_metric_fields"]):
                critical_metric_missing_rows += 1

    block_reasons: list[str] = []
    warn_reasons: list[str] = []
    if missing_required_fields:
        block_reasons.append(f"MISSING_REQUIRED_FIELDS:{','.join(missing_required_fields)}")
    if invalid_parse_rows > rules["invalid_parse_rows_max"]:
        block_reasons.append(f"INVALID_PARSE_ROWS:{invalid_parse_rows}")
    if seller_share_abnormal_rate > rules["seller_share_abnormal_rate_max"]:
        block_reasons.append(f"SELLER_SHARE_ABNORMAL_RATE:{seller_share_abnormal_rate:.4f}")
    if ratio_out_of_range_rate > rules["ratio_out_of_range_rate_max"]:
        block_reasons.append(f"RATIO_OUT_OF_RANGE_RATE:{ratio_out_of_range_rate:.4f}")

    if path_missing_counts.get("parent_l2", 0) > 0:
        warn_reasons.append(f"MISSING_PARENT_L2_ROWS:{path_missing_counts['parent_l2']}")
    if critical_metric_missing_rows > 0:
        warn_reasons.append(f"CRITICAL_METRIC_MISSING_ROWS:{critical_metric_missing_rows}")

    quality_status = "BLOCK" if block_reasons else "WARN" if warn_reasons else "PASS"
    return {
        "m02_file": str(m02_file),
        "row_count": row_count,
        "quality_status": quality_status,
        "missing_required_fields": missing_required_fields,
        "invalid_parse_rows": invalid_parse_rows,
        "invalid_sum_rows": invalid_sum_rows,
        "seller_share_sum_gt_rows": seller_share_sum_gt_rows,
        "seller_share_abnormal_rows": seller_share_abnormal_rows,
        "seller_share_abnormal_rate": round(seller_share_abnormal_rate, 6),
        "ratio_out_of_range_rows": ratio_out_of_range_rows,
        "ratio_out_of_range_rate": round(ratio_out_of_range_rate, 6),
        "path_missing_counts": path_missing_counts,
        "critical_metric_missing_rows": critical_metric_missing_rows,
        "block_reasons": block_reasons,
        "warn_reasons": warn_reasons,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate one M02 file before Step1.")
    parser.add_argument("--m02-file", required=True)
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = validate_m02_file(Path(args.m02_file).resolve())
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
