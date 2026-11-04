-- depends on {{ ref('shipment_hub') }}
-- depends on {{ ref('shipment_sat') }}
-- depends on {{ ref('shipment_order_link') }}
-- depends on {{ ref('shipment_warehouse_link') }}
-- depends on {{ ref('shipment_carrier_link') }}
select cast(null as varchar) as shipment_key, cast(null as varchar) as order_key, cast(null as varchar) as warehouse_key, cast(null as varchar) as carrier_key, cast(null as integer) as lead_time_days
