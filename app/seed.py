"""
Deterministic mock data seeder for the Stelloid Command Center.

Run with:
    python -m app.seed

Uses a fixed random seed (42) so the database can be rebuilt
with identical data every time.
"""

import random
from datetime import date, timedelta

from app.database import engine, SessionLocal, Base
from app.models import Channel, DailyChannelMetric, DailyBrandMetric


# Fixed seed for reproducibility
RANDOM_SEED = 42

# Date range: 30 days from Sep 5 to Oct 4, 2026
START_DATE = date(2026, 9, 5)
END_DATE = date(2026, 10, 4)

# Channel definitions
CHANNELS = [
    {"name": "Shopify", "business_scope": "DTC"},
    {"name": "Amazon US", "business_scope": "Marketplace"},
    {"name": "Walmart Marketplace", "business_scope": "Marketplace"},
]

# Baseline daily metrics per channel (will be varied with random noise)
# These are tuned so the 30-day totals roughly match the dashboard screenshot:
#   GMV ~$446,792 | Net Revenue ~$404,360 | Contribution ~$134,289
#   Returns/Refunds ~$20,695 | Net Orders ~8,604 | AOV ~$47.00
CHANNEL_BASELINES = {
    "Shopify": {
        "gmv": 7200,
        "net_revenue": 6500,
        "contribution": 2200,
        "returns_refunds": 320,
        "net_orders": 140,
    },
    "Amazon US": {
        "gmv": 5000,
        "net_revenue": 4600,
        "contribution": 1450,
        "returns_refunds": 250,
        "net_orders": 100,
    },
    "Walmart Marketplace": {
        "gmv": 2700,
        "net_revenue": 2400,
        "contribution": 830,
        "returns_refunds": 120,
        "net_orders": 47,
    },
}


def _vary(base: float, rng: random.Random, pct: float = 0.20) -> float:
    """Apply random variation of ±pct to a base value."""
    factor = 1.0 + rng.uniform(-pct, pct)
    return round(base * factor, 2)


def seed_database():
    """Drop all tables, recreate them, and insert deterministic mock data."""
    rng = random.Random(RANDOM_SEED)

    # Recreate all tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # --- Insert channels ---
        channel_objects = {}
        for ch_data in CHANNELS:
            channel = Channel(name=ch_data["name"], business_scope=ch_data["business_scope"])
            db.add(channel)
            db.flush()  # populate channel.id
            channel_objects[ch_data["name"]] = channel

        # --- Generate daily metrics ---
        num_days = (END_DATE - START_DATE).days + 1

        for day_offset in range(num_days):
            current_date = START_DATE + timedelta(days=day_offset)

            # Track brand totals for this day
            brand_gmv = 0.0
            brand_net_revenue = 0.0
            brand_contribution = 0.0
            brand_returns_refunds = 0.0
            brand_net_orders = 0

            for ch_name, baseline in CHANNEL_BASELINES.items():
                channel = channel_objects[ch_name]

                gmv = _vary(baseline["gmv"], rng)
                net_revenue = _vary(baseline["net_revenue"], rng)
                contribution = _vary(baseline["contribution"], rng)
                returns_refunds = _vary(baseline["returns_refunds"], rng)
                net_orders = max(1, int(_vary(baseline["net_orders"], rng)))

                metric = DailyChannelMetric(
                    date=current_date,
                    channel_id=channel.id,
                    gmv=gmv,
                    net_revenue=net_revenue,
                    contribution=contribution,
                    returns_refunds=returns_refunds,
                    net_orders=net_orders,
                )
                db.add(metric)

                brand_gmv += gmv
                brand_net_revenue += net_revenue
                brand_contribution += contribution
                brand_returns_refunds += returns_refunds
                brand_net_orders += net_orders

            # Insert aggregated brand-level metrics for this day
            brand_metric = DailyBrandMetric(
                date=current_date,
                gmv=round(brand_gmv, 2),
                net_revenue=round(brand_net_revenue, 2),
                contribution=round(brand_contribution, 2),
                returns_refunds=round(brand_returns_refunds, 2),
                net_orders=brand_net_orders,
            )
            db.add(brand_metric)

        db.commit()
        print("[OK] Database seeded successfully!")
        print(f"   Channels: {len(CHANNELS)}")
        print(f"   Date range: {START_DATE} to {END_DATE} ({num_days} days)")
        print(f"   Daily channel metrics: {num_days * len(CHANNELS)} rows")
        print(f"   Daily brand metrics: {num_days} rows")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
