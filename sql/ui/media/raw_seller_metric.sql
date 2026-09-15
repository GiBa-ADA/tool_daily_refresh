-- AUTOMATED
WITH params AS (
    SELECT
        (now() - INTERVAL '30 day')::date AS start_date,
        (now() - INTERVAL '1 day')::date AS end_date,
        $1::text as company
)
SELECT 
    p.company || ' - ' || rsm.seller_used_id as company_seller_used_id,
    rsm."day",
    split_part(rsm.metric_type, '__', 2) as sub_channel,
    count(distinct rsm.day) as day_has_data,
    SUM(
        CASE 
            WHEN split_part(rsm.metric_type, '__', 1) = 'ad_impression'
            THEN rsm.metric_value
            ELSE 0
        END
    ) AS ad_impression,
    SUM(
        CASE 
            WHEN split_part(rsm.metric_type, '__', 1) = 'ad_spend'
            THEN rsm.metric_value
            ELSE 0
        END
    ) AS ad_spend,
    SUM(
        CASE 
            WHEN split_part(rsm.metric_type, '__', 1) = 'ad_revenue'
            THEN rsm.metric_value
            ELSE 0
        END
    ) AS ad_revenue,
    SUM(
        CASE 
            WHEN split_part(rsm.metric_type, '__', 1) = 'ad_visits'
            THEN rsm.metric_value
            ELSE 0
        END
    ) AS ad_visits
FROM raw_seller_metrics rsm
CROSS JOIN params p
where
  split_part(rsm.metric_type, '__', 2) != ''
  and (rsm."day" BETWEEN p.start_date AND p.end_date)
GROUP BY 1,2,3
ORDER BY 1,2;


 