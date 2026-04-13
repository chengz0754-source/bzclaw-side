# B_RETURN_PACKET_DEMOTION_LEDGER

| packet_or_folder | role | status | why demoted | may_still_be_read_for_history |
|---|---|---|---|---|
| `E:/bzclaw-exchange/02_B_TO_A_OUTBOX/20260413-0636-B-A-ADS_PHASE1_SIGNAL/` | legacy pre-V2 signal packet | `DEMOTED_VISIBLE` | visible on B but incomplete for the current consume target because it lacks the required `REVIEW_SUBSET/` and is superseded by `20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY-V2` | `YES` |
| `E:/bzclaw-exchange/02_B_TO_A_OUTBOX/20260413-0319-B-A-ADS_PHASE1_EXECUTION-READY` | historical old exchange main package family | `DEMOTED_NOT_VISIBLE` | the old exchange-full-package family is obsolete after canonical hosting moved under `E:/bzclaw-side/returns/ads_phase1/...` plus V2 exchange signal routing; this folder is not currently visible on B | `YES` |

## Current visibility notes
- `DEPRECATED_PACKET_SET_CURRENT.md` names `Z:/02_B_TO_A_OUTBOX/20260413-0636-B-A-ADS_PHASE1_SIGNAL/`; on this B machine that share alias is not mounted, while the corresponding local exchange folder above is visible
- the named historical folder `E:/bzclaw-exchange/02_B_TO_A_OUTBOX/20260413-0319-B-A-ADS_PHASE1_EXECUTION-READY` is not visible in the current repo-visible state

## Active packet
- exact active packet path: `E:/bzclaw-side/returns/ads_phase1/20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY`
- exact exchange signal path: `E:/bzclaw-exchange/02_B_TO_A_OUTBOX/20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY-V2`

## Default consume rule
- default future consume target: `E:/bzclaw-exchange/02_B_TO_A_OUTBOX/20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY-V2/`
- canonical main-return pointer: `E:/bzclaw-side/returns/ads_phase1/20260413-210213-B-A-ADS_PHASE1_EXECUTION-READY`
- demoted folders may still be read for history only and must not silently outrank the active V2 packet pair
