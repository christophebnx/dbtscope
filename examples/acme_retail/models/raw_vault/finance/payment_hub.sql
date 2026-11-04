select md5(cast(payment_id as varchar)) as hk_payment, payment_id, current_timestamp as load_ts, 'erp' as record_source
from {{ ref('stg_billing__payments') }}
