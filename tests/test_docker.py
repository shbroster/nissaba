"""
Test the docker infrastructure used by the other tests.
"""
from sqlalchemy.engine import Engine, Connection


def test_postgres_engine_fixture(postgres_engine: Engine) -> None:
    """Verify the postgres_engine fixture starts postgres and returns an engine."""
    connection = postgres_engine.connect()
    assert isinstance(connection, Connection)
