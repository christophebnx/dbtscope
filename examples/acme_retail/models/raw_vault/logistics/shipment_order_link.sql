select md5(concat_ws('|', shipment_id, order_id)) as hk_shipment_order, md5(cast(shipment_id as varchar)) as hk_shipment, md5(cast(order_id as varchar)) as hk_order, current_timestamp as load_ts
from {{ ref('stg_wms__shipments') }}
