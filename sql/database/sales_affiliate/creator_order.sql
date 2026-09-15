with params as (
select
	$1::text as company,
	(now() - INTERVAL '30 day')::date AS start_date,
    (now() - INTERVAL '1 day')::date AS end_date
)
select
	p.company || ' - ' || concat_ws(
		'.',
		split_part(ecs.used_id, '.', 1),
		split_part(ecs.used_id, '.', 2),
		split_part(ecs.used_id, '.', 3)
	) as company_seller_used_id,
	ecs.day as day,
	'affiliate_api' as source,
	count(distinct ecs."day") as day_has_data,
	sum(ecs.quantity) as quantity,
	sum(ecs.revenue) as revenue,
	sum(ecs.commission_paid_estimated) as spend
from ecommerce_creator_sales ecs
cross join params p
where ecs."day" between p.start_date and p.end_date
group by 1,2