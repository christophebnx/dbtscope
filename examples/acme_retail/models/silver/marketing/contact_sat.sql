select md5(cast(contact_id as varchar)) as hk_contact, md5(concat_ws('|', channel, consent)) as hd_contact, channel, consent, current_timestamp as load_ts
from {{ ref('stg_crm__contacts') }}
