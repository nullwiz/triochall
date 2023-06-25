from sqlalchemy import (
    Table,
    Column,
    Integer,
    String,
    DateTime,
    Float,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy import event
from sqlalchemy.orm import registry
from sqlalchemy import text
import uuid
from api.domain import models
from api.domain.enums import UserRole, OrderStatus, ConsumeLocation
import logging

logger = logging.getLogger(__name__)
mapper_registry = registry()

metadata = mapper_registry.metadata


user = Table(
    "users",
    metadata,
    Column(
        "id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    ),
    Column("email", String(120), unique=True, nullable=False),
    Column("password", String(255), nullable=False),
    Column("role", Enum(UserRole), default=UserRole.CUSTOMER),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)

# product
product = Table(
    "products",
    metadata,
    Column(
        "id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    ),
    Column("name", String(50), unique=True, nullable=False),
    Column("description", String(255), nullable=False),
    Column("price", Float(), nullable=False),
    Column("is_deleted", Integer(), nullable=False, default=0),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)

# variation
variation = Table(
    "variations",
    metadata,
    Column(
        "id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    ),
    Column("name", String(50), unique=False, nullable=False),
    Column("price", Float(), nullable=False),
    Column("is_deleted", Integer(), nullable=False, default=0),
    Column("product_id", String(36), ForeignKey("products.id")),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)

# order
order = Table(
    "orders",
    metadata,
    Column(
        "id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    ),
    Column("status", Enum(OrderStatus), default=OrderStatus.WAITING),
    Column(
        "consume_location",
        Enum(ConsumeLocation),
        default=ConsumeLocation.IN_HOUSE,
    ),
    Column("total_cost", Float(), nullable=False),
    Column("user_id", String(36), ForeignKey("users.id")),
    Column("is_deleted", Integer(), nullable=False, default=0),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)

# order item
order_item = Table(
    "order_items",
    metadata,
    Column(
        "id", String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    ),
    Column("quantity", Integer, nullable=False),
    Column("unit_price", Float(), nullable=False),
    Column("product_id", String(36), ForeignKey("products.id")),
    Column("variation_id", String(36), ForeignKey("variations.id")),
    Column("order_id", String(36), ForeignKey("orders.id")),
    Column("created_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", DateTime, server_default=text("CURRENT_TIMESTAMP")),
)


def start_mappers():
    logger.info("Starting mappers")
    mapper_registry.map_imperatively(
        models.User,
        user,
        properties={
            "orders": relationship(
                models.Order, backref="user", cascade="all, delete-orphan"
            )
        },
    )
    mapper_registry.map_imperatively(
        models.Product,
        product,
        properties={
            "variations": relationship(
                models.Variation,
                backref="product",
                cascade="all, delete-orphan",
            )
        },
    )
    mapper_registry.map_imperatively(models.Variation, variation)
    mapper_registry.map_imperatively(
        models.Order,
        order,
        properties={
            "order_items": relationship(
                models.OrderItem, backref="order", cascade="all, delete-orphan"
            )
        },
    )
    mapper_registry.map_imperatively(models.OrderItem, order_item)
    logger.info("Mappers started")


def create_tables(engine):
    logger.info("Creating tables")
    metadata.create_all(engine)
    logger.info("Tables created")


def drop_tables(engine):
    logger.info("Dropping tables")
    metadata.drop_all(engine)
    logger.info("Tables dropped")


def has_started_mappers():
    return len(mapper_registry.mappers) > 0


def clear_mappers():
    mapper_registry.dispose()


# Orm events, not persisted in the database


@event.listens_for(models.User, "load")
def receive_user_load(target, _):
    target._events = []


@event.listens_for(models.Product, "load")
def receive_product_load(target, _):
    target._events = []


@event.listens_for(models.Order, "load")
def receive_order_load(target, _):
    target._events = []
