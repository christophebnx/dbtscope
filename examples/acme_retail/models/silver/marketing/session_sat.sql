select md5(cast(session_id as varchar)) as hk_session, md5(concat_ws('|', started_at, device)) as hd_session, started_at, device, current_timestamp as load_ts
from {{ ref('stg_web__sessions') }}
