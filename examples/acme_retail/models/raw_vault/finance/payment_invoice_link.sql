select md5(concat_ws('|', payment_id, invoice_id)) as hk_payment_invoice, md5(cast(payment_id as varchar)) as hk_payment, md5(cast(invoice_id as varchar)) as hk_invoice, current_timestamp as load_ts
from {{ ref('stg_billing__payments') }}
