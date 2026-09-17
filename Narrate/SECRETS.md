# Narrate secrets

Never commit Firebase / GCP / Notion / xAI / SMTP / Langfuse keys into this monorepo.

Use (gitignored):

- `Narrate/.env` — `GEMINI_*`, `SMTP_*`, `DIGEST_*`, `BQ_*`, `LANGFUSE_*`, `CONTENTSQUARE_*`, `CLARITY_*`, DB URLs

Templates (safe to commit): `Narrate/.env.example`

Also ignored at repo root: `firebase.json`, SA JSON, `*.pem` / `*.key`, `terraform/terraform.tfvars`.

