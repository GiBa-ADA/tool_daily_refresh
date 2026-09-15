-- AUTOMATED
WITH params AS (
    SELECT
        (now() - INTERVAL '30 day')::date AS start_date,
        (now() - INTERVAL '1 day')::date AS end_date,
        $1::text as company
)
SELECT 
    p.company || ' - ' || rsm.seller_used_id AS company_seller_used_id,
    rsm."day",
    count(distinct rsm."day") as day_has_data,
    SUM(
        CASE 
            WHEN rsm.metric_type = 'item_count'
            THEN rsm.metric_value
            ELSE NULL
        END
    ) AS quantity,
    SUM(
        CASE 
            WHEN rsm.metric_type = 'gmv'
            THEN rsm.metric_value
            ELSE NULL
        END
    ) AS revenue,
    SUM(
        CASE 
            WHEN rsm.metric_type = 'page_view'
            THEN rsm.metric_value
            ELSE NULL
        END
    ) AS page_view
FROM raw_seller_metrics rsm
CROSS JOIN params p
WHERE rsm."day" BETWEEN p.start_date AND p.end_date
GROUP BY 1,2
ORDER BY 2;

