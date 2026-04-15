# State Sync Contract (Current)

## Purpose

This contract freezes `chengz0754-source/bzclaw-side` as the Machine B business
state host.

This repo may host only repo-visible business state for:

- truth pack
- board
- current state
- owner writeback

This repo must not be rewritten into:

- an online execution bus
- a worker host
- a package-owned dispatcher
- an A-side API mirror

## Repo Role Freeze

| Plane | Repo | Role | Must not move here |
| --- | --- | --- | --- |
| A | `chengz0754-source/bzclaw` | Only control plane, approval plane, dispatch truth, and final verification owner | B-side runtime, local-only evidence, owner writeback materialization |
| B execution | `chengz0754-source/amazon-selection-automation` | Runtime execution, local models, Playwright, receipts, manifests, and raw evidence | Final business truth, current-state hosting, owner promotion |
| B state | `chengz0754-source/bzclaw-side` | Business state host for truth-pack, board, current-state, and owner writeback | Online dispatch, worker leasing, callback bus, transport truth |

## Existing Truth Priority

The current repo-visible truth priority is already explicit in
`reports/latest_sellersprite_stage_status.json` and is frozen here as:

1. `reports/sellersprite_truth_pack_current.json`
2. `contracts/sellersprite_current_stage_closure_contract_v1.json`
3. `reports/selection/MASTER_PROGRESS_BOARD__20260412.csv`
4. `reports/selection/SELLERSPRITE_POST_STAGE_OPEN_DEBT_REGISTER__20260413.csv`
5. `templates/owner_manual_writeback/02__SELLERSPRITE_OWNER_STAGE_WRITEBACK_PACKET__20260413.csv`
6. derived current-state hosts such as `README.md` and
   `skills/skill_sellersprite_four_line_runtime_registry.md`

Runtime outputs may support review, but they do not outrank the git-visible
truth chain above.

## Sync Object Roles And Entrypoints

| Object family | Active repo-visible host | Role | Sync rule |
| --- | --- | --- | --- |
| `truth_pack` | `reports/sellersprite_truth_pack_current.json` | Canonical fact bundle for current SellerSprite business-state truth | Repo-visible JSON only; no raw runtime payloads |
| `board` | `reports/selection/MASTER_PROGRESS_BOARD__20260412.csv` | Current progress board and per-line status host | Repo-visible CSV only; not a queue, not a scheduler |
| `current_state` | `README.md` and `reports/latest_sellersprite_stage_status.json` | Deterministic current-state render for human and machine readers | Must mirror repo truth; must not imply business promotion |
| `owner_writeback` | `templates/owner_manual_writeback/02__SELLERSPRITE_OWNER_STAGE_WRITEBACK_PACKET__20260413.csv`, `reports/latest_sellersprite_owner_handoff.json`, and `reports/latest_sellersprite_owner_writeback_export.json` | Manual owner/business handoff and externalized writeback export | Manual-only next-stage surface; externalized from current-stage closure |

The following documentation-only entrypoints are reserved to make those roles
explicit without changing the active host paths:

- `docs/truth_pack/README.md`
- `docs/current_state/README.md`
- `reports/board/README.md`
- `docs/owner_writeback/README.md`

## Candidate Sync Entry Layer

Automated candidate ingest from `chengz0754-source/amazon-selection-automation`
is limited to the following staging roots:

| Candidate family | Staging root | Rule |
| --- | --- | --- |
| `truth_pack_candidate` | `docs/truth_pack/candidates/` | Candidate truth only; active truth-pack host stays `reports/sellersprite_truth_pack_current.json` |
| `board_candidate` | `reports/board/candidates/` | Candidate board objects only; not a queue, not a scheduler |
| `current_state_candidate` | `docs/current_state/candidates/` | Candidate current-state objects only; active hosts stay `README.md` and `reports/latest_sellersprite_stage_status.json` |

`owner_writeback` remains manual-only next-stage material and is excluded from
the automated candidate ingest surface.

## What May Sync Into Git

Only the following input classes may sync into git truth:

| Input class | Allowed into git | Rule |
| --- | --- | --- |
| repo-visible state contracts | Yes | Contracts, schemas, and role-freeze docs may live under `docs/` and `contracts/` |
| truth pack | Yes | Curated repo-visible truth-pack JSON such as `reports/sellersprite_truth_pack_current.json` |
| board | Yes | Repo-visible board CSV/MD that carries stable status meaning |
| deterministic current-state render | Yes | `README.md` and `reports/latest_sellersprite_stage_status.json` may mirror repo truth |
| candidate truth objects | Yes | Only via the frozen candidate staging roots and `contracts/state_sync_candidate_input_contract_v1.json` |
| owner writeback packet and handoff | Yes | Manual-only owner packet template, repo-visible handoff JSON, and deterministic externalized export JSON |
| redacted evidence summaries | Yes | Only after they are rewritten into stable, reviewable repo-visible state objects |

## What Must Never Sync Into Git

The following may support runtime execution or review, but they must never
become git truth directly:

- `outputs/**`
- `logs/**`
- `runs/**`
- `playwright/auth/**`
- `playwright/profiles/**`
- `playwright/screenshots/**`
- `playwright/traces/**`
- raw workbooks, raw downloads, raw screenshots, raw traces, and other
  local-only evidence
- `.env`, tokens, cookies, storage state, and any other secret material
- A/B exchange queue payloads, callback bodies, worker leases, and transport
  temp files
- online dispatch instructions, worker heartbeats, or API request/response
  traffic

Standardized Machine B run receipts, manifests, and run summaries may be kept
only as provenance refs inside candidate metadata. They must not be committed
here as raw runtime bodies or treated as active git truth by themselves.

If a runtime artifact matters, summarize it into a reviewed repo-visible state
object first. Never commit the raw runtime object itself as business truth.

## Hard Boundaries

- `git/repo visible state ONLY`
- runtime outputs and git truth stay separate
- `FLOW_CLOSED` may coexist with `BUSINESS_NOT_PROMOTED`
- receipt visibility does not equal business promotion
- B local model and B local runtime may support evidence but may not declare
  final business success
- mirror refresh remains manual after repo-visible change

## Non-Goals

- no online worker
- no A-machine API integration
- no package-owned dispatch bus
- no reclassification of this repo into the execution sidecar

## Change Control

If sync object roles, truth priority, or active host paths change, update in
the same commit:

- `docs/state_sync_contract_current.md`
- `docs/state_sync_io_contract.schema.json`
- `README.md`

Do not make silent breaking changes to the state-sync contract.
