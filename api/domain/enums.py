from enum import Enum


class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    MANAGER = "MANAGER"


class OrderStatus(str, Enum):
    WAITING = "Waiting"
    PREPARATION = "Preparation"
    READY = "Ready"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"


class ConsumeLocation(str, Enum):
    IN_HOUSE = "In-House"
    TAKE_AWAY = "Take Away"
