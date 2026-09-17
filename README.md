# Insights (monorepo)

**Narrate** (Digests) + **Prove** (optional infra UI).  
Delivery: **email Digests** — no Decide UI.

## Docs

| Doc | Purpose |
|-----|---------|
| **[docs/strategy-recommendation.md](docs/strategy-recommendation.md)** | Strategy (start here) |
| [docs/insights-architecture.md](docs/insights-architecture.md) | Architecture |
| [docs/ui-setup-load-paths.md](docs/ui-setup-load-paths.md) | Console / keys setup |

## Layout

```
Narrate/     # Digest engine → Cloud Function + Scheduler
Prove/       # Optional hex map / cost API
terraform/   # BQ warehouse + digest Scheduler
docs/        # Three essential docs above
```

## Quick start (Narrate)

```bash
cd Narrate
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
bash scripts/deploy_digest_fn.sh   # after .env filled
```

Secrets: `Narrate/SECRETS.md`.

## Status

- [x] Digests + daily/weekly Scheduler  
- [ ] KIH billing export · YCA billing freshness  
- [ ] Looker board (optional)
