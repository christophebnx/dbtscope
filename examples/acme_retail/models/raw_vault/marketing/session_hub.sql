select md5(cast(session_id as varchar)) as hk_session, session_id, current_timestamp as load_ts, 'erp' as record_source
from {{ ref('stg_web__sessions') }}
