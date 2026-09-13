# Insights (monorepo)

**Decide** + **Narrate** + **Prove** in one repo (formerly Stateboard).  
Legacy repos Aureyo / Raporting should be archived after deploy is green.

**North star:** weekly/monthly Digests (Slack / email) from BigQuery for `kih` · `lindle` · `yca`.

## Layout

```
Decide/                 # on-demand UI (ex Aureyo)
Narrate/                # Digest engine FastAPI (ex Raporting)
Prove/
  web/                  # hex map / cost / health UI
  Stateboard.Api/       # .NET API
  Stateboard.Core/      # HCL → graph, cost
packages/tf-cost/       # shared TS helpers
```

Still three deployables from one git tree.

## Quick start

### Prove API + web

```bash
dotnet run --project Prove/Stateboard.Api --urls http://localhost:5281
npm install && npm run dev
```

### Narrate

```bash
cd Narrate
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Secrets: see `Narrate/SECRETS.md` — never commit Firebase/SA JSON.

### Decide

```bash
cd Decide
cp src/config.example.json src/config.json   # local only; gitignored
npm install && npm start
```

## Merge status

- [x] Import Decide + Narrate; folder layout `Decide/` `Narrate/` `Prove/`
- [ ] Wire Digest schedule → Slack/email
- [ ] Rename GitHub repo `stateboard` → `insights` (when ready)
- [ ] Archive Synthapse/Aureyo + Synthapse/Raporting

## Deploy

Today: `stateboard.synthapse.xyz` / Cloud Run `stateboard-api` on cognispace.  
See `docs/deploy-gcp.md`.
