with params as (
	select 
		(now() - INTERVAL '30 day')::date AS start_date,
    (now() - INTERVAL '1 day')::date AS end_date,
    $1::text as company
)
SELECT
    p.company || ' - ' || REGEXP_REPLACE(ma.used_id, '^([^.]+\.){3}([^.]+\.[^.]+\.[^.]+).*', '\2') as company_seller_used_id,
    mpt.day AS day,
    m.name AS sub_channel,
    count(distinct mpt.day) as day_has_data,
    SUM(mpt.ad_impression)      AS ad_impression,
    SUM(mpt.spend)              AS ad_spend,
    SUM(mpt.mkp_revenue_store)  AS ad_revenue,
    SUM(mpt.mkp_session_direct) AS ad_visits
FROM media_advertising_platform m
cross join params p
JOIN media_ad ma
  ON substring(ma.used_id from '^([^.]+\.[^.]+\.[^.]+)') =
     substring(m.used_id  from '^([^.]+\.[^.]+\.[^.]+)')
JOIN media_paid_traffic mpt
  ON mpt.fk_ad_id = ma.id
WHERE mpt.day BETWEEN p.start_date and p.end_date 
	and substring(ma.used_id FROM '^([^.]+\.[^.]+\.[^.]+)') IN (
    SELECT DISTINCT substring(ma.used_id FROM '^([^.]+\.[^.]+\.[^.]+)')
    FROM media_ad ma
)
GROUP by
	1,2,3
ORDER BY
  2 DESC