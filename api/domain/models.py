import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from api.domain.enums import UserRole, ConsumeLocation, OrderStatus
from . import events


class UnableToCreateUser(Exception):
    pass


@dataclass
class User:
    email: str
    password: str
    role: UserRole
    _events: List[events.Event] = field(default_factory=list)
    id: str | None = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self):
        if not self.id:
            object.__setattr__(self, "id", str(uuid.uuid4()))

    def __eq__(self, other):
        if not isinstance(other, User):
            return False
        return other.id == self.id

    def __hash__(self):
        return hash(self.id)

    def append_event(self, event: events.Event):
        self._events.append(event)

    def pop_events(self) -> List[events.Event]:
        events = self._events
        self._events = []
        return events


@dataclass
class Variation:
    name: str
    price: float
    product_id: str
    price: float
    id: str | None = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
    is_deleted: int = 0

    def __post_init__(self):
        if not self.id:
            object.__setattr__(self, "id", str(uuid.uuid4()))

    def __hash__(self):
        return hash(self.id)


@dataclass
class Product:
    name: str
    description: str
    price: float
    variations: List[Variation] = field(default_factory=list)
    id: str | None = None
    is_deleted: int = 0
    _events: List[events.Event] = field(default_factory=list)
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self):
        if not self.id:
            object.__setattr__(self, "id", str(uuid.uuid4()))

    def __hash__(self):
        return hash(self.id)

    def append_event(self, event: events.Event):
        self._events.append(event)

    def pop_events(self) -> List[events.Event]:
        events = self._events
        self._events = []
        return events

    def add_variation(self, variation: Variation):
        self.variations.append(variation)

    def remove_variation(self, id: str):
        variation = self.get_variation_by_id(id)
        if variation:
            variation.is_deleted = 1
            return
        raise ValueError("Variation not found.")

    def get_active_variations(self) -> List[Variation]:
        return [v for v in self.variations if v.is_deleted == 0]

    def get_variation_by_id(self, variation_id: str) -> Optional[Variation]:
        variations = self.get_active_variations()
        for v in variations:
            if v.id == variation_id:
                return v
        return None


@dataclass
class OrderItem:
    quantity: int
    product_id: str
    variation_id: str
    order_id: str
    unit_price: float
    id: str | None = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    def __post_init__(self):
        if not self.id:
            object.__setattr__(self, "id", str(uuid.uuid4()))


@dataclass
class Order:
    consume_location: ConsumeLocation
    total_cost: float
    user_id: str
    order_items: List[OrderItem]
    status: OrderStatus = OrderStatus.WAITING
    id: str | None = None
    _events: List[events.Event] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self):
        if not self.id:
            object.__setattr__(self, "id", str(uuid.uuid4()))

    def __eq__(self, other):
        if not isinstance(other, Order):
            return False
        return other.id == self.id

    def __hash__(self):
        return hash(self.id)

    def append_event(self, event: events.Event):
        self._events.append(event)

    def pop_events(self) -> List[events.Event]:
        events = self._events
        self._events = []
        return events

    def change_status(self, status: OrderStatus, items: List[OrderItem]):
        if self.status == status:
            raise ValueError("Cannot change to the same status.")
        if status == OrderStatus.CANCELLED:
            if self.status in [
                OrderStatus.DELIVERED,
                OrderStatus.CANCELLED,
                OrderStatus.READY,
            ]:
                raise ValueError(
                    "Cannot cancel an order that is already delivered, cancelled, or ready."
                )
        elif (
            status == OrderStatus.PREPARATION
            and self.status != OrderStatus.WAITING
        ):
            raise ValueError(
                "Cannot move to preparation unless the order is in waiting status."
            )
        elif (
            status == OrderStatus.READY
            and self.status != OrderStatus.PREPARATION
        ):
            raise ValueError(
                "Cannot move to ready unless the order is in preparation status."
            )
        elif (
            status == OrderStatus.DELIVERED and self.status != OrderStatus.READY
        ):
            raise ValueError(
                "Cannot move to delivered unless the order is in ready status."
            )
        if self.status == OrderStatus.CANCELLED:
            raise ValueError(
                "Order already cancelled. Cannot change status anymore."
            )

        self.status = status
        self.append_event(
            events.OrderStatusChanged(
                order_id=self.id,
                user_id=self.user_id,
                order_items=items,
                total_cost=self.total_cost,
                consume_location=self.consume_location,
                status=status,
                updated_at=datetime.utcnow(),
            )
        )
