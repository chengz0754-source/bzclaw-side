from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


HEADERS = [
    "record_id",
    "campaign_name",
    "ad_group_name",
    "entity_type",
    "target_expression",
    "match_type",
    "action",
    "new_bid",
    "negative_type",
    "status",
    "placement",
    "placement_modifier",
    "note",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a review-only bulk CSV draft from an approved Ads Phase1 plan."
    )
    parser.add_argument("--input", required=True, help="Path to the bulk plan JSON.")
    parser.add_argument("--output", required=True, help="Path to the output CSV file.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_rows(rows: list[dict[str, Any]]) -> None:
    required = {"record_id", "campaign_name", "ad_group_name", "entity_type", "target_expression", "action", "status"}
    for index, row in enumerate(rows, start=1):
        missing = sorted(required - row.keys())
        if missing:
            raise ValueError(f"Row {index} is missing required fields: {', '.join(missing)}")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in HEADERS})


def main() -> None:
    args = parse_args()
    payload = load_json(Path(args.input))
    rows = payload.get("rows", [])
    validate_rows(rows)
    write_csv(Path(args.output), rows)


if __name__ == "__main__":
    main()
