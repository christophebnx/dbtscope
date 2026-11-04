select page_view_id, session_id, url, viewed_at
from {{ source('web', 'page_views') }}
