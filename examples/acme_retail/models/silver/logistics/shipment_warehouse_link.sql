select md5(concat_ws('|', shipment_id, warehouse_id)) as hk_shipment_warehouse, md5(cast(shipment_id as varchar)) as hk_shipment, md5(cast(warehouse_id as varchar)) as hk_warehouse, current_timestamp as load_ts
from {{ ref('stg_wms__shipments') }}
