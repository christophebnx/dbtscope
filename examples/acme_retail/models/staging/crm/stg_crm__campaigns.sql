select campaign_id, name, channel, starts_at, ends_at, budget
from {{ source('crm', 'campaigns') }}
