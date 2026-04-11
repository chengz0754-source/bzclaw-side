# Nightly Orchestration Rules

## Canonical Role

- business execution owner: `E:\选品文件夹\amazon-selection-automation`
- governance/handoff owner: `E:\bzclaw-side`
- runner of record:
  - `scripts/run_nightly_selection_acceptance.py`
- current runner posture:
  - `dispatch_mode = shadow`
  - `execution_class = dry_run`

## Scheduling Rules

- every run must use a new `batch_id`
- every run must archive under `outputs/selection_runs/<batch_id>/`
- current working inputs are copied into `01_consumed_inputs/` before execution
- the nightly runner must never overwrite current operator inputs in place
- the nightly runner must never self-promote from `shadow` to `approved`
- the nightly runner must never enter publish, owner-approval, or formal-release semantics

## Required Bundle Outputs

Every accepted nightly batch must emit these files even when the business chain is blocked:

- `00_run_summary.md`
- `00_run_manifest.json`
- `02_generated_outputs/artifact_index.json`
- `03_logs/evidence_pack.json`
- `03_logs/shadow_run_receipt.json`
- `03_logs/nightly_acceptance_summary.json`

Minimum generated business outputs:

- `batch_queue_status.csv`
- `batch_run_summary.json`
- `03_候选市场与候选品初筛池.csv`
- `60_候选样品池.csv`
- `50_SIF流量结构补强.csv`
- `51_SIF关键词价值补强.csv`
- `52_SIF广告结构补强.csv`
- `53_SIF补强下推结果.csv`
- `61_待供应链核利清单.csv`

## Fail-Closed Rule

If a downstream step does not emit its expected files, nightly orchestration must synthesize blocked artifacts instead of aborting the whole run.

Current required fallback behaviors:

- if `collect_sif_detail_surface.py` does not emit `sif_detail_surface_probe.json` plus `50`, emit:
  - blocked fallback `sif_detail_surface_probe.json`
  - header-only `50`
  - run-local `03_logs/sif_surfaces/latest_detail_run.json`
- if `collect_sif_search_surface.py` does not emit `sif_search_surface_probe.json` plus `51/52`, emit:
  - blocked fallback `sif_search_surface_probe.json`
  - header-only `51`
  - header-only `52`
  - run-local `03_logs/sif_surfaces/latest_search_run.json`
- if `build_sif_enrichment_daytime_pack.py` does not emit `53/61` plus summary, emit:
  - blocked fallback `sif_enrichment_daytime_pack_summary.json`
  - header-only `53`
  - header-only `61`
  - placeholder `61.md`
  - run-local `03_logs/sif_enrichment/latest_run.json`

Fallback rules must:

- keep `status = HOLD`
- preserve real `reason_code`
- never fabricate `PASS`
- keep model receipt refs empty when no model call occurred

## Telemetry And Evidence Rules

- screenshots, auth incident JSON, page snapshots, workbooks, review markdown, and receipts are valid evidence refs
- auth/profile/storage-state secrets remain local-only and must not be attached as handoff payloads
- traces are optional but should be indexed when present
- if a nightly batch emits no fresh trace zip, the bundle may still pass telemetry completeness as long as the absence is stated explicitly

## DATA And B02 Boundary

- `DATA` and `B02` may be scheduled for B-side handoff only when their local execution hosts are repo-visible
- when hostlines are absent, B may only return:
  - contract intake note
  - expected object surface
  - missing host declaration
- nightly orchestration must not invent DATA/B02 execution results from package text alone

## Promotion Boundary

- nightly `PASS` means the shadow run passed its own acceptance gate
- nightly `HOLD` is still a valid ingestable bundle
- no nightly result can directly promote a lane to:
  - `business verified`
  - `formal publish`
  - `owner-approved closeout`

## Operator Actions On HOLD

- inspect `00_run_manifest.json`
- inspect `03_logs/evidence_pack.json`
- inspect row-level benchmark and market logs
- inspect auth-incident evidence when SellerSprite blocks
- decide whether the next action is:
  - upstream data repair
  - auth repair
  - queue/input correction
  - explicit owner review
