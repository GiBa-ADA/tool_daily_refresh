with params as (
select
 	(now() - INTERVAL '30 day')::date AS start_date,
    (now() - INTERVAL '1 day')::date AS end_date,
    $1::text as company
),
content_map as (
	select
		 distinct t.fk_seller_used_id, t.fk_content_used_id,
		 day as year_month,
		 p.company as company,
		 null::float8 as revenue,
		 SUM(product_impression)::int4 as product_impression,
		 null::int4 as content_impression
	from ecommerce_content_seller_traffic t
	cross join params p
	where t.day between p.start_date and p.end_date 
	group by 1,2,3,4
),
all_metrics as (
	-- product impression
	select * from content_map
	union all
	-- revenue
	select
		 fk_seller_used_id,
		 fk_content_used_id,
		 day,
		 p.company as company,
		 SUM(revenue),
		 null,
		 null
	from ecommerce_content_seller_sales
	cross join params p
	where day between p.start_date and p.end_date
	group by 1,2,3,4
	union all
	-- content impression
	select
		 c.fk_seller_used_id,
		 e.fk_content_used_id,
		 day,
		 p.company as company,
		 null,
		 null,
		 SUM(impression)
	from ecommerce_content_engagement e
	join content_map c on c.fk_content_used_id = e.fk_content_used_id
		and c.year_month = day
	cross join params p
	where day between p.start_date and p.end_date
	group by 1,2,3,4
)
select
	 company || ' - ' || fk_seller_used_id as company_seller_used_id,
	 year_month as day,
	 case
		  when fk_content_used_id like '%.L-%'
		            then 'TikTok Content Live'
		  when fk_content_used_id like '%.V-%'
		            then 'TikTok Content Video'
	 else 'TikTok Seller Center Content Other'
	 end as sub_channel,
	 count(distinct year_month) as day_has_data,
	 SUM(revenue) as revenue,
	 SUM(product_impression) as product_impression,
	 SUM(content_impression) as content_impression
from all_metrics
group by 1,2,3;