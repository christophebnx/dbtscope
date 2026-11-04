select refund_id, payment_id, refunded_at, amount, reason
from {{ source('billing', 'refunds') }}
