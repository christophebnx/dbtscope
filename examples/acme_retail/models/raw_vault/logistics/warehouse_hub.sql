select md5(cast(warehouse_id as varchar)) as hk_warehouse, warehouse_id, current_timestamp as load_ts, 'erp' as record_source
from {{ ref('stg_wms__warehouses') }}
