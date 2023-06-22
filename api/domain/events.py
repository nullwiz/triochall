from dataclasses import dataclass
from datetime import date, timedelta
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


@dataclass
class OrderSale(Event):
    product_id: str = "SomeProductId"
    url: str = "https://www.google.com"
    price = 100.0
    discount: float = 50.0
    sale_price: float = 50.0
    sale_start: date = date.today()
    sale_end: date = date.today() + timedelta(days=7)


# We might have other event relevant here, to track relevant info
# for our Analytics team.
