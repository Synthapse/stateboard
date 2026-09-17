-- Fallback when the rolling lookback window is empty (export lag / gap).
-- Uses the latest {{lookback_days}} ending at MAX(usage_start_time) for the project.
WITH bounds AS (
  SELECT MAX(DATE(usage_start_time)) AS end_d
  FROM `{{billing_table}}`
  WHERE project.id = @gcp_project
)
SELECT
  SUM(cost) AS cloud_cost_usd,
  SUM(IF(LOWER(service.description) LIKE '%vertex%'
         OR LOWER(sku.description) LIKE '%gemini%'
         OR LOWER(sku.description) LIKE '%generative%', cost, 0)) AS ai_cost_usd
FROM `{{billing_table}}`, bounds
WHERE project.id = @gcp_project
  AND bounds.end_d IS NOT NULL
  AND DATE(usage_start_time) BETWEEN
    DATE_SUB(bounds.end_d, INTERVAL {{lookback_days}} - 1 DAY)
    AND bounds.end_d
