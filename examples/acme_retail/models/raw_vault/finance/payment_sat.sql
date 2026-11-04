select md5(cast(payment_id as varchar)) as hk_payment, md5(concat_ws('|', paid_at, amount, method)) as hd_payment, paid_at, amount, method, current_timestamp as load_ts
from {{ ref('stg_billing__payments') }}
