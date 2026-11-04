select md5(cast(product_id as varchar)) as hk_product, md5(concat_ws('|', label, category, list_price)) as hd_product, label, category, list_price, current_timestamp as load_ts
from {{ ref('stg_erp__products') }}
