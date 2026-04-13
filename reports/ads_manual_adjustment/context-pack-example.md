# Ads Phase1 Context Pack

- context_pack_id: `ads-phase1-context-example`
- marketplace: `US`
- account_name: `Manual Review Sandbox`
- campaign_name: `SP | Squeeze Toys | Core`
- ad_group_name: `Exact Winners`
- objective: `Reduce waste while protecting converting traffic.`
- date_range: `2026-04-01` to `2026-04-12`

## Observations

- Search term spend is concentrated on broad traffic with weak order contribution.
- Two exact targets still convert and should be protected.
- Top of search modifier is amplifying weak CPC on low-intent terms.

## Diagnostic Summary

Traffic quality drift is causing spend leakage. The campaign still has recoverable exact-match demand, so the first batch should cut waste and preserve proven targets.

## Guardrails

- Do not increase budget in this batch.
- Do not adjust more than three targets at once.
- Require approval before any manual upload.

## Proposed Actions

- Add one phrase negative for an irrelevant search pattern.
- Lower the bid on a weak broad target by 15 percent.
- Keep the winning exact target active with no bid increase yet.
