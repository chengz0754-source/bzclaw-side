# Research Failure Taxonomy

## Scope

This taxonomy covers the current B-side SellerSprite research family:

- STEP1 Product Research
- STEP4 Benchmark / Competitor

It exists to normalize intake and evidence handling without replacing the native script-level `reason_code`.

This document does not:

- turn workbook download into final business closure
- hide auth/profile governance boundaries
- create a second object language beside the B5 execution pack

## Principles

- Preserve native reason codes. The normalized class is an intake aid, not a replacement.
- Separate collector failure from builder failure. A passed workbook download can still end in a blocked business pack.
- Keep evidence requirements explicit. Every failure class must say what proof must survive.
- Allow shadow intake. A pack can be real and still stay `shadow_candidate` when the latest truth is unstable.

## Native Status Model

- `PASS`
  - The relevant collector or builder stage completed and emitted the expected evidence refs.
- `BLOCKED`
  - Final execution receipt state when a required stage cannot complete or cannot be trusted for ingest.
- Step status values that may still appear inside run summaries:
  - `PASS`
  - `FAIL`
  - `WAIT`
  - `HOLD`

Interpretation rules:

- collector `PASS` plus builder `FAIL` is not business closure
- workbook presence alone is not `PASS`
- screenshots and traces are evidence aids, not status truth by themselves

## Failure Classes

| failure_class | stage_band | representative_reason_codes | meaning | required_evidence | receipt_outcome | retry_policy |
| --- | --- | --- | --- | --- | --- | --- |
| `INPUT_CONTEXT_INVALID` | intake / pre-page | `BENCHMARK_SITE_UNSUPPORTED`, `BENCHMARK_DAYS_UNSUPPORTED`, and equivalent context-resolution failures before page open | Input contract is incomplete or unsupported before a live SellerSprite action can start. | input profile ref, route or context ref, validation message | `BLOCKED` | Fix input contract first; do not retry blind. |
| `AUTH_PROFILE_BLOCK` | auth / session bootstrap | `SELLERSPRITE_AUTH_REQUIRED` | Surface redirected to login or replay material was insufficient to enter the page/export-log flow. | collector summary, auth incident screenshot ref, `auth_surface_family`, replay attempted flag | `BLOCKED` | Retry only after profile/auth replay repair. |
| `QUERY_SURFACE_BLOCK` | page interaction | `PRODUCT_QUERY_INPUT_NOT_VISIBLE`, `PRODUCT_QUERY_BUTTON_NOT_VISIBLE`, `PRODUCT_RESULT_ROWS_MISSING`, `PRODUCT_RESULT_CHECKBOX_NOT_VISIBLE`, `PRODUCT_EXPORT_BUTTON_NOT_VISIBLE`, `PRODUCT_EXPORT_BUTTON_DISABLED`, `BENCHMARK_QUERY_INPUT_NOT_VISIBLE`, `BENCHMARK_QUERY_BUTTON_NOT_VISIBLE`, `BENCHMARK_RESULT_TABLE_NOT_VISIBLE`, `BENCHMARK_RESULT_ROW_NOT_FOUND`, `BENCHMARK_RESULT_CHECKBOX_NOT_VISIBLE` | The target page opened but the expected query/result/export controls were not reliably usable. | summary step timeline, page URL/title, blocking screenshot ref | `BLOCKED` | Retry only after selector or page-state review. |
| `OVERLAY_MODAL_BLOCK` | modal / overlay | `RESULT_PAGE_BLOCKED_BY_OVERLAY`, `UNEXPECTED_MODAL_BLOCKING_ACTION`, `EXPORT_DIALOG_NOT_VISIBLE`, `EXPORT_CONFIRM_BUTTON_NOT_VISIBLE` | A visible overlay, modal, or unexpected interstitial blocked the intended export action. | screenshot ref, step record, selector or modal note | `BLOCKED` | Retry after UI guard adjustment or replay stabilization. |
| `EXPORT_LOG_BLOCK` | export-log task tracking | `EXPORT_LOG_TASK_NOT_FOUND`, `EXPORT_LOG_STATUS_TIMEOUT`, `EXPORT_LOG_STATUS_FAILED`, `PRODUCT_EXPORT_STATUS_FAILED` | Export trigger occurred or was attempted, but the export-log task could not be found, did not finish, or failed. | baseline task context, matched task name/status, poll step history, screenshot ref if redirected | `BLOCKED` | Bounded retry is allowed after confirming export-log freshness and auth state. |
| `DOWNLOAD_VALIDATION_BLOCK` | download handoff | `EXPORT_DOWNLOAD_BUTTON_NOT_VISIBLE`, `EXPORT_FILE_NOT_DOWNLOADED` | Export-log reported a downloadable artifact, but the file could not be validated as downloaded. | expected filename prefix, download dir ref, step timeline, file existence check | `BLOCKED` | Retry after storage/download directory review. |
| `WORKBOOK_PARSE_BLOCK` | parse | `PRODUCT_EXPORT_WORKBOOK_PARSE_FAILED`, `EXPORT_WORKBOOK_PARSE_FAILED` | Workbook exists, but parsing into raw JSON failed or produced unusable structure. | workbook ref, parser exception, sheet names, header snapshot if available | `BLOCKED` | Retry after parser fix or workbook format review. |
| `UPSTREAM_SEED_BLOCK` | builder precondition | `STEP1_GATE_MISSING`, `STEP1_SEED_MISSING`, `STEP1_PASS_SEED_MISSING`, `STEP3_GATE_MISSING`, `STEP3_CLEANED_MISSING`, `STEP3_PASS_SEED_MISSING` | Benchmark or downstream build could not start because the required upstream PASS seed or gate file was missing. | upstream artifact refs, upstream gate status, build summary ref | `BLOCKED` | Repair upstream artifact chain before retry. |
| `BUILD_ARTIFACT_BLOCK` | builder | `PRODUCT_RUN_SUMMARY_MISSING`, `PRODUCT_EXPORT_NOT_PASS`, `PRODUCT_RAW_ARTIFACT_MISSING`, `PRODUCT_RAW_ROWS_EMPTY`, `PRODUCT_SEED_ROWS_EMPTY`, `BENCHMARK_RUN_SUMMARY_MISSING`, `BENCHMARK_EXPORT_NOT_PASS`, `BENCHMARK_RAW_ARTIFACT_MISSING`, `BENCHMARK_RAW_ROWS_EMPTY` | Collector evidence exists or partially exists, but canonical builder outputs cannot be trusted or emitted. | collector summary ref, raw artifact ref if present, build summary ref, missing-output note | `BLOCKED` | Retry after repairing raw artifact integrity or build logic. |
| `UNHANDLED_RUNTIME_ERROR` | any | `PRODUCT_RESEARCH_UNHANDLED_ERROR`, `BENCHMARK_EXPORT_UNHANDLED_ERROR`, and equivalent uncaught runtime exits | Execution stopped through an unclassified exception path. | exception message, current step, page URL/title, screenshot ref if present | `BLOCKED` | Investigate before retry; do not normalize away the exception. |

## Non-Fatal Evidence Variations

These do not automatically change the execution pack into business failure, but they must stay visible in notes/evidence:

| variation_class | native_signal | handling_rule |
| --- | --- | --- |
| `OPTIONAL_UI_VARIATION` | `PRODUCT_EXPORT_IMAGE_OPTIONAL_MISSING` | Record the UI variation in evidence, but do not downgrade a run that otherwise completed. |
| `OPTIONAL_TRACE_ABSENCE` | no trace zip captured | Keep trace refs optional. Screenshot and summary evidence can still be sufficient. |
| `PATH_HYGIENE_DRIFT` | product screenshots observed under benchmark screenshot tree, or other runtime path drift | Treat as storage hygiene debt only. Do not rewrite object ownership because of path placement drift. |

## Evidence Requirements By Class

- `INPUT_CONTEXT_INVALID`
  - keep the input profile ref, route/context ref, and the exact validation message
- `AUTH_PROFILE_BLOCK`
  - keep auth screenshot ref, auth surface family, replay attempted flag, and final redirect URL/title
- `QUERY_SURFACE_BLOCK`
  - keep page URL/title, blocking screenshot ref, and the failed step name
- `OVERLAY_MODAL_BLOCK`
  - keep modal/overlay screenshot ref and the selector or visible text note when available
- `EXPORT_LOG_BLOCK`
  - keep baseline task context, matched task name/status, poll timeline, and any redirect/auth note
- `DOWNLOAD_VALIDATION_BLOCK`
  - keep expected filename prefix, download dir ref, and file existence result
- `WORKBOOK_PARSE_BLOCK`
  - keep workbook ref, parser exception, sheet names, and header sample when available
- `UPSTREAM_SEED_BLOCK`
  - keep missing upstream file refs and the latest upstream gate status
- `BUILD_ARTIFACT_BLOCK`
  - keep collector summary ref, raw artifact ref if present, build summary ref, and missing-output list
- `UNHANDLED_RUNTIME_ERROR`
  - keep exception message, step name, page snapshot, and any screenshot ref

## Receipt Emission Rules

### Collector blocked before workbook

Emit:

- collector receipt with `status=BLOCKED`
- failure record
- evidence pack refs pointing to summary, step timeline, and screenshots

Do not emit:

- workbook artifact
- raw parse artifact
- canonical artifact set

### Collector passed, builder blocked

Emit:

- collector receipt
- workbook artifact ref
- raw parse artifact ref if it exists
- builder receipt with `status=BLOCKED`
- failure record

Intake posture:

- default `shadow_candidate`
- never rewrite this state into final benchmark or research closure

### Collector passed, builder passed

Emit:

- collector receipt
- workbook artifact ref
- raw parse artifact ref
- canonical artifact set
- builder receipt
- execution receipt with `status=PASS`

Intake posture:

- `approved_execution_candidate`
- still bounded to artifact/business-execution scope only

### Older PASS exists, latest rerun unstable

Emit:

- keep the older real PASS pack reviewable
- mark the latest intake posture as `shadow_candidate`
- preserve the latest blocker reason code instead of hiding it behind the older PASS

## Native Codes Worth Preserving

### Product-side

- `SELLERSPRITE_AUTH_REQUIRED`
- `PRODUCT_QUERY_INPUT_NOT_VISIBLE`
- `PRODUCT_QUERY_BUTTON_NOT_VISIBLE`
- `PRODUCT_RESULT_ROWS_MISSING`
- `PRODUCT_RESULT_CHECKBOX_NOT_VISIBLE`
- `PRODUCT_EXPORT_BUTTON_NOT_VISIBLE`
- `PRODUCT_EXPORT_BUTTON_DISABLED`
- `PRODUCT_EXPORT_STATUS_FAILED`
- `PRODUCT_EXPORT_WORKBOOK_PARSE_FAILED`
- `EXPORT_LOG_TASK_NOT_FOUND`
- `EXPORT_LOG_STATUS_TIMEOUT`
- `EXPORT_DOWNLOAD_BUTTON_NOT_VISIBLE`
- `PRODUCT_EXPORT_IMAGE_OPTIONAL_MISSING`

### Benchmark-side

- `SELLERSPRITE_AUTH_REQUIRED`
- `BENCHMARK_QUERY_INPUT_NOT_VISIBLE`
- `BENCHMARK_QUERY_BUTTON_NOT_VISIBLE`
- `BENCHMARK_RESULT_TABLE_NOT_VISIBLE`
- `BENCHMARK_RESULT_ROW_NOT_FOUND`
- `BENCHMARK_RESULT_CHECKBOX_NOT_VISIBLE`
- `RESULT_PAGE_BLOCKED_BY_OVERLAY`
- `EXPORT_DIALOG_NOT_VISIBLE`
- `EXPORT_CONFIRM_BUTTON_NOT_VISIBLE`
- `UNEXPECTED_MODAL_BLOCKING_ACTION`
- `EXPORT_LOG_TASK_NOT_FOUND`
- `EXPORT_LOG_STATUS_TIMEOUT`
- `EXPORT_LOG_STATUS_FAILED`
- `EXPORT_DOWNLOAD_BUTTON_NOT_VISIBLE`
- `EXPORT_FILE_NOT_DOWNLOADED`
- `EXPORT_WORKBOOK_PARSE_FAILED`

### Build-side

- `PRODUCT_RUN_SUMMARY_MISSING`
- `PRODUCT_EXPORT_NOT_PASS`
- `PRODUCT_RAW_ARTIFACT_MISSING`
- `PRODUCT_RAW_ROWS_EMPTY`
- `PRODUCT_SEED_ROWS_EMPTY`
- `BENCHMARK_RUN_SUMMARY_MISSING`
- `BENCHMARK_EXPORT_NOT_PASS`
- `BENCHMARK_RAW_ARTIFACT_MISSING`
- `BENCHMARK_RAW_ROWS_EMPTY`
- `STEP1_GATE_MISSING`
- `STEP1_SEED_MISSING`
- `STEP1_PASS_SEED_MISSING`
- `STEP3_GATE_MISSING`
- `STEP3_CLEANED_MISSING`
- `STEP3_PASS_SEED_MISSING`

## Current Intake Judgment On 2026-04-11

- Product research family:
  - observed real collector `PASS` plus build `PASS` samples exist
  - current normalized intake posture can be `approved_execution_candidate`
- Benchmark / competitor family:
  - observed real collector `PASS` plus build `PASS` samples exist
  - normalize to `approved_execution_candidate` when the current run truth stays stable
  - downgrade to `shadow_candidate` whenever the latest rerun reintroduces export-log or replay instability
- Combined research pack:
  - attachable now as an objectized business execution family
  - not equivalent to final product verdict, final competitor verdict, or end-to-end business closure
