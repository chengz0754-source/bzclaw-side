# Models

This folder reserves the model-call placement for Machine B.

Current baseline:

- Preferred provider: local Ollama
- Default model: `qwen3:4b-instruct`
- OpenAI-compatible base URL: `http://127.0.0.1:11434/v1`
- Default API key value for local use: `ollama`

Do not claim model availability beyond what has been verified in the reports.
`configs/model.json` is the source of truth for provider wiring.
