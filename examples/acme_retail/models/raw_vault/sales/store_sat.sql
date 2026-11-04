select md5(cast(store_id as varchar)) as hk_store, md5(concat_ws('|', name, city, country_code)) as hd_store, name, city, country_code, current_timestamp as load_ts
from {{ ref('stg_erp__stores') }}
