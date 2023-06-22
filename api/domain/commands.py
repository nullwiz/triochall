from dataclasses import dataclass
from api.domain.enums import OrderStatus, ConsumeLocation
from api.domain.models import OrderItem


class Command:
    pass


@dataclass
class CustomizeProduct(Command):
    name: str
    price: float
    description: str
    variations: list


@dataclass
class GetAllProducts(Command):
    page: int


@dataclass
class CreateOrder(Command):
    user_id: str
    consume_location: ConsumeLocation
    order_items: list[OrderItem]


@dataclass
class CancelOrder(Command):
    order_id: str
    user_id: str


@dataclass
class UpdateOrderStatus(Command):
    id: str
    status: OrderStatus


@dataclass
class GetOrder(Command):
    id: str


@dataclass
class GetOrders(Command):
    page: int
    filters: dict
    page_size: int = 10


@dataclass
class GetOrdersForCustomer(Command):
    page: int
    user_id: str
    page_size: int = 10


@dataclass
class CreateProduct(Command):
    name: str
    price: float
    description: str
    variations: list


@dataclass
class GetProduct(Command):
    id: str


@dataclass
class UpdateProduct(Command):
    id: str
    name: str | None
    price: float | None
    description: str | None
    variations: list = None


@dataclass
class DeleteProduct(Command):
    id: str


@dataclass
class CreateVariation(Command):
    product_id: str
    name: str
    price: float


@dataclass
class UpdateVariation(Command):
    variation_id: str
    name: str | None
    price: float | None
    product_id: str


@dataclass
class DeleteVariation(Command):
    product_id: str
    variation_id: str


@dataclass
class CreateUser(Command):
    email: str
    password: str
    role: str


@dataclass
class GetUserByEmail(Command):
    email: str


@dataclass
class HealthCheck(Command):
    pass


# Auth
@dataclass
class AuthenticateUser(Command):
    email: str
    password: str


# Catalog
@dataclass
class GetCatalog(Command):
    page: int


# POC


@dataclass
class NotifyOrderSale(Command):
    pass
