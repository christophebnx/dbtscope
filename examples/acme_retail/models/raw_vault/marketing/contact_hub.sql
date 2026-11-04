select md5(cast(contact_id as varchar)) as hk_contact, contact_id, current_timestamp as load_ts, 'erp' as record_source
from {{ ref('stg_crm__contacts') }}
