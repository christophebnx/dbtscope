select md5(concat_ws('|', shipment_id, carrier_id)) as hk_shipment_carrier, md5(cast(shipment_id as varchar)) as hk_shipment, md5(cast(carrier_id as varchar)) as hk_carrier, current_timestamp as load_ts
from {{ ref('stg_wms__shipments') }}
