select md5(concat_ws('|', order_id, store_id)) as hk_order_store, md5(cast(order_id as varchar)) as hk_order, md5(cast(store_id as varchar)) as hk_store, current_timestamp as load_ts
from {{ ref('stg_erp__orders') }}
