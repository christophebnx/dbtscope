select invoice_id, order_id, issued_at, amount, currency
from {{ source('billing', 'invoices') }}
