from sqlalchemy.orm import Session
from sqlalchemy.engine.reflection import Inspector

from nissaba.db.schema import Base


def test_schema_creation(
    postgres_session: Session, postgres_inspector: Inspector
) -> None:
    """Test the database can be created and deleted from our schema definition

    The `postgres_session` fixture does all this for us. Just verify it's the
    of the right type and that all the tables are empty.
    """
    assert isinstance(postgres_session, Session)

    # Check the tables are empty
    for table_name in postgres_inspector.get_table_names():
        table = Base.metadata.tables[table_name]
        assert len(postgres_session.query(table).all()) == 0
