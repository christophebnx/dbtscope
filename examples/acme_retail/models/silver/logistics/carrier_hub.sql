select md5(cast(carrier_id as varchar)) as hk_carrier, carrier_id, current_timestamp as load_ts, 'erp' as record_source
from {{ ref('stg_wms__carriers') }}
