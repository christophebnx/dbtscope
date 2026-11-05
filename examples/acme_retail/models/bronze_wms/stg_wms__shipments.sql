select shipment_id, order_id, warehouse_id, carrier_id, shipped_at, delivered_at
from {{ source('wms', 'shipments') }}
