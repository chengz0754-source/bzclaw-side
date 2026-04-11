from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


PROTECTED_INPUT_NAMES = {"README.md", ".gitkeep"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="按时间戳归档本次选品运行输入、输出与日志，并清空当前输入目录。"
    )
    parser.add_argument(
        "--generated",
        nargs="*",
        default=[],
        help="本次运行生成的结果文件或目录，可传多个相对路径或绝对路径。",
    )
    parser.add_argument(
        "--logs",
        nargs="*",
        default=[],
        help="本次运行日志、自检结果或报错文件，可传多个相对路径或绝对路径。",
    )
    parser.add_argument(
        "--move-generated",
        action="store_true",
        help="把 --generated 指定的结果移动到归档目录；默认是复制。",
    )
    parser.add_argument(
        "--move-logs",
        action="store_true",
        help="把 --logs 指定的日志移动到归档目录；默认是复制。",
    )
    parser.add_argument(
        "--timestamp",
        default=None,
        help="可选，手工指定时间戳目录名，格式建议为 YYYYMMDD_HHMMSS。",
    )
    return parser.parse_args()


def resolve_paths(repo_root: Path, raw_paths: list[str], label: str) -> list[Path]:
    resolved: list[Path] = []
    missing: list[str] = []
    for raw in raw_paths:
        path = Path(raw)
        if not path.is_absolute():
            path = repo_root / path
        if not path.exists():
            missing.append(raw)
            continue
        resolved.append(path)
    if missing:
        print(f"归档失败：以下{label}不存在：", file=sys.stderr)
        for item in missing:
            print(f"- {item}", file=sys.stderr)
        raise FileNotFoundError(label)
    return resolved


def copy_or_move(items: list[Path], destination_dir: Path, move: bool) -> list[Path]:
    archived_paths: list[Path] = []
    for item in items:
        target = destination_dir / item.name
        if item.is_dir():
            if move:
                shutil.move(str(item), str(target))
            else:
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target)
        else:
            if move:
                shutil.move(str(item), str(target))
            else:
                shutil.copy2(item, target)
        archived_paths.append(target)
    return archived_paths


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    input_dir = repo_root / "inputs" / "selection_run_current"
    outputs_root = repo_root / "outputs" / "selection_runs"

    input_dir.mkdir(parents=True, exist_ok=True)
    outputs_root.mkdir(parents=True, exist_ok=True)

    consumable_inputs = [
        path
        for path in sorted(input_dir.iterdir())
        if path.name not in PROTECTED_INPUT_NAMES
    ]
    if not consumable_inputs:
        print(
            "归档未执行：`inputs/selection_run_current/` 中没有可归档的输入文件。"
            " 请先放入本次运行 CSV，再执行归档脚本。",
            file=sys.stderr,
        )
        return 1

    try:
        generated_items = resolve_paths(repo_root, args.generated, "结果文件")
        log_items = resolve_paths(repo_root, args.logs, "日志文件")
    except FileNotFoundError:
        return 1

    timestamp = args.timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = outputs_root / timestamp
    if run_dir.exists():
        print(f"归档失败：时间戳目录已存在：{run_dir}", file=sys.stderr)
        return 1

    consumed_dir = run_dir / "01_consumed_inputs"
    generated_dir = run_dir / "02_generated_outputs"
    logs_dir = run_dir / "03_logs"
    for path in (consumed_dir, generated_dir, logs_dir):
        path.mkdir(parents=True, exist_ok=True)

    archived_inputs = []
    while True:
        current_batch = [
            path
            for path in sorted(input_dir.iterdir())
            if path.name not in PROTECTED_INPUT_NAMES
        ]
        if not current_batch:
            break
        for item in current_batch:
            target = consumed_dir / item.name
            shutil.move(str(item), str(target))
            archived_inputs.append(target)

    archived_generated = copy_or_move(generated_items, generated_dir, args.move_generated)
    archived_logs = copy_or_move(log_items, logs_dir, args.move_logs)

    summary_lines = [
        "# 本次选品运行归档摘要",
        "",
        f"- 归档时间戳：`{timestamp}`",
        f"- 归档目录：`{run_dir}`",
        "",
        "## 已归档输入",
        "",
    ]
    summary_lines.extend([f"- `{path.name}`" for path in archived_inputs] or ["- 无"])
    summary_lines.extend(["", "## 已归档输出结果", ""])
    summary_lines.extend([f"- `{path.name}`" for path in archived_generated] or ["- 无"])
    summary_lines.extend(["", "## 已归档日志", ""])
    summary_lines.extend([f"- `{path.name}`" for path in archived_logs] or ["- 无"])
    summary_lines.extend(
        [
            "",
            "## 输入目录清理结果",
            "",
            "- `inputs/selection_run_current/` 中的本次输入文件已移入 `01_consumed_inputs/`。",
            "- 模板参考目录 `templates/selection_csv_cn_reference/` 未被修改。",
            "- `04_供应链询价与利润核算.csv` 仍按后置表处理，不在前置阶段强制要求填写。",
        ]
    )
    write_text(run_dir / "00_run_summary.md", "\n".join(summary_lines) + "\n")

    archive_log_lines = [
        f"archive_timestamp={timestamp}",
        f"consumed_inputs={len(archived_inputs)}",
        f"generated_outputs={len(archived_generated)}",
        f"logs={len(archived_logs)}",
        f"input_dir={input_dir}",
        f"run_dir={run_dir}",
    ]
    write_text(logs_dir / "archive_log.txt", "\n".join(archive_log_lines) + "\n")

    remaining = [
        path.name
        for path in sorted(input_dir.iterdir())
        if path.name not in PROTECTED_INPUT_NAMES
    ]
    if remaining:
        print("归档后清空检查失败：输入目录仍残留以下文件：", file=sys.stderr)
        for name in remaining:
            print(f"- {name}", file=sys.stderr)
        return 1

    print(f"归档完成：{run_dir}")
    print("已归档输入：")
    for path in archived_inputs:
        print(f"- {path}")
    if archived_generated:
        print("已归档结果文件：")
        for path in archived_generated:
            print(f"- {path}")
    if archived_logs:
        print("已归档日志文件：")
        for path in archived_logs:
            print(f"- {path}")
    print("输入目录已清空，仅保留 README.md 等受保护文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
