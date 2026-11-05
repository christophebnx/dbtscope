-- depends on {{ ref('customer_hub') }}
-- depends on {{ ref('customer_sat') }}
-- depends on {{ ref('contact_customer_link') }}
-- depends on {{ ref('contact_sat') }}
select cast(null as varchar) as customer_key, cast(null as varchar) as name, cast(null as varchar) as email, cast(null as varchar) as country_code, cast(null as boolean) as has_consent
