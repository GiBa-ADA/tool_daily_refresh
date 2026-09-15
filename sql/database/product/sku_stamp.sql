-- SKU STAMP 
WITH 
params as (
	select 
		(CURRENT_DATE - INTERVAL '30 day') as start_date,
		CURRENT_DATE as end_date,
        $1::text AS company
),
sku AS (
    SELECT
        DATE(es.updated AT TIME ZONE COALESCE(umc.timezone, 'UTC')) AS day,
        substring(es.used_id FROM '^[^\.]+\.[^\.]+\.[^\.]+') AS seller_used_id,
        es.source,
        COUNT(*) AS sku_count
    FROM ecommerce_sku es
    LEFT JOIN user_management_country umc
        ON umc.used_id = split_part(es.used_id, '.', 1)
    WHERE es.updated >= (CURRENT_DATE - INTERVAL '1 day')
    GROUP BY
        DATE(es.updated AT TIME ZONE COALESCE(umc.timezone, 'UTC')),
        substring(es.used_id FROM '^[^\.]+\.[^\.]+\.[^\.]+'),
        es.source
),
sku_stamp AS (
    SELECT
        DATE(ess.updated AT TIME ZONE COALESCE(umc.timezone, 'UTC')) AS day,
        substring(es.used_id FROM '^[^\.]+\.[^\.]+\.[^\.]+') AS seller_used_id,
        ess.source,
        COUNT(*) AS sku_stamp_count
    FROM ecommerce_sku_stamp ess
    join ecommerce_sku es on es.id = ess.fk_sku_id
    LEFT JOIN user_management_country umc
        ON umc.used_id = split_part(es.used_id, '.', 1)
    WHERE ess.updated >= (CURRENT_DATE - INTERVAL '1 day')
    GROUP BY
        DATE(ess.updated AT TIME ZONE COALESCE(umc.timezone, 'UTC')),
        substring(es.used_id FROM '^[^\.]+\.[^\.]+\.[^\.]+'),
        ess.source
)
SELECT
    p.company || ' - ' || s.seller_used_id as company_seller_used_id,
    TO_CHAR(s.day, 'YYYY-MM-DD')::date AS day,
    'ecommerce_sku' AS source,
    count(distinct s.day) as day_has_data,
    sum(s.sku_count) AS sku,
    sum(ss.sku_stamp_count) AS stamp
FROM sku s
CROSS JOIN params p
JOIN sku_stamp ss
    ON s.day = ss.day
   AND s.seller_used_id = ss.seller_used_id
   AND s.source = ss.source
WHERE s.sku_count > 0
  AND ss.sku_stamp_count > 0
  AND s.day between p.start_date and p.end_date
GROUP BY
    1,2