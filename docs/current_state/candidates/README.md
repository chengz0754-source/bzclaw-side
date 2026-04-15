# Current State Candidate Staging Root

This folder receives deterministic current-state candidate objects only.

Allowed here:

- `*.candidate.json`
- `*.payload.json`
- `*.payload.md`

Forbidden here:

- logs
- Playwright artifacts
- raw callback payloads
- raw runtime outputs

Promoting a candidate into the active current-state hosts remains a separate
review step.
