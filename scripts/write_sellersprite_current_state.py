from __future__ import annotations

import argparse
import json
from pathlib import Path

from sellersprite_stage_closure_lib import find_repo_root, read_json, write_current_state


def main() -> int:
    parser = argparse.ArgumentParser(description="Write SellerSprite current-state hosts from reconciled deterministic input.")
    parser.add_argument("--repo-root", type=Path, default=None, help="Optional repo root override.")
    parser.add_argument("--input", type=Path, required=True, help="Reconciled JSON input path.")
    args = parser.parse_args()

    repo_root = find_repo_root(args.repo_root)
    input_path = args.input if args.input.is_absolute() else repo_root / args.input
    reconciled = read_json(input_path)
    written_files = write_current_state(reconciled, repo_root)
    print(json.dumps({"written_files": written_files}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
