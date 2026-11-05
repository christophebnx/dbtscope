select order_id, customer_id, store_id, ordered_at, status
from {{ source('erp', 'orders') }}
