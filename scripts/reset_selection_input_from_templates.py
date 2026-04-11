from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


PRE_SCREEN_TEMPLATE_FILES = [
    "00_选品运行目标与边界.csv",
    "01_市场入口与筛选参数.csv",
    "01_选品任务路由与目的.csv",
    "01A_市场发现参数.csv",
    "01B_产品与竞品种子输入.csv",
    "02_账号与合规预检查.csv",
    "02A_SIF补强策略输入.csv",
    "03_候选市场与候选品初筛池.csv",
]
POST_COST_TEMPLATE_FILE = "04_供应链询价与利润核算.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset current selection input files from the purpose-routed template set.",
    )
    parser.add_argument(
        "--include-post-cost",
        action="store_true",
        help="Also copy the post-cost sheet 04_供应链询价与利润核算.csv.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    template_dir = repo_root / "templates" / "selection_csv_cn_reference"
    input_dir = repo_root / "inputs" / "selection_run_current"

    template_dir.mkdir(parents=True, exist_ok=True)
    input_dir.mkdir(parents=True, exist_ok=True)

    template_names = list(PRE_SCREEN_TEMPLATE_FILES)
    if args.include_post_cost:
        template_names.append(POST_COST_TEMPLATE_FILE)

    missing = [name for name in template_names if not (template_dir / name).exists()]
    if missing:
        print("Missing template files:", file=sys.stderr)
        for name in missing:
            print(f"- {name}", file=sys.stderr)
        return 1

    copied: list[Path] = []
    for name in template_names:
        source = template_dir / name
        destination = input_dir / name
        shutil.copy2(source, destination)
        copied.append(destination)

    print("Reset current input directory from templates:")
    for path in copied:
        print(f"- {path}")
    print("Default copy set is 00 / 01(runtime) / 01(route) / 01A / 01B / 02 / 02A / 03. Add --include-post-cost to include 04.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
