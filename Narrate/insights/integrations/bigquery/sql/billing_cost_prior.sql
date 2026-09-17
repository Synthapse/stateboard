-- Prior-period cloud cost for delta.
-- Partition prune + usage_start_time filter (same window pattern as billing_cost.sql).
SELECT SUM(cost) AS cloud_cost_prior
FROM `{{billing_table}}`
WHERE project.id = @gcp_project
  AND _PARTITIONTIME >= TIMESTAMP(DATE_SUB(CURRENT_DATE(), INTERVAL {{lookback_days}} * 2 + 1 DAY))
  AND _PARTITIONTIME < TIMESTAMP(DATE_SUB(CURRENT_DATE(), INTERVAL {{lookback_days}} DAY))
  AND DATE(usage_start_time) BETWEEN
    DATE_SUB(CURRENT_DATE(), INTERVAL {{lookback_days}} * 2 DAY)
    AND DATE_SUB(CURRENT_DATE(), INTERVAL {{lookback_days}} + 1 DAY)
