select supplier_id, name, country_code
from {{ source('erp', 'suppliers') }}
