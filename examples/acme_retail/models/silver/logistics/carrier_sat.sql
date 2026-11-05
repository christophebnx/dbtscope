select md5(cast(carrier_id as varchar)) as hk_carrier, md5(concat_ws('|', name, service_level)) as hd_carrier, name, service_level, current_timestamp as load_ts
from {{ ref('stg_wms__carriers') }}
