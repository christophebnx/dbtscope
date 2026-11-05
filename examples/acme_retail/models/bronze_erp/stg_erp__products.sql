select product_id, label, category, supplier_id, list_price
from {{ source('erp', 'products') }}
