# Decide

On-demand Insights UI — product picker, Snapshot KPIs, generate narratives via **Narrate**, link to **Prove**.

Legacy: **Aureyo** frontend (+ `serverless/`).

## Run

```bash
cd Decide
cp src/config.example.json src/config.json   # local only; gitignored
npm install
npm start
```

Point env / config at Narrate (`:8000`) and Prove API as needed.

## Notes

- Do not commit `src/config.json` with secrets.
- PARKED: points/payments, Reddit/MAS, Notion serverless — not Digests v1.
