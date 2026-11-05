-- depends on {{ ref('stg_wms__stock_levels') }}
-- depends on {{ ref('dim_product') }}
-- depends on {{ ref('dim_warehouse') }}
select cast(null as varchar) as warehouse_key, cast(null as varchar) as product_key, cast(null as date) as measured_date, cast(null as integer) as quantity
