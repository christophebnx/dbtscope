select md5(concat_ws('|', product_id, supplier_id)) as hk_product_supplier, md5(cast(product_id as varchar)) as hk_product, md5(cast(supplier_id as varchar)) as hk_supplier, current_timestamp as load_ts
from {{ ref('stg_erp__products') }}
