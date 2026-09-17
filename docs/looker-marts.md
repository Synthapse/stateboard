# Looker Studio on Insights marts

Flat BigQuery views under `cognispace.marts.looker_*` so Looker Studio can chart
without digging into `metrics_json`.

## One-time: create views

```bash
cd Narrate
DIGEST_USE_FIXTURE=0 python -c "from insights import looker_views; print(looker_views())"
# or HTTP: ?action=looker_views
```

| View | Source mart | Useful fields |
|------|-------------|----------------|
| `marts.looker_growth` | `growth` | sessions, users, sessions_delta_pct |
| `marts.looker_product` | `product` | event_total, top_event_name/count |
| `marts.looker_customer` | `customer` | dau, wau_engagement_sum |
| `marts.looker_ai` | `ai` | total_cost_usd, trace_count |
| `marts.looker_cost` | `cost` | cloud_cost_usd (Lindle today) |
| `marts.looker_reliability` | `reliability` | services_up/down, exception_count, failing_services |
| `marts.looker_feature` | `fct_events` ⨝ `dim_feature` | feature_name, event_count, users by day × product |

## Connect Looker Studio

1. Open [Looker Studio](https://lookerstudio.google.com/) → **Create** → **Data source** → **BigQuery**
2. Project: `cognispace` → Dataset: `marts` → pick a `looker_*` view  
   (or **Custom query** in location **EU**)
3. Authorize with an account that has `bigquery.dataViewer` on `cognispace`
4. Create a report; add charts with:
   - Dimension: `period_date`, `product`
   - Metrics: e.g. `sessions`, `dau`, `cloud_cost_usd`, `services_up`

## Suggested pages

1. **Growth** — time series of `sessions` / `users` by `product` (`looker_growth`)
2. **Product** — `event_total` + table of `top_event_name` (`looker_product`)
3. **Customer** — `dau` by product (`looker_customer`)
4. **AI $** — `total_cost_usd` + `trace_count` (`looker_ai`)
5. **Cloud $** — `cloud_cost_usd` (`looker_cost`; empty until KIH/YCA billing export)
6. **Reliability** — `services_up` / `services_down` / `exception_count` (`looker_reliability`)

Filter control: `product` (kih | lindle | yca).

## Refresh

Views always read live mart tables. Keep marts fresh via `daily_pipeline` / Scheduler.
Re-run `looker_views()` only if view SQL changes.

## Error Reporting (exceptions beyond health fails)

APIs enabled on `dr-kiwi-app`, `cognispace`, `adroit-router-462912-n6`.
ADC identity needs `roles/errorreporting.viewer` on each product GCP project
(so `healthchecks()` can list groupStats → `fct_exceptions`).
