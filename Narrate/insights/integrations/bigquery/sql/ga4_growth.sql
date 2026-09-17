-- GA4 growth for one product (last @lookback_days ending yesterday).
-- Params substituted by snapshot_builder: {{ga4_events}}, {{lookback_days}}
SELECT
  COUNTIF(event_name = 'session_start') AS sessions,
  COUNT(DISTINCT user_pseudo_id) AS users
FROM `{{ga4_events}}`
WHERE _TABLE_SUFFIX BETWEEN
  FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL {{lookback_days}} DAY))
  AND FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))
