select md5(cast(campaign_id as varchar)) as hk_campaign, campaign_id, current_timestamp as load_ts, 'erp' as record_source
from {{ ref('stg_crm__campaigns') }}
