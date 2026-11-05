select warehouse_id, product_id, measured_at, quantity
from {{ source('wms', 'stock_levels') }}
