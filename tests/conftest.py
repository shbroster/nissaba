from typing import Any

import psycopg2
import pytest
from pytest_docker.plugin import Services
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine.reflection import Inspector


import nissaba.db.schema as sch

TEST_DATABASE = "test_database"
TEST_DB_USER = "test_user"
TEST_DB_PWD = "test_password"


def is_postgress_running(**kwargs: Any) -> bool:
    """Method for checking the connection to a postgres server"""
    try:
        psycopg2.connect(**kwargs)
    except psycopg2.OperationalError:
        return False
    else:
        return True


@pytest.fixture(scope="session")
def postgres_engine(docker_ip: str, docker_services: Services) -> Engine:
    """Create a container running postgres and wait for it to start."""

    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for("database", 5432)
    docker_services.wait_until_responsive(
        timeout=30.0,
        pause=0.1,
        check=lambda: is_postgress_running(
            host=docker_ip,
            database=TEST_DATABASE,
            user=TEST_DB_USER,
            password=TEST_DB_PWD,
            port=port,
        ),
    )
    return create_engine(
        f"postgresql://{TEST_DB_USER}:{TEST_DB_PWD}@{docker_ip}:{port}/{TEST_DATABASE}"
    )


@pytest.fixture(scope="function")
def postgres_session(postgres_engine: Engine) -> Session:
    """Create a version of the nissaba database and return an interface to it"""
    sch.Base.metadata.create_all(postgres_engine)
    session = sessionmaker(postgres_engine)()
    yield session
    session.close()
    sch.Base.metadata.drop_all(bind=postgres_engine)


@pytest.fixture(scope="function")
def postgres_inspector(postgres_engine: Engine) -> Inspector:
    """Create a version of the nissaba database and return an interface to it"""
    return inspect(postgres_engine)
