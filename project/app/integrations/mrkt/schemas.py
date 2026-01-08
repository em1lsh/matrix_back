from .._base_schemas import *


# Специфичный фильтр для получения товаров @mrkt
class MrktSalingFilter(SalingFilter):
    cursor: str = ""


# Специфичный ответ списка товаров на мркт
class MrktSalingsResponse(MarketSalings):
    cursor: str = ""
