select md5(cast(shipment_id as varchar)) as hk_shipment, md5(concat_ws('|', shipped_at, delivered_at)) as hd_shipment, shipped_at, delivered_at, current_timestamp as load_ts
from {{ ref('stg_wms__shipments') }}
