select contact_id, customer_id, channel, consent, updated_at
from {{ source('crm', 'contacts') }}
