from __future__ import annotations

import argparse
import json
from pathlib import Path

from sellersprite_stage_closure_lib import (
    evaluate_stage_status,
    find_repo_root,
    read_json,
    reconcile_truth_hosts,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile SellerSprite current truth hosts from deterministic evaluator output.")
    parser.add_argument("--repo-root", type=Path, default=None, help="Optional repo root override.")
    parser.add_argument("--input", type=Path, default=None, help="Evaluator JSON input. If omitted, evaluate first.")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path.")
    args = parser.parse_args()

    repo_root = find_repo_root(args.repo_root)
    if args.input is not None:
        input_path = args.input if args.input.is_absolute() else repo_root / args.input
        evaluation = read_json(input_path)
    else:
        evaluation = evaluate_stage_status(repo_root)
    payload = reconcile_truth_hosts(evaluation, repo_root)
    if args.output is not None:
        output_path = args.output if args.output.is_absolute() else repo_root / args.output
        write_json(output_path, payload)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
