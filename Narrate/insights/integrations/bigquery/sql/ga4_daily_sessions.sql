-- Daily sessions + users from GA4 events_* (one product).
-- Substituted: {{ga4_events}}, {{lookback_days}}, {{product}}
SELECT
  PARSE_DATE('%Y%m%d', _TABLE_SUFFIX) AS period_date,
  '{{product}}' AS product,
  COUNTIF(event_name = 'session_start') AS sessions,
  COUNT(DISTINCT user_pseudo_id) AS users
FROM `{{ga4_events}}`
WHERE _TABLE_SUFFIX BETWEEN
  FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL {{lookback_days}} DAY))
  AND FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))
GROUP BY 1, 2
ORDER BY 1
