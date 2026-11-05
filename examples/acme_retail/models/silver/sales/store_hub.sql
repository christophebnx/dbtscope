select md5(cast(store_id as varchar)) as hk_store, store_id, current_timestamp as load_ts, 'erp' as record_source
from {{ ref('stg_erp__stores') }}
