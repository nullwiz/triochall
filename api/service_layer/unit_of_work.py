import abc
import api.config as config
import logging
import asyncio
from api.adapters import repository
from sqlalchemy.exc import DatabaseError
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import text

logger = logging.getLogger(__name__)


class AbstractUnitOfWork(abc.ABC):
    users: repository.AbstractUserRepository
    products: repository.AbstractProductRepository
    variations: repository.AbstractVariationRepository
    orders: repository.AbstractOrderRepository
    order_items: repository.AbstractOrderItemRepository

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type is not None:
            await self._rollback()

    async def commit(self):
        await self._commit()

    def collect_new_events(self):
        repos = [self.users, self.orders, self.products]
        for repo in repos:
            for obj in repo.seen:
                while obj._events:
                    yield obj._events.pop(0)

    @abc.abstractmethod
    async def health_check(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def _commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def _rollback(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def __repr__(self):
        raise NotImplementedError


def create_engine():
    return create_async_engine(
        config.get_postgres_uri(),
        future=True,
        echo=True,
    )


DEFAULT_SESSION_FACTORY = async_sessionmaker(
    create_engine(),
    expire_on_commit=False,
    class_=AsyncSession,
    future=True,
)


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory=DEFAULT_SESSION_FACTORY):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session: AsyncSession = self.session_factory()
        self.users = repository.SqlAlchemyUserRepository(self.session)
        self.products = repository.SqlAlchemyProductRepository(self.session)
        self.variations = repository.SqlAlchemyVariationRepository(
            self.session)
        self.orders = repository.SqlAlchemyOrderRepository(self.session)
        self.order_items = repository.SqlAlchemyOrderItemRepository(
            self.session
        )
        return self

    async def health_check(self):
        try:
            stmt = text("SELECT 1")
            await asyncio.wait_for(self.session.execute(stmt), timeout=5)
        except asyncio.TimeoutError as e:
            logger.exception("Health check timed out: %s", e)
            raise
        except Exception as e:
            logger.exception("Health check failed: %s", e)
            raise e

    async def __aexit__(self, exc_type, exc, _):
        if (
            exc_type is not None
        ):  # An exception occurred, log it and raise as IntegrityError
            await self._rollback()
            logger.exception("Exception occurred: %s", exc)
            if isinstance(exc, DatabaseError):
                raise HTTPException(
                    status_code=400,
                    detail="Database error: {}".format(exc.orig),
                )

        await self.session.close()

    async def _commit(self):
        self.collect_new_events()
        await self.session.commit()

    async def _rollback(self):
        await self.session.rollback()

    async def __repr__(self):
        return f"<SqlAlchemyUnitOfWork(session={self.session})>"
