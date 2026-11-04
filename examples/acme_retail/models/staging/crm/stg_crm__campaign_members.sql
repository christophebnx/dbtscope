select campaign_id, contact_id, responded_at
from {{ source('crm', 'campaign_members') }}
