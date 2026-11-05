select md5(cast(order_id as varchar)) as hk_order, md5(concat_ws('|', ordered_at, status)) as hd_order, ordered_at, status, current_timestamp as load_ts
from {{ ref('stg_erp__orders') }}
