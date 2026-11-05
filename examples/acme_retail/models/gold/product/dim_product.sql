-- depends on {{ ref('product_hub') }}
-- depends on {{ ref('product_sat') }}
-- depends on {{ ref('product_supplier_link') }}
-- depends on {{ ref('supplier_sat') }}
select cast(null as varchar) as product_key, cast(null as varchar) as label, cast(null as varchar) as category, cast(null as varchar) as supplier_name, cast(null as decimal(12,2)) as list_price
