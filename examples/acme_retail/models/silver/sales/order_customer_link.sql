select md5(concat_ws('|', order_id, customer_id)) as hk_order_customer, md5(cast(order_id as varchar)) as hk_order, md5(cast(customer_id as varchar)) as hk_customer, current_timestamp as load_ts
from {{ ref('stg_erp__orders') }}
