from __future__ import annotations

import argparse
from pathlib import Path

from sellersprite_stage_closure_lib import (
    build_owner_writeback_bundle,
    find_repo_root,
    load_stage_evaluation_payload,
    read_json,
    write_owner_writeback_bundle,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic SellerSprite next-stage owner handoff outputs from structured truth-pack hosts.")
    parser.add_argument("--repo-root", type=Path, default=None, help="Optional repo root override.")
    parser.add_argument(
        "--stage-status",
        type=Path,
        default=Path("reports/latest_sellersprite_stage_status.json"),
        help="Stage evaluator result JSON path.",
    )
    args = parser.parse_args()

    repo_root = find_repo_root(args.repo_root)
    stage_status_path = args.stage_status if args.stage_status.is_absolute() else repo_root / args.stage_status
    stage_payload = read_json(stage_status_path)
    stage_evaluation = load_stage_evaluation_payload(stage_payload)
    bundle = build_owner_writeback_bundle(stage_evaluation, repo_root, generated_at_utc=stage_evaluation.get("generated_at_utc"))
    write_owner_writeback_bundle(bundle, repo_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
