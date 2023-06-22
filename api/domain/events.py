from dataclasses import dataclass
from datetime import date
from api.domain.enums import OrderStatus


class Event:
    pass


@dataclass
class OrderStatusChanged(Event):
    order_id: str
    user_id: str
    total_cost: float
    status: OrderStatus
    consume_location: str
    order_items: list[dict]
    updated_at: date


@dataclass
class VariationDeleted(Event):
    variation_id: str


@dataclass
class VariationAdded(Event):
    variation_id: str
    product_id: str


@dataclass
class OrderCreated(Event):
    id: str
    status: OrderStatus
    updated_at: date
    user_id: str
    total_cost: float
    consume_location: str
    order_items: list
    created_at: date


# We might have other event relevant here, to track relevant info
# for our Analytics team.
