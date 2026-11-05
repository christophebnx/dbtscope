select session_id, customer_id, campaign_id, started_at, device
from {{ source('web', 'sessions') }}
