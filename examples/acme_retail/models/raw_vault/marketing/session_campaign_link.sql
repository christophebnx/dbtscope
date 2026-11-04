select md5(concat_ws('|', session_id, campaign_id)) as hk_session_campaign, md5(cast(session_id as varchar)) as hk_session, md5(cast(campaign_id as varchar)) as hk_campaign, current_timestamp as load_ts
from {{ ref('stg_web__sessions') }}
