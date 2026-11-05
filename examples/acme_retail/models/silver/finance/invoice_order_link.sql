select md5(concat_ws('|', invoice_id, order_id)) as hk_invoice_order, md5(cast(invoice_id as varchar)) as hk_invoice, md5(cast(order_id as varchar)) as hk_order, current_timestamp as load_ts
from {{ ref('stg_billing__invoices') }}
