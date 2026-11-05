select customer_id, name, email, country_code, created_at
from {{ source('erp', 'customers') }}
