select md5(cast(customer_id as varchar)) as hk_customer, md5(concat_ws('|', name, email, country_code)) as hd_customer, name, email, country_code, current_timestamp as load_ts
from {{ ref('stg_erp__customers') }}
