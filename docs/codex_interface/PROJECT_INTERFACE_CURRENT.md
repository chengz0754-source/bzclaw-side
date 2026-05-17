# Project Interface Current

updated_at: 2026-05-18T07:43:39+08:00
run_id: r3a_bzclaw_side_remote_interface_sync_20260518

- expected repo: `chengz0754-source/bzclaw-side`
- local path: `E:\bzclaw-Bworkspace\bzclaw-side`
- role: `sellersprite_business_state_host`
- positioning: Machine B SellerSprite business state host for truth-pack / board / current-state / owner writeback.

## Not

- online execution bus
- worker host
- A-side control plane

## Truth Hosts

- README.md
- docs/state_sync_contract_current.md
- reports/latest_sellersprite_stage_status.json
- reports/sellersprite_truth_pack_current.json
- reports/selection/MASTER_PROGRESS_BOARD__20260412.csv
- templates/owner_manual_writeback/02__SELLERSPRITE_OWNER_STAGE_WRITEBACK_PACKET__20260413.csv
- reports/latest_sellersprite_owner_handoff.json
- reports/latest_sellersprite_owner_writeback_export.json

## Known Boundaries

- Current legal wording: SELLERSPRITE_FLOW_CLOSED__BUSINESS_NOT_PROMOTED.
- Forbidden wording unless active truth hosts change: SELLERSPRITE_CLOSED.
- Forbidden wording unless active truth hosts change: BUSINESS_PROMOTED.
- Current-stage SellerSprite flow closure does not imply business promotion.
- Owner-side manual writeback and promotion are next-stage owner/business flow, not this interface push.

## Forbidden Actions

- Do not claim SELLERSPRITE_CLOSED unless active truth hosts explicitly change.
- Do not claim BUSINESS_PROMOTED unless active truth hosts explicitly change.
- Do not treat this repo as online execution bus or A-side control plane.

Before replying `TASK COMPLETE`, update the interface or write `docs/codex_interface/last_task_interface_check.json`.
