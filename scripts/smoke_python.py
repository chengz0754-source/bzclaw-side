from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report_path = root / "reports" / "PYTHON_SMOKE_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Python Smoke Report",
        "",
        f"- UTC timestamp: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Executable: `{sys.executable}`",
        f"- Version: `{platform.python_version()}`",
        f"- Platform: `{platform.platform()}`",
        f"- Project root: `{root}`",
        "- Result: `PASS`",
        "",
        "Python launched successfully from the sidecar environment.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
