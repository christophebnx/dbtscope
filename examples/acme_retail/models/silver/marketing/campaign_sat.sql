select md5(cast(campaign_id as varchar)) as hk_campaign, md5(concat_ws('|', name, channel, budget)) as hd_campaign, name, channel, budget, current_timestamp as load_ts
from {{ ref('stg_crm__campaigns') }}
