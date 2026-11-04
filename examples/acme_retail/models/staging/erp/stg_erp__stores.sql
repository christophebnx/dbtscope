select store_id, name, city, country_code, opened_at
from {{ source('erp', 'stores') }}
