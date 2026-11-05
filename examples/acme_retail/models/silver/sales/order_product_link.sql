select md5(concat_ws('|', order_id, product_id)) as hk_order_product, md5(cast(order_id as varchar)) as hk_order, md5(cast(product_id as varchar)) as hk_product, current_timestamp as load_ts
from {{ ref('stg_erp__order_lines') }}
