# Interface Update Protocol Current

Before any future Codex business task replies `TASK COMPLETE`, it must choose exactly one path.

## A. Interface Changed

Update:

- `docs/codex_interface/STATUS_CURRENT.md`
- `docs/codex_interface/STATUS_CURRENT.json`
- `docs/codex_interface/REUSE_POINTERS_CURRENT.md`
- `docs/codex_interface/NEXT_TASK_ENTRY_CURRENT.md`
- `docs/codex_interface/PROJECT_INTERFACE_CURRENT.json`

If the task creates a reusable workflow, add:

- `docs/codex_interface/reuse/<FLOW_NAME>_REUSE_POINTER_CURRENT.md`

## B. Interface Unchanged

Write `docs/codex_interface/last_task_interface_check.json`:

```json
{
  "task_id": "",
  "checked_at": "",
  "interface_change_required": false,
  "reason": "",
  "files_checked": []
}
```

## Hard Rule

Do not reply `TASK COMPLETE` until A or B is complete.
