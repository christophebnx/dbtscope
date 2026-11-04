select payment_id, invoice_id, paid_at, amount, method
from {{ source('billing', 'payments') }}
