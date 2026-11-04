select order_line_id, order_id, product_id, quantity, unit_price
from {{ source('erp', 'order_lines') }}
