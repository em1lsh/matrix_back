from typing import Literal

BUY_ORDER_SORT_OPTIONS = {"created_at/asc", "created_at/desc", "price/asc", "price/desc"}

BuyOrderStatusEnum = Literal["ACTIVE", "FILLED", "CANCELLED"]
BuyOrderDealSourceEnum = Literal["AUTO_MATCH", "MANUAL_SELL"]