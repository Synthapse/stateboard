# Narrate secrets

Never commit Firebase / GCP / Notion / xAI keys into this monorepo.

Use:

- `Narrate/.env` (gitignored) — `GEMINI_API_KEY`, `XAI_API_KEY`
- `Decide/.env` (gitignored) — `REACT_APP_NOTION_TOKEN`, `REACT_APP_NOTION_DB_ID`
- `Decide/serverless/env.yaml` (gitignored) — copy from `env.yaml.example`

See also `*.env.example` files for variable names.

