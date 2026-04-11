from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_ALLOWED_FILES = {
    ".env.example",
    ".gitignore",
    "amazon-selection-automation.gitignore",
    "package.json",
    "README.md",
    "requirements.txt",
}
STANDARD_SELECTION_CSV_NAMES = [
    "00_选品运行目标与边界.csv",
    "01_市场入口与筛选参数.csv",
    "02_账号与合规预检查.csv",
    "03_候选市场与候选品初筛池.csv",
    "04_供应链询价与利润核算.csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="扫描并治理仓库根目录业务文件污染，默认只输出建议；使用 --apply 才会实际迁移。"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="执行建议动作，把根目录业务文件归位或清除重复副本。",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_business_root_file(path: Path) -> bool:
    if path.name in ROOT_ALLOWED_FILES:
        return False
    suffix = path.suffix.lower()
    if suffix in {".csv", ".xlsx", ".xls"}:
        return True
    if suffix == ".md" and any(token in path.stem.lower() for token in ("选品", "market", "selection", "candidate", "mapping")):
        return True
    return False


def detect_root_business_files(repo_root: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in repo_root.iterdir()
            if path.is_file() and is_business_root_file(path)
        ]
    )


def classify_root_file(repo_root: Path, path: Path) -> dict[str, Any]:
    template_dir = repo_root / "templates" / "selection_csv_cn_reference"
    input_dir = repo_root / "inputs" / "selection_run_current"
    runs_market_dir = repo_root / "runs" / "manual" / "10_market"

    record: dict[str, Any] = {
        "file": str(path),
        "name": path.name,
        "action": "REPORT_ONLY",
        "reason": "",
        "destination": "",
    }

    if path.name in STANDARD_SELECTION_CSV_NAMES:
        template_path = template_dir / path.name
        input_path = input_dir / path.name
        if template_path.exists() and sha256(path) == sha256(template_path):
            record.update(
                {
                    "action": "REMOVE_ROOT_DUPLICATE",
                    "reason": "根目录副本与模板目录完全一致，视为污染副本。",
                    "destination": str(template_path),
                }
            )
            return record
        if input_path.exists() and sha256(path) == sha256(input_path):
            record.update(
                {
                    "action": "REMOVE_ROOT_DUPLICATE",
                    "reason": "根目录副本与当前输入目录完全一致，视为污染副本。",
                    "destination": str(input_path),
                }
            )
            return record
        if not input_path.exists():
            record.update(
                {
                    "action": "MOVE_TO_CURRENT_INPUT",
                    "reason": "根目录文件与模板不一致，且当前输入目录缺少同名文件，更像本轮真实输入。",
                    "destination": str(input_path),
                }
            )
            return record
        record.update(
            {
                "action": "MOVE_TO_ROOT_RECOVERY_ARCHIVE",
                "reason": "根目录文件与模板/当前输入都不一致，需要保守归档保留。",
                "destination": str(
                    repo_root
                    / "outputs"
                    / "selection_runs"
                    / datetime.now().strftime("%Y%m%d_%H%M%S")
                    / "02_generated_outputs"
                    / "root_recovered_from_root"
                    / path.name
                ),
            }
        )
        return record

    if path.suffix.lower() in {".xlsx", ".xls"}:
        destination = runs_market_dir / path.name
        record.update(
            {
                "action": "MOVE_TO_MARKET_RUNS",
                "reason": "根目录市场表/业务 Excel 应落在 runs/manual/10_market/。",
                "destination": str(destination),
            }
        )
        return record

    if path.suffix.lower() == ".md":
        destination = repo_root / "reports" / path.name
        record.update(
            {
                "action": "MOVE_TO_REPORTS",
                "reason": "根目录业务说明文档应落在 reports/。",
                "destination": str(destination),
            }
        )
        return record

    return record


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def apply_action(record: dict[str, Any]) -> dict[str, Any]:
    path = Path(record["file"])
    action = record["action"]
    destination = Path(record["destination"]) if record["destination"] else None
    applied = dict(record)
    applied["status"] = "SKIPPED"

    if action == "REMOVE_ROOT_DUPLICATE":
        path.unlink()
        applied["status"] = "APPLIED"
        return applied

    if action in {"MOVE_TO_CURRENT_INPUT", "MOVE_TO_MARKET_RUNS", "MOVE_TO_REPORTS"} and destination is not None:
        ensure_parent(destination)
        if destination.exists():
            if destination.is_file() and sha256(path) == sha256(destination):
                path.unlink()
                applied["status"] = "APPLIED_DUPLICATE_REMOVED"
                return applied
            raise FileExistsError(f"目标文件已存在且内容不同：{destination}")
        shutil.move(str(path), str(destination))
        applied["status"] = "APPLIED"
        return applied

    if action == "MOVE_TO_ROOT_RECOVERY_ARCHIVE" and destination is not None:
        ensure_parent(destination)
        shutil.move(str(path), str(destination))
        applied["status"] = "APPLIED"
        return applied

    return applied


def write_reports(repo_root: Path, records: list[dict[str, Any]], apply_mode: bool) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    markdown_lines = [
        "# 仓库根目录业务文件迁移记录",
        "",
        f"- 记录时间：`{timestamp}`",
        f"- 模式：`{'APPLY' if apply_mode else 'REPORT_ONLY'}`",
        "",
        "## 明细",
        "",
    ]
    for record in records:
        markdown_lines.extend(
            [
                f"### {record['name']}",
                "",
                f"- 动作：`{record['action']}`",
                f"- 原因：{record['reason']}",
                f"- 目标位置：`{record['destination'] or 'N/A'}`",
                f"- 执行状态：`{record.get('status', 'PLANNED')}`",
                "",
            ]
        )
    markdown_path = repo_root / "reports" / "仓库根目录业务文件迁移记录.md"
    markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    json_path = repo_root / "reports" / "仓库根目录业务文件迁移记录.json"
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    root_files = detect_root_business_files(repo_root)
    if not root_files:
        print("仓库根目录未发现需要治理的业务文件。")
        write_reports(repo_root, [], args.apply)
        return 0

    records = [classify_root_file(repo_root, path) for path in root_files]
    if args.apply:
        applied_records: list[dict[str, Any]] = []
        for record in records:
            try:
                applied_records.append(apply_action(record))
            except Exception as exc:
                failed = dict(record)
                failed["status"] = f"FAILED: {exc}"
                applied_records.append(failed)
                write_reports(repo_root, applied_records, True)
                print(f"执行失败：{exc}", file=sys.stderr)
                return 1
        write_reports(repo_root, applied_records, True)
        print("仓库根目录业务文件治理完成：")
        for record in applied_records:
            print(
                f"- {record['name']} | {record['action']} | {record.get('status', 'APPLIED')} | "
                f"{record['destination'] or 'N/A'}"
            )
        return 0

    write_reports(repo_root, records, False)
    print("仓库根目录业务文件治理建议：")
    for record in records:
        print(f"- {record['name']} | {record['action']} | {record['destination'] or 'N/A'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
