# Agent Rules For Semantic Filter Local

## Scope Boundary

- Only handle `M03_niche_shortlist -> M03_semantic_filtered`.
- Only prepare a semantic benchmark queue for retained rows.
- Do not enter Step2 benchmark analysis.
- Do not make final launch, supply-chain, IP, or SIF decisions.

## Model Boundary

- Use only local Ollama.
- Use only `http://localhost:11434/v1/`.
- Use only model `qwen3:4b-instruct`.
- Do not call OpenAI cloud or any other external service.

## Decision Boundary

- Do not overturn Step1 hard gates.
- Do not turn `DROP` rows back into keepers.
- Only semantic-filter rows where `step1_status == PASS_TO_STEP2`.
- Only use labels `KEEP`, `REVIEW`, and `DROP_LOW_MATCH`.
- Be conservative: if uncertain, choose `REVIEW`, not `DROP_LOW_MATCH`.

## File Boundary

- Read the latest `M03_niche_shortlist__*.xlsx|csv` by default.
- Write outputs only under `outputs/<run_id>/`.
- Write logs only under `logs/<run_id>/`.
- Do not write result files into the root workspace.
- Do not overwrite an existing run unless `--overwrite` is explicit.

## Evidence Boundary

- Keep all original rows in the filtered output.
- Preserve upstream Step1 reasons.
- Record semantic reasons and confidence explicitly.
- Keep non-`PASS_TO_STEP2` rows visible with `final_keep_flag = False`.
