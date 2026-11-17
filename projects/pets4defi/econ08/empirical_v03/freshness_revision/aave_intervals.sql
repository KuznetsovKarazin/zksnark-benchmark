-- Base Aave v3 Pool. Output consists exclusively of counts.
-- The requested window is [2026-05-21, 2026-11-17), UTC.
WITH events AS (
    SELECT "onBehalfOf" AS wallet, evt_tx_hash AS tx, evt_block_time AS moment
    FROM aave_v3_base.Pool_evt_Supply
    WHERE evt_block_time >= TIMESTAMP '2026-05-21' AND evt_block_time < TIMESTAMP '2026-11-17'
      AND contract_address = 0xa238dd80c259a72e81d7e4664a9801593f98d1c5
    UNION ALL
    SELECT "user", evt_tx_hash, evt_block_time
    FROM aave_v3_base.Pool_evt_Withdraw
    WHERE evt_block_time >= TIMESTAMP '2026-05-21' AND evt_block_time < TIMESTAMP '2026-11-17'
      AND contract_address = 0xa238dd80c259a72e81d7e4664a9801593f98d1c5
), dedup AS (
    SELECT wallet, tx, min(moment) AS moment FROM events GROUP BY 1, 2
), ranked AS (
    SELECT wallet, moment, count(*) OVER (PARTITION BY wallet) AS n,
           lag(moment) OVER (PARTITION BY wallet ORDER BY moment, tx) AS prev
    FROM dedup
), bins AS (
    SELECT n, date_diff('second',prev,moment) AS gap,
           CASE WHEN n=1 THEN '1' WHEN n=2 THEN '2' ELSE '3+' END AS cohort
    FROM ranked
)
SELECT 'wallet_count' AS metric, cohort AS bin, CAST(round(sum(1.0e0/n)) AS BIGINT) AS amount
FROM bins GROUP BY cohort
UNION ALL
SELECT 'gap_count_3plus', CASE WHEN gap=0 THEN 'same_timestamp' WHEN gap<3600 THEN 'under_1h'
     WHEN gap<21600 THEN '1h_to_6h' WHEN gap<86400 THEN '6h_to_1d' WHEN gap<604800 THEN '1d_to_7d'
     WHEN gap<2592000 THEN '7d_to_30d' ELSE '30d_or_more' END, count(*)
FROM bins WHERE n>=3 AND gap IS NOT NULL GROUP BY 2
