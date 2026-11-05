-- depends on {{ ref('invoice_hub') }}
-- depends on {{ ref('invoice_sat') }}
-- depends on {{ ref('invoice_order_link') }}
select cast(null as varchar) as invoice_key, cast(null as varchar) as order_key, cast(null as date) as issued_date, cast(null as decimal(12,2)) as amount, cast(null as varchar) as currency
