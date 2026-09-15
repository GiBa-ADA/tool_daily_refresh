-- SALES API V4 + V3
WITH params AS (
    SELECT 
        (now() - INTERVAL '30 day')::date AS start_date,
        (now() - INTERVAL '1 day')::date AS end_date,
        $1::text as company
),
country_tz AS (
    SELECT 
        used_id, 
        COALESCE(timezone, 'UTC') AS timezone 
    FROM user_management_country
),
base_items AS (
    SELECT
        ei.id,
        ei.day,
        ei.quantity,
        ei.s_net,
        ei.s_paid,
        ei.fees_paid,
        ei.shipping_fee_paid,
        ei.mkp_shipping_sub,
        ei.mkp_fees_sub,
        ei.mkp_onsite,
        ei.fk_status_used_id,
        ei.package_id,
        ei.fk_order_id,
        CASE 
            WHEN ei.source ILIKE 'v3%' THEN 'v3' 
            ELSE 'v4' 
        END AS source_type,
        split_part(ei.fk_sku_used_id, '.', 2) AS marketplace,
        p.company || ' - ' || concat_ws(
            '.',
            split_part(ei.fk_sku_used_id, '.', 1),
            split_part(ei.fk_sku_used_id, '.', 2),
            split_part(ei.fk_sku_used_id, '.', 3)
        ) AS company_seller_used_id,
        split_part(ei.seller_used_id, '.', 1) AS seller_country,
-- Order fields
        eo.payment_method,
        eo.paid_time,
        eo.order_type,
        eo.day AS order_day,
        COALESCE(ctz.timezone, 'UTC') AS timezone,
        p.start_date,
        p.end_date
    FROM ecommerce_item ei
    CROSS JOIN params p
    LEFT JOIN ecommerce_order eo
      ON split_part(ei.seller_used_id, '.', 2) IN ('LAZ', 'TTK')
     AND ei.fk_order_id = eo.id
     AND eo.day BETWEEN p.start_date AND p.end_date
    LEFT JOIN country_tz ctz
      ON split_part(ei.seller_used_id, '.', 2) IN ('LAZ', 'TTK')
     AND split_part(ei.seller_used_id, '.', 1) = ctz.used_id
    WHERE ei.day BETWEEN p.start_date AND p.end_date
)
-- 1. LAZADA - V3 (Simple logic, no filters)
SELECT
    b.company_seller_used_id AS company_seller_used_id,
    b.day AS day,
    'item' AS source,
    COUNT(DISTINCT b.day) AS day_has_data,
    SUM(b.quantity) AS quantity,
    SUM(
        COALESCE(b.s_net, 0)
        + COALESCE(b.fees_paid, 0)
        + COALESCE(b.shipping_fee_paid, 0)
        + COALESCE(b.mkp_shipping_sub, 0)
        + COALESCE(b.mkp_fees_sub, 0)
    ) AS revenue,
    NULL::text AS blank_col,
    'v3' AS source_type
FROM base_items b
WHERE b.marketplace = 'LAZ'
  AND b.source_type = 'v3'
GROUP BY 1, 2, 3, 7
UNION ALL
-- 2. LAZADA - V4 (Full logic & filters)
SELECT
    b.company_seller_used_id AS company_seller_used_id,
    CASE
        WHEN b.payment_method <> 'COD' AND b.paid_time IS NOT NULL 
            THEN (b.paid_time AT TIME ZONE b.timezone)::date
        ELSE b.day
    END AS day,
    'item' AS source,
    COUNT(
        DISTINCT CASE
            WHEN b.payment_method <> 'COD' AND b.paid_time IS NOT NULL 
                THEN (b.paid_time AT TIME ZONE b.timezone)::date
            ELSE b.day
        END
    ) AS day_has_data,
    SUM(b.quantity) AS quantity,
    SUM(
        COALESCE(b.s_net, 0)
        + COALESCE(b.fees_paid, 0)
        + COALESCE(b.shipping_fee_paid, 0)
        + COALESCE(b.mkp_shipping_sub, 0)
        + COALESCE(b.mkp_fees_sub, 0)
    ) AS revenue,
    NULL::text AS blank_col,
    'v4' AS source_type
FROM base_items b
WHERE b.marketplace = 'LAZ'
  AND b.source_type = 'v4'
  AND b.payment_method IS NOT NULL
  AND (COALESCE(b.fk_status_used_id, '') NOT ILIKE '%canceled.marketplace%' OR COALESCE(b.fk_status_used_id, '') NOT ILIKE '%cancelled.marketplace%')
  AND NOT (b.payment_method <> 'COD' AND b.paid_time IS NULL)
  AND (
        CASE
            WHEN b.payment_method IS NULL THEN b.day
            WHEN b.payment_method <> 'COD' AND b.paid_time IS NOT NULL 
                THEN (b.paid_time AT TIME ZONE b.timezone)::date
            ELSE b.day
        END
      ) BETWEEN b.start_date AND b.end_date
GROUP BY 1, 2, 3, 7
UNION ALL
-- 3. TIKTOK - V3 (Simple logic, no filters)
SELECT
    b.company_seller_used_id AS company_seller_used_id,
    b.day AS day,
    'item' AS source,
    COUNT(DISTINCT b.day) AS day_has_data,
    SUM(b.quantity) AS quantity,
    SUM(b.s_paid) AS revenue,
    NULL::text AS blank_col,
    'v3' AS source_type
FROM base_items b
WHERE b.marketplace = 'TTK'
  AND b.source_type = 'v3'
GROUP BY 1, 2, 3, 7
UNION ALL
-- 4. TIKTOK - V4 (Full logic, explicit package_id filter)
SELECT
    b.company_seller_used_id AS company_seller_used_id,
    CASE
        WHEN b.order_type IS NULL THEN b.day
        WHEN b.payment_method = 'Cash on delivery' THEN b.order_day
        WHEN b.paid_time IS NOT NULL THEN (b.paid_time AT TIME ZONE b.timezone)::date
        ELSE b.day
    END AS day,
    'item' AS source,
    COUNT(
        DISTINCT CASE
            WHEN b.order_type IS NULL THEN b.day
            WHEN b.payment_method = 'Cash on delivery' THEN b.order_day
            WHEN b.paid_time IS NOT NULL THEN (b.paid_time AT TIME ZONE b.timezone)::date
            ELSE b.day
        END
    ) AS day_has_data,
    SUM(b.quantity) AS quantity,
    SUM(b.s_paid) AS revenue,
    NULL::text AS blank_col,
    'v4' AS source_type
FROM base_items b
WHERE b.marketplace = 'TTK'
  AND b.source_type = 'v4'
  AND b.package_id IS NOT NULL
  AND COALESCE(b.order_type, '') <> 'SELLER_FUND_FREE_SAMPLE'
  AND (
        CASE
            WHEN b.order_type IS NULL THEN b.day
            WHEN b.payment_method = 'Cash on delivery' THEN b.order_day
            WHEN b.paid_time IS NOT NULL THEN (b.paid_time AT TIME ZONE b.timezone)::date
            ELSE b.day
        END
      ) BETWEEN b.start_date AND b.end_date
GROUP BY 1, 2, 3, 7
UNION ALL
-- 5. SHOPEE - V3 (Simple logic)
SELECT
    b.company_seller_used_id AS company_seller_used_id, 
    b.day AS day,
    'item' AS source,
    COUNT(DISTINCT b.day) AS day_has_data,
    SUM(b.quantity) AS quantity,
    SUM(b.s_paid) AS revenue,
    NULL::text AS blank_col,
    'v3' AS source_type
FROM base_items b 
WHERE b.marketplace = 'SHP'
  AND b.source_type = 'v3'
GROUP BY 1, 2, 3, 7
UNION ALL
-- 6. SHOPEE - V4 (Conditional Revenue Formula)
SELECT
    b.company_seller_used_id AS company_seller_used_id, 
    b.day AS day,
    'item' AS source,
    COUNT(DISTINCT b.day) AS day_has_data,
    SUM(b.quantity) AS quantity,
    SUM(
        CASE
            WHEN b.day >= DATE '2026-01-01'
                THEN COALESCE(b.s_net, 0) + COALESCE(b.mkp_onsite, 0)
            ELSE COALESCE(b.s_paid, 0)
        END
    ) AS revenue,
    NULL::text AS blank_col,
    'v4' AS version
FROM base_items b 
WHERE b.marketplace = 'SHP'
  AND b.source_type = 'v4'
GROUP BY 1, 2, 3, 7
UNION ALL
-- 7. OTHERS (Standard aggregation without version splitting)
SELECT 
    b.company_seller_used_id AS company_seller_used_id,
    b.day AS day,
    'item' AS source,
    COUNT(DISTINCT b.day) AS day_has_data,
    SUM(b.quantity) AS quantity,
    SUM(b.s_paid) AS revenue,
    NULL::text AS blank_col,
    b.source_type as version
FROM base_items b
WHERE b.marketplace NOT IN ('SHP', 'LAZ', 'TTK')
GROUP BY 1, 2, 3, 7, 8;
 