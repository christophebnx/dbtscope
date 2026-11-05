select md5(cast(warehouse_id as varchar)) as hk_warehouse, md5(concat_ws('|', name, city)) as hd_warehouse, name, city, current_timestamp as load_ts
from {{ ref('stg_wms__warehouses') }}
