select md5(cast(customer_id as varchar)) as hk_customer, customer_id, current_timestamp as load_ts, 'erp' as record_source
from {{ ref('stg_erp__customers') }}
