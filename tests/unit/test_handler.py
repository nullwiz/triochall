from unittest import mock
from api.domain import commands
from api.adapters.notifications import AbstractNotifications
from api.bootstrap import bootstrap
from api.utils.exceptions import Unauthorized, ProductNotFound
from api.domain.enums import ConsumeLocation, OrderStatus
from api.service_layer import unit_of_work
from api.adapters import repository
from api.domain.models import Order, OrderItem, Product, Variation, User
from api.domain.enums import UserRole
from api.utils.hashoor import hash_password
import pytest
import uuid


def order_item_data(id):
    return {
        "product_id": str(uuid.uuid4()),
        "variation_id": str(uuid.uuid4()),
        "quantity": 2,
        "order_id": id,
        "unit_price": 0.0,
    }


def order_data():
    id = str(uuid.uuid4())

    return {
        "consume_location": ConsumeLocation.IN_HOUSE,
        "order_items": [OrderItem(**order_item_data(id))],
        "total_cost": 0.0,
        "user_id": str(uuid.uuid4()),
        "status": OrderStatus.WAITING,
        "id": id,
        "created_at": "2021-08-01T00:00:00",
        "updated_at": "2021-08-01T00:00:00",
    }


class FakeOrderRepository(repository.AbstractOrderRepository):
    def __init__(self, orders):
        super().__init__()
        self.orders = orders

    async def _add(self, order):
        self.orders.append(order)

    async def _get(self, id):
        for order in self.orders:
            if order.id == id:
                return order
        return None

    async def _get_all(self):
        return self.orders

    async def _delete(self, id):
        for order in self.orders:
            if order.id == id:
                self.orders.remove(order)
                return True
        return False

    async def _update(self, order):
        for i, o in enumerate(self.orders):
            if o.id == order.id:
                self.orders[i] = order
                return True
        return False


class FakeProductRepository(repository.AbstractProductRepository):
    def __init__(self, products):
        super().__init__()
        self.products = products

    async def _add(self, product):
        self.products.append(product)

    async def _get(self, id):
        for product in self.products:
            if product.id == id:
                return product
        return None

    async def _get_all(self):
        return self.products

    async def _delete(self, id):
        for product in self.products:
            if product.id == id:
                self.products.remove(product)
                return True
        return False

    async def _update(self, product):
        for i, p in enumerate(self.products):
            if p.id == product.id:
                self.products[i] = product
                return True
        return False


class FakeVariationRepository(repository.AbstractVariationRepository):
    def __init__(self, variations):
        super().__init__()
        self.variations = variations

    async def _add(self, variation):
        self.variations.append(variation)

    async def _get(self, id):
        for variation in self.variations:
            if variation.id == id:
                return variation
        return None

    async def _get_all(self):
        return self.variations

    async def _delete(self, id):
        for variation in self.variations:
            if variation.id == id:
                self.variations.remove(variation)
                return True
        return False

    async def _update(self, variation):
        for i, v in enumerate(self.variations):
            if v.id == variation.id:
                self.variations[i] = variation
                return True
        return False


class FakeUsersRepository(repository.AbstractUserRepository):
    def __init__(self, users):
        super().__init__()
        self.users = users

    async def _add(self, user):
        self.users.append(user)

    async def _get(self, id):
        for user in self.users:
            if user["id"] == id:
                return user
        return None

    async def _get_all(self):
        return self.users

    async def get_by_email(self, email):
        for user in self.users:
            if user["email"] == email:
                return user
        return None

    async def _delete(self, id):
        for user in self.users:
            if user["id"] == id:
                self.users.remove(user)
                return True
        return False

    async def _commit(self):
        pass

    async def _rollback(self):
        pass

    async def _update(self, user):
        for i, u in enumerate(self.users):
            if u["id"] == user["id"]:
                self.users[i] = user
                return True
        return False


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.orders = FakeOrderRepository([])
        self.products = FakeProductRepository([])
        self.variations = FakeVariationRepository([])
        self.users = FakeUsersRepository([])
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def __repr__(self):
        return "<FakeUnitOfWork>"

    async def _commit(self):
        self.committed = True

    async def _rollback(self):
        pass

    async def health_check(self):
        pass


class FakeNotifications(AbstractNotifications):
    def __init__(self):
        self.sent = []

    def send(self, destination, message):
        self.sent[destination].append(message)


def bootstrap_test_app():
    return bootstrap(
        start_orm=False,
        uow=FakeUnitOfWork(),
        notifications=mock.MagicMock(),
        publish=lambda *args: None,
    )


class TestOrders:
    @pytest.mark.asyncio
    async def test_create_order_handler(self):
        bus = bootstrap_test_app()
        # Add variations
        # Add product and variations
        user_id = str(uuid.uuid4())
        product_id = str(uuid.uuid4())
        variation_id = str(uuid.uuid4())
        bus.uow.users.users.append(
            User(
                id=user_id,
                email="createorder@example.com",
                password=hash_password("test"),
                role=UserRole.CUSTOMER.value,
            ))
        bus.uow.products.products.append(
            Product(
                id=product_id,
                description="Test Product",
                name="Test Product",
                price=10.0,
                variations=[]
            )
        )
        bus.uow.variations.variations.append(
            Variation(
                id=variation_id,
                name="Test Variation",
                price=10.0,
                product_id=product_id,
            ))

        order_items = [
            {
                "product_id": product_id,
                "variation_id": variation_id,
                "quantity": 2,
            },
        ]
        cmd = commands.CreateOrder(
            consume_location="HOME_DELIVERY",
            user_id=str(uuid.uuid4()),
            order_items=order_items,
        )
        result = await bus.handle(cmd)

        assert isinstance(result, Order)

    @pytest.mark.asyncio
    async def test_create_order_handler_with_invalid_product_id(
        self
    ):
        bus = bootstrap_test_app()

        order_items = [
            {
                "product_id": str(uuid.uuid4()),
                "variation_id": str(uuid.uuid4()),
                "quantity": 2,
            }
        ]

        cmd = commands.CreateOrder(
            consume_location=ConsumeLocation.IN_HOUSE,
            user_id=str(uuid.uuid4()),
            order_items=order_items,
        )

        with pytest.raises(ProductNotFound):
            await bus.handle(cmd)

    @pytest.mark.asyncio
    async def test_create_order_handler_with_invalid_variation_id(self
                                                                  ):
        bus = bootstrap_test_app()
        order_items = [
            {
                "product_id": str(uuid.uuid4()),
                "variation_id": str(uuid.uuid4()),
                "quantity": 2,
            }
        ]

        cmd = commands.CreateOrder(
            consume_location=ConsumeLocation.IN_HOUSE,
            user_id=str(uuid.uuid4()),
            order_items=order_items,
        )

        with pytest.raises(Exception):
            await bus.handle(cmd)

    @pytest.mark.asyncio
    async def test_update_order_handler_order_not_found(self):
        bus = bootstrap_test_app()

        cmd = commands.UpdateOrderStatus(
            id=str(uuid.uuid4()), status=OrderStatus.DELIVERED.value
        )

        with pytest.raises(Exception):
            await bus.handle(cmd)

    @pytest.mark.asyncio
    async def test_mark_order_as_cancelled_handler(self):
        bus = bootstrap_test_app()
        product_id = str(uuid.uuid4())
        variation_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        bus.uow.products.products.append(
            Product(
                id=product_id,
                description="Test Product",
                name="Test Product",
                price=10.0,
                variations=[
                ]
            )
        )
        bus.uow.variations.variations.append(
            Variation(
                id=variation_id,
                name="Test Variation",
                price=10.0,
                product_id=product_id,
            ))

        order_items = [
            {
                "product_id": product_id,
                "variation_id": variation_id,
                "quantity": 2,
            },
        ]
        cmd = commands.CreateOrder(
            consume_location=ConsumeLocation.IN_HOUSE,
            user_id=user_id,
            order_items=order_items,
        )
        result = await bus.handle(cmd)

        assert isinstance(result, Order)

        cmd = commands.CancelOrder(
            order_id=result.id, user_id=user_id)

        result = await bus.handle(cmd)
        assert result[0] is True
        assert result[1] == "Order cancelled successfully"

    @pytest.mark.asyncio
    async def test_user_can_only_cancel_their_order(self):
        bus = bootstrap_test_app()
        product_id = str(uuid.uuid4())
        variation_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        bus.uow.products.products.append(
            Product(
                id=product_id,
                description="Test Product",
                name="Test Product",
                price=10.0,
                variations=[]
            )
        )
        bus.uow.variations.variations.append(
            Variation(
                id=variation_id,
                name="Test Variation",
                price=10.0,
                product_id=product_id,
            ))

        order_items = [
            {
                "product_id": product_id,
                "variation_id": variation_id,
                "quantity": 2,
            },
        ]
        cmd = commands.CreateOrder(
            consume_location="HOME_DELIVERY",
            user_id=user_id,
            order_items=order_items,
        )
        result = await bus.handle(cmd)

        assert isinstance(result, Order)

        cmd = commands.CancelOrder(
            order_id=result.id, user_id=str(uuid.uuid4()))

        with pytest.raises(Unauthorized):
            result = await bus.handle(cmd)


@pytest.mark.asyncio
async def test_delete_product_handler():
    bus = bootstrap_test_app()
    product_id = str(uuid.uuid4())
    bus.uow.products.products.append(
        Product(
            id=product_id,
            description="Test Product",
            name="Test Product",
            price=10.0,
            variations=[]
        )
    )

    cmd = commands.DeleteProduct(id=product_id)
    result = await bus.handle(cmd)
    # I return the product that was deleted if successful
    assert isinstance(result, Product)


@pytest.mark.asyncio
async def test_delete_non_existent_product_handler():
    bus = bootstrap_test_app()

    cmd = commands.DeleteProduct(id=str(
        uuid.uuid4()))

    with pytest.raises(ProductNotFound):
        await bus.handle(cmd)


@pytest.mark.asyncio
async def test_update_product_handler():
    bus = bootstrap_test_app()

    # Add a product
    product_id = str(uuid.uuid4())
    bus.uow.products.products.append(
        Product(
            id=product_id,
            description="Test Product",
            name="Test Product",
            price=10.0,
            variations=[]
        )
    )

    cmd = commands.UpdateProduct(
        id=product_id,
        description="Updated Product",
        name="Updated Product",
        price=20.0
    )

    result = await bus.handle(cmd)

    assert result.description == "Updated Product"


@pytest.mark.asyncio
async def test_update_non_existent_product_handler():
    bus = bootstrap_test_app()

    cmd = commands.UpdateProduct(
        id=str(uuid.uuid4()),
        description="Updated Product",
        name="Updated Product",
        price=20.0
    )

    with pytest.raises(ProductNotFound):
        await bus.handle(cmd)
