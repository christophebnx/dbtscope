-- depends on {{ ref('order_product_link') }}
-- depends on {{ ref('fct_orders') }}
-- depends on {{ ref('stg_erp__order_lines') }}
select cast(null as varchar) as order_line_key, cast(null as varchar) as order_key, cast(null as varchar) as product_key, cast(null as integer) as quantity, cast(null as decimal(12,2)) as net_amount
