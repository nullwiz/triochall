import abc
from api.domain import models
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, contains_eager
from dataclasses import asdict
from sqlalchemy.ext.asyncio import AsyncSession
from api.domain.events import Event, OrderCreated
from typing import Set, Optional, List


class AbstractUserRepository(abc.ABC):
    def __init__(self):
        self.seen: Set[models.User] = set()
        self._events: Set[Event] = set()

    async def add(self, user: models.User):
        await self._add(user)
        self.seen.add(user)

    async def get(self, id: str) -> Optional[models.User]:
        user = await self._get(id)
        if user:
            self.seen.add(user)
        return user

    async def delete(self, user: models.User):
        await self._delete(user)
        self.seen.remove(user)

    async def update(self, user: models.User):
        await self._update(user)

    @abc.abstractmethod
    async def _add(self, user: models.User):
        raise NotImplementedError

    @abc.abstractmethod
    async def _get(self, id: str) -> Optional[models.User]:
        raise NotImplementedError

    @abc.abstractmethod
    async def _delete(self, user: models.User):
        raise NotImplementedError

    @abc.abstractmethod
    async def _update(self, user: models.User):
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_email(self, email: str) -> Optional[models.User]:
        raise NotImplementedError


class AbstractProductRepository(abc.ABC):
    def __init__(self):
        self.seen: Set[models.Product] = set()
        self._events: Set[Event] = set()

    async def add(self, product: models.Product):
        await self._add(product)
        self.seen.add(product)

    async def get(self, id: str) -> Optional[models.Product]:
        product = await self._get(id)
        if product:
            self.seen.add(product)
        return product

    async def delete(self, product: models.Product):
        await self._delete(product)
        self.seen.remove(product)

    async def update(self, product: models.Product):
        await self._update(product)

    async def get_all(
        self, page=1, page_size=10, filters=None
    ) -> Optional[List[models.Product]]:
        products = await self._get_all(page, page_size, filters)
        if products:
            return products
        return []

    @abc.abstractmethod
    async def _add(self, product: models.Product):
        raise NotImplementedError

    @abc.abstractmethod
    async def _update(self, product: models.Product):
        raise NotImplementedError

    @abc.abstractmethod
    async def _get(self, id: str) -> Optional[models.Product]:
        raise NotImplementedError

    @abc.abstractmethod
    async def _delete(self, product: models.Product):
        raise NotImplementedError

    @abc.abstractmethod
    async def _get_all(
        self, page: int, page_size=10, filters=None
    ) -> Optional[List[models.Product]]:
        raise NotImplementedError


class AbstractVariationRepository(abc.ABC):
    def __init__(self):
        self.seen: Set[models.Variation] = set()

    async def add(self, variation: models.Variation):
        await self._add(variation)
        self.seen.add(variation)

    async def get(self, id: str) -> Optional[models.Variation]:
        variation = await self._get(id)
        if variation:
            self.seen.add(variation)
        return variation

    async def update(self, variation: models.Variation):
        await self._update(variation)

    async def delete(self, variation: models.Variation):
        await self._delete(variation)
        self.seen.remove(variation)

    @abc.abstractmethod
    async def _add(self, variation: models.Variation):
        raise NotImplementedError

    @abc.abstractmethod
    async def _get(self, id: str) -> Optional[models.Variation]:
        raise NotImplementedError

    @abc.abstractmethod
    async def _delete(self, variation: models.Variation):
        raise NotImplementedError

    @abc.abstractmethod
    async def _update(self, variation: models.Variation):
        raise NotImplementedError


class AbstractOrderRepository(abc.ABC):
    def __init__(self):
        self.seen: Set[models.Order] = set()
        self._events: Set[Event] = set()

    async def add(self, order: models.Order):
        await self._add(order)
        # Notify users of their order being created, pop non relevant info
        order_event = asdict(order)
        order_event.pop("_events")
        order_event.pop("is_deleted")
        order.append_event(OrderCreated(**order_event))
        self.seen.add(order)

    async def get(self, id: str) -> Optional[models.Order]:
        order = await self._get(id)
        if order:
            self.seen.add(order)
        return order

    async def get_all(
        self, page=1, page_size=10, filters=None
    ) -> Optional[List[models.Order]]:
        orders = await self._get_all(page, page_size, filters)
        if orders:
            for order in orders:
                self.seen.add(order)
            return orders
        return []

    async def update(self, order: models.Order):
        await self._update(order)

    async def delete(self, order: models.Order):
        await self._delete(order)
        self.seen.remove(order)

    @abc.abstractmethod
    async def _add(self, order: models.Order):
        raise NotImplementedError

    @abc.abstractmethod
    async def _get(self, id: str) -> Optional[models.Order]:
        raise NotImplementedError

    @abc.abstractmethod
    async def _get_all(
        self, page: int, page_size=10, filters=None
    ) -> Optional[List[models.Product]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def _delete(self, order: models.Order):
        raise NotImplementedError

    @abc.abstractmethod
    async def _update(self, order: models.Order):
        raise NotImplementedError


class AbstractOrderItemRepository(abc.ABC):
    def __init__(self):
        self.seen: Set[models.OrderItem] = set()

    async def add(self, order_item: models.OrderItem):
        await self._add(order_item)
        self.seen.add(order_item)

    async def get(self, id: str) -> Optional[models.OrderItem]:
        order_item = await self._get(id)
        if order_item:
            self.seen.add(order_item)
        return order_item

    async def update(self, order_item: models.OrderItem):
        await self._update(order_item)

    async def delete(self, order_item: models.OrderItem):
        await self._delete(order_item)
        self.seen.remove(order_item)

    @abc.abstractmethod
    async def _add(self, order_item: models.OrderItem):
        raise NotImplementedError

    @abc.abstractmethod
    async def _get(self, id: str) -> Optional[models.OrderItem]:
        raise NotImplementedError

    @abc.abstractmethod
    async def _update(self, order_item: models.OrderItem):
        raise NotImplementedError

    @abc.abstractmethod
    async def _delete(self, order_item: models.OrderItem):
        raise NotImplementedError


class SqlAlchemyUserRepository(AbstractUserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        super().__init__()

    async def _add(self, user):
        self.session.add(user)

    async def _get(self, id):
        result = await self.session.execute(
            select(models.User).filter_by(id=id)
        )
        return result.scalars().first()

    async def get_by_email(self, email):
        result = await self.session.execute(
            select(models.User).filter_by(email=email)
        )
        return result.scalars().first()

    async def _delete(self, user):
        await self.session.delete(user)

    async def _update(self, user):
        await self.session.merge(user)


class SqlAlchemyProductRepository(AbstractProductRepository):
    def __init__(self, session):
        self.session = session
        super().__init__()

    async def _add(self, product):
        self.session.add(product)

    async def _get(self, id):
        query = (
            select(models.Product)
            .filter(models.Product.id == id, models.Product.is_deleted == 0)
            .options(joinedload(models.Product.variations))
        )
        result = await self.session.execute(query)
        product = result.scalars().first()

        if product is not None:
            return product

    async def _delete(self, product):
        product.is_deleted = 1
        await self.session.merge(product)

    async def _get_all(self, page, page_size=10, filters=None):
        query = (
            select(models.Product)
            .outerjoin(models.Variation, models.Product.variations)
            .options(contains_eager(models.Product.variations))
            .order_by(models.Product.id)
            .filter(
                models.Product.is_deleted == 0, models.Variation.is_deleted == 0
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        if filters:
            for key, value in filters.items():
                query = query.filter(getattr(models.Product, key) == value)

        result = await self.session.execute(query)
        return result.scalars().unique().all()

    async def _update(self, product):
        await self.session.merge(product)


class SqlAlchemyVariationRepository(AbstractVariationRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        super().__init__()

    async def _add(self, variation):
        self.session.add(variation)

    async def _get(self, id):
        result = await self.session.execute(
            select(models.Variation).filter_by(id=id, is_deleted=0)
        )
        return result.scalars().first()

    async def _get_all(self, page, page_size=10):
        stmt = (
            select(models.Variation)
            .order_by(models.Variation.id)
            .filter_by(is_deleted=0)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def _delete(self, variation):
        variation.is_deleted = 1
        await self.session.merge(variation)

    async def _update(self, variation):
        await self.session.merge(variation)


class SqlAlchemyOrderRepository(AbstractOrderRepository):
    def __init__(self, session):
        self.session = session
        super().__init__()

    async def _add(self, order):
        self.session.add(order)

    async def _get(self, id):
        result = await self.session.execute(
            select(models.Order)
            .filter_by(id=id)
            .options(joinedload(models.Order.order_items))
        )

        return result.scalars().first()

    async def _get_all(self, page, page_size=10, filters=None):
        query = (
            select(models.Order)
            .options(joinedload(models.Order.order_items))
            .order_by(models.Order.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        if filters:
            for key, value in filters.items():
                if value:
                    query = query.filter(getattr(models.Order, key) == value)

        result = await self.session.execute(query)
        return result.scalars().unique().all()

    async def _delete(self, order):
        order.is_deleted = 1
        await self.session.merge(order)

    async def _update(self, order):
        await self.session.merge(order)


class SqlAlchemyOrderItemRepository(AbstractOrderItemRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        super().__init__()

    async def _add(self, order_item):
        self.session.add(order_item)

    async def _get(self, id):
        result = await self.session.execute(
            select(models.OrderItem).filter_by(id=id)
        )
        return result.scalars().first()

    async def _get_all(self, page, page_size=10):
        stmt = (
            select(models.OrderItem)
            .order_by(models.OrderItem.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def _delete(self, order_item):
        await self.session.delete(order_item)

    async def _update(self, order_item):
        await self.session.merge(order_item)
