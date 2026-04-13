# ADS Phase1 Diagnostic Playbook

## Goal

Use this playbook to turn observed ads issues into a structured problem card
before any manual platform action is proposed.

## Minimum Evidence

- campaign and ad group identifiers
- date range and marketplace
- spend, sales, orders, clicks, impressions, CTR, CPC, CVR, ACOS, ROAS
- change history or recent experiments
- budget, bid, placement, targeting, and search term context

## Diagnostic Flow

1. Confirm the scope: campaign, ad group, keyword or product target, and date
   window.
2. Classify the symptom:
   - low impressions
   - clicks without orders
   - rising ACOS
   - spend concentration on weak terms
   - budget throttling
3. Check the likely cause:
   - bid too low or too high
   - match type or query mismatch
   - negative keyword conflict
   - listing conversion weakness
   - budget cap or placement distortion
4. Write the diagnosis in a problem card with evidence, guardrails, and open
   risks.

## Common Diagnosis Patterns

### Low Impressions

- check budget depletion and impression share
- compare bid versus median top-of-search range
- review overly narrow negatives and paused states

### High Spend, Low Orders

- split search term waste from listing conversion weakness
- inspect placement modifiers that may overpay for weak traffic
- isolate broad targets that need harvest or exclusion decisions

### Good CTR, Weak CVR

- verify listing price, offer health, inventory, and review context
- avoid aggressive bid raises until the offer issue is understood

## Required Output

The diagnostic stage must end with `templates/ads_manual_adjustment/ads_problem_card.template.md`
filled for the target issue.
