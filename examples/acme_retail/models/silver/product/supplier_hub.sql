select md5(cast(supplier_id as varchar)) as hk_supplier, supplier_id, current_timestamp as load_ts, 'erp' as record_source
from {{ ref('stg_erp__suppliers') }}
