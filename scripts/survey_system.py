from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def first_line(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return None
    output = (completed.stdout or completed.stderr).strip().splitlines()
    return output[0] if output else None


def command_info(name: str) -> dict[str, str | bool | None]:
    path = shutil.which(name)
    version = None
    if path:
        version = first_line([name, "--version"])
    return {"found": bool(path), "path": path, "version": version}


def limited_files(base: Path, patterns: tuple[str, ...], limit: int = 20) -> list[str]:
    matches: list[str] = []
    if not base.exists():
        return matches
    for pattern in patterns:
        for item in base.rglob(pattern):
            if ".venv" in item.parts:
                continue
            if item.is_file():
                matches.append(str(item))
            if len(matches) >= limit:
                return matches
    return matches


def limited_dirs(base: Path, names: set[str], limit: int = 20) -> list[str]:
    matches: list[str] = []
    if not base.exists():
        return matches
    for item in base.rglob("*"):
        if ".venv" in item.parts:
            continue
        if item.is_dir() and item.name in names:
            matches.append(str(item))
        if len(matches) >= limit:
            return matches
    return matches


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    legacy_root = Path(r"E:\选品")
    target_root = Path(r"E:\选品文件夹")
    zip_path = Path(r"C:\Users\Administrator\Downloads\SELECTION_SYSTEM_VERIFICATION_PACKAGE__20260404 (1).zip")
    common_browsers = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ]

    inventory = {
        "mode_candidates": ["VERIFY_ONLY", "VERIFY_AND_BOOTSTRAP", "FULL_BOOTSTRAP"],
        "paths": {
            "target_root_exists": target_root.exists(),
            "project_root_exists": root.exists(),
            "legacy_selection_root_exists": legacy_root.exists(),
            "verification_package_zip_exists": zip_path.exists(),
        },
        "tooling": {
            "node": command_info("node"),
            "npm": command_info("npm"),
            "pnpm": command_info("pnpm"),
            "python": command_info("python"),
            "git": command_info("git"),
            "ollama": command_info("ollama"),
        },
        "browser_binaries": [str(path) for path in common_browsers if path.exists()],
        "playwright_cli": command_info("playwright"),
        "reuse_candidates": {
            "legacy_env_files": limited_files(legacy_root, (".env", ".env.local", ".env.example")),
            "legacy_configs": limited_files(legacy_root, ("*.yaml", "*.yml", "*.json"), limit=30),
            "legacy_outputs_dirs": limited_dirs(legacy_root, {"outputs", "logs", "reports"}, limit=30),
            "seller_exports": limited_files(legacy_root, ("Market-research*.xlsx",), limit=10),
            "seller_or_sif_scripts": limited_files(legacy_root, ("*.py", "*.md"), limit=40),
            "playwright_state_files": limited_files(legacy_root, ("*storage_state*.json", "*state*.json", "*auth*.json"), limit=20),
        },
        "notes": {
            "project_root": str(root),
            "legacy_selection_root": str(legacy_root),
            "verification_package_zip": str(zip_path),
            "chrome_default_profile_not_for_automation": True,
        },
    }

    inventory_path = reports_dir / "ENV_INVENTORY.json"
    inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
    print(inventory_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
