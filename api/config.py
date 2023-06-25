import os
from dotenv import load_dotenv
import pathlib

# Load dotenv from base dir.
env_path = pathlib.Path("..") / ".env"
load_dotenv()


def get_postgres_uri():
    host = os.environ.get("DB_HOST", "localhost")
    port = 5432
    password = os.environ.get("DB_PASSWORD", "password")
    user = os.environ.get("DB_USER", "postgres")
    db_name = os.environ.get("DB_NAME", "triochall")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"


# For creating initial tables. not used in docker
def get_sync_postgres_uri():
    host = os.environ.get("DB_HOST", "localhost")
    port = 5432
    password = os.environ.get("DB_PASSWORD", "password")
    user = os.environ.get("DB_USER", "postgres")
    db_name = os.environ.get("DB_NAME", "triochall")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"


def get_redis_host_and_port():
    host = os.environ.get("REDIS_HOST", "127.0.0.1")
    port = os.environ.get("REDIS_PORT", 6379)
    return {"host": host, "port": port}


def get_repo_orm():
    return os.environ.get("REPO_ORM", "sqlalchemy")


def get_mailhog_host():
    return os.environ.get("MAILHOG_HOST", "localhost")
