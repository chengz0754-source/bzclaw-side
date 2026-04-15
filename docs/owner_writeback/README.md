# Owner Writeback Contract Entry

This folder documents the frozen owner-writeback role for `bzclaw-side`.

The current active repo-visible owner-writeback hosts remain:

- `templates/owner_manual_writeback/02__SELLERSPRITE_OWNER_STAGE_WRITEBACK_PACKET__20260413.csv`
- `reports/latest_sellersprite_owner_handoff.json`
- `reports/latest_sellersprite_owner_writeback_export.json`

Owner writeback is manual-only next-stage material. Do not turn it into an
automatic runtime writeback channel.

There is no automated candidate ingest root for owner writeback in this repo.

The deterministic update path is `scripts/run_sellersprite_stage_closure.py`,
which renders current-state hosts first and then externalizes owner writeback
from repo-visible truth.
