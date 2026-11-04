-- depends on {{ ref('payment_hub') }}
-- depends on {{ ref('payment_sat') }}
-- depends on {{ ref('payment_invoice_link') }}
-- depends on {{ ref('stg_billing__refunds') }}
-- depends on {{ ref('currency_rates') }}
select cast(null as varchar) as payment_key, cast(null as varchar) as invoice_key, cast(null as date) as paid_date, cast(null as decimal(12,2)) as amount_eur, cast(null as decimal(12,2)) as refunded_eur
