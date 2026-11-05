select md5(concat_ws('|', campaign_id, contact_id)) as hk_campaign_contact, md5(cast(campaign_id as varchar)) as hk_campaign, md5(cast(contact_id as varchar)) as hk_contact, current_timestamp as load_ts
from {{ ref('stg_crm__campaign_members') }}
