select md5(cast(invoice_id as varchar)) as hk_invoice, md5(concat_ws('|', issued_at, amount, currency)) as hd_invoice, issued_at, amount, currency, current_timestamp as load_ts
from {{ ref('stg_billing__invoices') }}
