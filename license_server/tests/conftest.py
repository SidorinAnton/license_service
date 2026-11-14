import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.core.database import Base, get_db
from src.main import app

pytest_plugins = [
    "tests.license.fixtures",
]


def create_test_db_url():
    curr_url = make_url(str(settings.DATABASE_URL))
    test_db = "test_" + curr_url.database

    if not re.fullmatch(r"[a-z_]+", test_db):
        # По идее это не может вызвать инъекцию
        raise ValueError("Test database name is unsafe")

    return curr_url.set(database=test_db)


def pytest_report_header():
    return [
        f"test_db_url: {create_test_db_url().render_as_string(hide_password=True)}",
    ]


@pytest.fixture(scope="session")
def setup_database():
    test_url = create_test_db_url()
    admin_url = test_url.set(database="postgres")

    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": test_url.database}
        ).scalar()
        if not exists:
            conn.execute(text(f"CREATE DATABASE {test_url.database}"))

    engine = create_engine(test_url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()

    with admin_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {test_url.database}"))


@pytest.fixture
def db_session(setup_database):
    connection = setup_database.connect()
    transaction = connection.begin()
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=setup_database)
    session = testing_session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
