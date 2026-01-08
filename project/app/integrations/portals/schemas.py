from .._base_schemas import *


# Специфичный фильтр для получения товаров @portals
class PortalsSalingFilter(SalingFilter):
    limit: int = 50
    offset: int = 0
