-- Prior-period sessions for delta (lookback window shifted back one period).
SELECT
  COUNTIF(event_name = 'session_start') AS sessions_prior
FROM `{{ga4_events}}`
WHERE _TABLE_SUFFIX BETWEEN
  FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL {{lookback_days}} * 2 DAY))
  AND FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL {{lookback_days}} + 1 DAY))
