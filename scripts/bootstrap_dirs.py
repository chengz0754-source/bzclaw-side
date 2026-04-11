from __future__ import annotations

from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    required_dirs = [
        root / "configs",
        root / "inputs",
        root / "outputs",
        root / "logs",
        root / "reports",
        root / "runs",
        root / "playwright" / "auth",
        root / "playwright" / "profiles",
        root / "playwright" / "screenshots",
        root / "playwright" / "traces",
        root / "scripts",
        root / "models",
    ]
    for directory in required_dirs:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"OK {directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
