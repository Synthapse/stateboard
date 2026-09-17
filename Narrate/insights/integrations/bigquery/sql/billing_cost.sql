-- Cloud cost USD for a GCP project over the lookback window (Billing Detailed export).
-- {{billing_table}} = cognispace.raw_billing.gcp_billing_export_resource_v1_<ACCOUNT>
-- _PARTITIONTIME prune keeps scanned bytes small as the export table grows.
SELECT
  SUM(cost) AS cloud_cost_usd,
  SUM(IF(LOWER(service.description) LIKE '%vertex%'
         OR LOWER(sku.description) LIKE '%gemini%'
         OR LOWER(sku.description) LIKE '%generative%', cost, 0)) AS ai_cost_usd
FROM `{{billing_table}}`
WHERE project.id = @gcp_project
  AND _PARTITIONTIME >= TIMESTAMP(DATE_SUB(CURRENT_DATE(), INTERVAL {{lookback_days}} + 1 DAY))
  AND _PARTITIONTIME < TIMESTAMP(CURRENT_DATE())
  AND DATE(usage_start_time) BETWEEN
    DATE_SUB(CURRENT_DATE(), INTERVAL {{lookback_days}} DAY)
    AND DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
