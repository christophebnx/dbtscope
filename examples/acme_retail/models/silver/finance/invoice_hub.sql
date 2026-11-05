select md5(cast(invoice_id as varchar)) as hk_invoice, invoice_id, current_timestamp as load_ts, 'erp' as record_source
from {{ ref('stg_billing__invoices') }}
