-- depends on {{ ref('order_hub') }}
-- depends on {{ ref('order_sat') }}
-- depends on {{ ref('order_customer_link') }}
-- depends on {{ ref('order_store_link') }}
select cast(null as varchar) as order_key, cast(null as varchar) as customer_key, cast(null as varchar) as store_key, cast(null as date) as order_date, cast(null as varchar) as status
