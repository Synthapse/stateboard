# Narrate

Digest / narrative engine (FastAPI). Turns an `InsightsSnapshot` into weekly/monthly Digests (Slack / email) and on-demand reports for **Decide**.

Legacy: **Raporting**.

## Run

```bash
cd Narrate
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Manual digest (when endpoint exists):

```bash
# POST /v1/insights/digest/run?product=kih&cadence=weekly
```

## Secrets

Never commit Firebase / GCP service-account JSON. See [SECRETS.md](./SECRETS.md).

## North star

Cloud Scheduler → BQ Snapshot → Narrate → Slack / email for `kih` · `lindle` · `yca`.
