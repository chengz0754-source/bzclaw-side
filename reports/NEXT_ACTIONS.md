# NEXT ACTIONS

1. Keep the dedicated SellerSprite login bootstrap flow on the existing sidecar
   profile and save refreshed authenticated state into
   `playwright/auth/sellersprite.storage_state.json` instead of the user's
   default Chrome profile.
2. Define the next-round operator input contract under `inputs/`, including the
   exact form/template fields Machine A will provide and the output naming
   convention Machine B will consume.
3. Implement the first live SellerSprite export automation path in this
   sidecar: launch profile, restore auth, navigate to the export page, download
   into a fixed folder, and write a run manifest under `runs/`.
4. Add a thin model adapter script that reads `configs/model.json` and can make
   one reversible probe call to the configured provider without embedding
   provider assumptions in business code.
5. Decide whether the project should stay Python-first for Playwright or also
   install Node LTS for JS-based tooling; do not assume npm-based scripts are
   available until Node is explicitly installed.
