"""
Test fixtures for the Stelloid Command Center API tests.

Creates an in-memory SQLite database with seeded test data
and provides a TestClient that uses this isolated database.
"""

import random
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Channel, DailyChannelMetric, DailyBrandMetric


# In-memory SQLite for test isolation
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    """Dependency override that uses the test database."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create tables and seed test data once for the entire test session."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    db = TestSessionLocal()

    rng = random.Random(42)

    # Create channels
    channels_data = [
        {"name": "Shopify", "business_scope": "DTC"},
        {"name": "Amazon US", "business_scope": "Marketplace"},
        {"name": "Walmart Marketplace", "business_scope": "Marketplace"},
    ]

    channel_objects = {}
    for ch_data in channels_data:
        channel = Channel(name=ch_data["name"], business_scope=ch_data["business_scope"])
        db.add(channel)
        db.flush()
        channel_objects[ch_data["name"]] = channel

    # Seed 10 days of data
    start = date(2026, 9, 20)
    baselines = {
        "Shopify": {"gmv": 7200, "net_revenue": 6500, "contribution": 2200, "returns_refunds": 320, "net_orders": 140},
        "Amazon US": {"gmv": 5000, "net_revenue": 4600, "contribution": 1450, "returns_refunds": 250, "net_orders": 100},
        "Walmart Marketplace": {"gmv": 2700, "net_revenue": 2400, "contribution": 830, "returns_refunds": 120, "net_orders": 47},
    }

    for day_offset in range(10):
        current_date = start + timedelta(days=day_offset)
        brand_gmv = brand_nr = brand_contrib = brand_rr = 0.0
        brand_orders = 0

        for ch_name, bl in baselines.items():
            gmv = round(bl["gmv"] * (1 + rng.uniform(-0.2, 0.2)), 2)
            nr = round(bl["net_revenue"] * (1 + rng.uniform(-0.2, 0.2)), 2)
            contrib = round(bl["contribution"] * (1 + rng.uniform(-0.2, 0.2)), 2)
            rr = round(bl["returns_refunds"] * (1 + rng.uniform(-0.2, 0.2)), 2)
            orders = max(1, int(bl["net_orders"] * (1 + rng.uniform(-0.2, 0.2))))

            db.add(DailyChannelMetric(
                date=current_date,
                channel_id=channel_objects[ch_name].id,
                gmv=gmv, net_revenue=nr, contribution=contrib,
                returns_refunds=rr, net_orders=orders,
            ))

            brand_gmv += gmv
            brand_nr += nr
            brand_contrib += contrib
            brand_rr += rr
            brand_orders += orders

        db.add(DailyBrandMetric(
            date=current_date,
            gmv=round(brand_gmv, 2), net_revenue=round(brand_nr, 2),
            contribution=round(brand_contrib, 2), returns_refunds=round(brand_rr, 2),
            net_orders=brand_orders,
        ))

    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def client():
    """Provides a FastAPI TestClient."""
    return TestClient(app)
