import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base

from dotenv import load_dotenv
load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

# TEST_DATABASE_URL = (
#     "postgresql+psycopg2://postgres:suraj123@localhost:5432/telegram_slot_test_db"
# )

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def session_factory():
    return TestingSessionLocal