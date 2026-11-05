-- depends on {{ ref('campaign_contact_link') }}
-- depends on {{ ref('contact_customer_link') }}
-- depends on {{ ref('stg_crm__campaign_members') }}
select cast(null as varchar) as campaign_key, cast(null as varchar) as customer_key, cast(null as timestamp) as responded_at
