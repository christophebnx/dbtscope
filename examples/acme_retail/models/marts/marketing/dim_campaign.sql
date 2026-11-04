-- depends on {{ ref('campaign_hub') }}
-- depends on {{ ref('campaign_sat') }}
select cast(null as varchar) as campaign_key, cast(null as varchar) as name, cast(null as varchar) as channel, cast(null as decimal(12,2)) as budget
