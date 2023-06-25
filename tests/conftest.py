import pytest
import pytest_asyncio
import asyncio
import async_timeout
from api.adapters.orm import (
    metadata,
)
from api.db.manage_postgres_tables import create_initial_data_async
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from api.adapters.orm import start_mappers, clear_mappers
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker
from api.config import get_postgres_uri
import json


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_state_dict_sqlite():
    file = open("tests/e2e/db_dict.json", "r")
    return json.load(file)


@pytest_asyncio.fixture
async def db_state_dict_postgres():
    file = open("tests/e2e/db_dict.json", "r")
    return json.load(file)


def dictionary_representation(row):
    return dict(row.items())


@pytest_asyncio.fixture
async def in_memory_sqlite_db():
    return create_async_engine("sqlite+aiosqlite:///:memory:")


@pytest_asyncio.fixture
async def create_db(in_memory_sqlite_db):
    # Start mappers
    clear_mappers()
    start_mappers()
    async with in_memory_sqlite_db.begin() as conn:
        await conn.run_sync(metadata.create_all)
        await create_initial_data_async(conn)
    yield conn
    async with in_memory_sqlite_db.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        clear_mappers()
    await conn.close()
    await in_memory_sqlite_db.dispose()


@pytest_asyncio.fixture
async def sqlite_session_factory(in_memory_sqlite_db, create_db):
    yield sessionmaker(
        bind=in_memory_sqlite_db, class_=AsyncSession, expire_on_commit=False
    )


@pytest_asyncio.fixture
async def session(sqlite_session_factory):
    return sqlite_session_factory()


@pytest_asyncio.fixture(scope="session")
async def postgres_async_engine():
    engine = create_async_engine(get_postgres_uri(), future=True)
    return engine


@pytest_asyncio.fixture(scope="session")
async def postgres_create(postgres_async_engine):
    # Start mappers
    await wait_for_postgres_to_come_up(postgres_async_engine)
    clear_mappers()
    start_mappers()
    async with postgres_async_engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
        await create_initial_data_async(conn)
    yield conn
    async with postgres_async_engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)
        clear_mappers()
        await conn.close()
        await postgres_async_engine.dispose()


async def wait_for_postgres_to_come_up(engine):
    async with async_timeout.timeout(10):
        return engine.connect()


@pytest_asyncio.fixture(scope="session")
async def postgres_session_factory(postgres_async_engine, postgres_create):
    yield sessionmaker(
        bind=postgres_async_engine, expire_on_commit=False, class_=AsyncSession
    )
