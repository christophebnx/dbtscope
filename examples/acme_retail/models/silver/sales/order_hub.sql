select md5(cast(order_id as varchar)) as hk_order, order_id, current_timestamp as load_ts, 'erp' as record_source
from {{ ref('stg_erp__orders') }}
