-- depends on {{ ref('session_hub') }}
-- depends on {{ ref('session_sat') }}
-- depends on {{ ref('session_campaign_link') }}
-- depends on {{ ref('stg_web__page_views') }}
select cast(null as varchar) as session_key, cast(null as varchar) as customer_key, cast(null as varchar) as campaign_key, cast(null as integer) as page_views
