-- TRAFFIC SELLER
WITH params AS (
    SELECT
        (now() - INTERVAL '30 day')::date AS start_date,
        (now() - INTERVAL '1 day')::date AS end_date,
        $1::text as company
)
SELECT
    p.company || ' - ' || concat_ws(
        '.',
        split_part(eest.fk_seller_used_id , '.', 1),
        split_part(eest.fk_seller_used_id, '.', 2),
        split_part(eest.fk_seller_used_id, '.', 3)
    ) AS company_seller_used_id,
    eest.day AS day,
    'export_seller_traffic' as source,
    count(distinct eest."day" ) as day_has_data,
    null AS quantity,
    null AS revenue,
    sum(eest.page_view) as page_view
FROM ecommerce_export_seller_traffic eest 
CROSS JOIN params p
WHERE eest.day BETWEEN p.start_date AND p.end_date
GROUP by 1, 2;
