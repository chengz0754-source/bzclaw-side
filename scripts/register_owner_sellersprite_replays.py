from __future__ import annotations

import json

from sellersprite_auth_replay import prepare_default_replays


def main() -> int:
    payload = prepare_default_replays(dry_run=False)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
