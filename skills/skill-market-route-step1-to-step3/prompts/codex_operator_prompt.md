# Codex Operator Prompt For SellerSprite Market Route Step1 To Step3

Use this skill when upstream `M02_market_cleaned` outputs already exist and the goal is to advance the SellerSprite market line to `K02_keyword_shortlist`.

Rules:

- Do not rebuild `skill-market-route-m01-to-m02`
- Do not modify upstream raw evidence
- Do not make final product launch decisions
- Use config files for thresholds and weights
- Persist status codes to tables and manifests
- If `benchmark_raw` or `keyword_raw` files are missing, emit queue files and stop in the correct `WAIT_*` state

Primary command:

```powershell
python .\skill-market-route-step1-to-step3\scripts\run_market_route_pipeline.py --root .
```
