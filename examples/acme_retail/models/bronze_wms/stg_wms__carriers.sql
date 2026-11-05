select carrier_id, name, service_level
from {{ source('wms', 'carriers') }}
