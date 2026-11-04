select md5(cast(shipment_id as varchar)) as hk_shipment, shipment_id, current_timestamp as load_ts, 'erp' as record_source
from {{ ref('stg_wms__shipments') }}
