select warehouse_id, name, city, country_code
from {{ source('wms', 'warehouses') }}
