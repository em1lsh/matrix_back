from .._base_schemas import *


class TonnelSalingFilter(SalingFilter):
    page: int = 1
    limit: int = 30
