from __future__ import annotations

import argparse
import json
from pathlib import Path

from sellersprite_stage_closure_lib import evaluate_stage_status, find_repo_root, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the current SellerSprite stage status from repo-visible truth hosts.")
    parser.add_argument("--repo-root", type=Path, default=None, help="Optional repo root override.")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path.")
    args = parser.parse_args()

    repo_root = find_repo_root(args.repo_root)
    payload = evaluate_stage_status(repo_root)
    if args.output is not None:
        output_path = args.output if args.output.is_absolute() else repo_root / args.output
        write_json(output_path, payload)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
