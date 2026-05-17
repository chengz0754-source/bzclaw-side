from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQ = [
    'AGENTS.md',
    '.codex/config.toml',
    'docs/codex_interface/PROJECT_INTERFACE_CURRENT.md',
    'docs/codex_interface/PROJECT_INTERFACE_CURRENT.json',
    'docs/codex_interface/READ_ORDER_CURRENT.md',
    'docs/codex_interface/REUSE_POINTERS_CURRENT.md',
    'docs/codex_interface/STATUS_CURRENT.md',
    'docs/codex_interface/STATUS_CURRENT.json',
    'docs/codex_interface/FORBIDDEN_ACTIONS_CURRENT.md',
    'docs/codex_interface/NEXT_TASK_ENTRY_CURRENT.md',
    'docs/codex_interface/INTERFACE_UPDATE_PROTOCOL_CURRENT.md',
    'docs/codex_interface/last_task_interface_check.json',
]
errors = []
for rel in REQ:
    if not (ROOT / rel).exists():
        errors.append('missing required file: ' + rel)
agents = ROOT / 'AGENTS.md'
if agents.exists():
    text = agents.read_text(encoding='utf-8')
    if '<!-- BZCLAW_CODEX_INTERFACE_BEGIN -->' not in text or '<!-- BZCLAW_CODEX_INTERFACE_END -->' not in text:
        errors.append('AGENTS.md missing marker block')
try:
    data = json.loads((ROOT / 'docs/codex_interface/PROJECT_INTERFACE_CURRENT.json').read_text(encoding='utf-8'))
except Exception as exc:
    errors.append('PROJECT_INTERFACE_CURRENT.json parse failed: ' + str(exc))
    data = {}
if data:
    if not data.get('updated_at'):
        errors.append('updated_at missing')
    if not data.get('repo', {}).get('role'):
        errors.append('repo.role missing')
    if 'truth_hosts' not in data:
        errors.append('truth_hosts missing')
    if 'forbidden_actions' not in data:
        errors.append('forbidden_actions missing')
    if data.get('end_of_task_update_required') is not True:
        errors.append('end_of_task_update_required must be true')
if errors:
    print('FAIL')
    for e in errors:
        print('- ' + e)
    sys.exit(1)
print('PASS')
