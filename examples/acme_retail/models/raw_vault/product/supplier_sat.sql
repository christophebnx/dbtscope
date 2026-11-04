select md5(cast(supplier_id as varchar)) as hk_supplier, md5(concat_ws('|', name, country_code)) as hd_supplier, name, country_code, current_timestamp as load_ts
from {{ ref('stg_erp__suppliers') }}
