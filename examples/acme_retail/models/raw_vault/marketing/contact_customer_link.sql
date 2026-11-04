select md5(concat_ws('|', contact_id, customer_id)) as hk_contact_customer, md5(cast(contact_id as varchar)) as hk_contact, md5(cast(customer_id as varchar)) as hk_customer, current_timestamp as load_ts
from {{ ref('stg_crm__contacts') }}
