-- SALES SELLER
WITH params AS (
    SELECT
        (now() - INTERVAL '30 day')::date AS start_date,
        (now() - INTERVAL '1 day')::date AS end_date,
        $1::text as company
)
SELECT
    p.company || ' - ' || concat_ws(
        '.',
        split_part(eess.fk_seller_used_id, '.', 1),
        split_part(eess.fk_seller_used_id, '.', 2),
        split_part(eess.fk_seller_used_id, '.', 3)
    ) AS company_seller_used_id,
    eess."day" AS day,
    'export_seller_sales' as source,
    count(distinct eess."day" ) as day_has_data,
    SUM(eess.quantity) AS quantity,
    SUM(eess.revenue ) AS revenue,
    null as page_view
FROM ecommerce_export_seller_sales eess
CROSS JOIN params p
WHERE eess.day BETWEEN p.start_date AND p.end_date
GROUP by 1, 2;
