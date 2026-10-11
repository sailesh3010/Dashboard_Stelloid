"""
SQLAlchemy ORM models for the Stelloid Command Center.

Three tables:
- channels:              Sales channel definitions (Shopify, Amazon US, etc.)
- daily_channel_metrics:  Per-channel daily performance numbers
- daily_brand_metrics:    Brand-level daily totals (aggregated across channels)
"""

from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Channel(Base):
    """Available sales channels (e.g. Shopify, Amazon US, Walmart Marketplace)."""

    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    business_scope = Column(String(50), nullable=False)  # e.g. "DTC", "Marketplace"

    # Relationship to daily metrics
    daily_metrics = relationship("DailyChannelMetric", back_populates="channel")

    def __repr__(self):
        return f"<Channel(id={self.id}, name='{self.name}', scope='{self.business_scope}')>"


class DailyChannelMetric(Base):
    """Daily channel-level performance measures."""

    __tablename__ = "daily_channel_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False, index=True)

    gmv = Column(Float, nullable=False, default=0.0)
    net_revenue = Column(Float, nullable=False, default=0.0)
    contribution = Column(Float, nullable=False, default=0.0)
    returns_refunds = Column(Float, nullable=False, default=0.0)
    net_orders = Column(Integer, nullable=False, default=0)

    # Enforce one row per date+channel combination
    __table_args__ = (
        UniqueConstraint("date", "channel_id", name="uq_date_channel"),
    )

    channel = relationship("Channel", back_populates="daily_metrics")

    def __repr__(self):
        return (
            f"<DailyChannelMetric(date={self.date}, channel_id={self.channel_id}, "
            f"gmv={self.gmv}, net_revenue={self.net_revenue})>"
        )


class DailyBrandMetric(Base):
    """Daily brand-level totals used for the overview cards and trend charts."""

    __tablename__ = "daily_brand_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True, index=True)

    gmv = Column(Float, nullable=False, default=0.0)
    net_revenue = Column(Float, nullable=False, default=0.0)
    contribution = Column(Float, nullable=False, default=0.0)
    returns_refunds = Column(Float, nullable=False, default=0.0)
    net_orders = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return (
            f"<DailyBrandMetric(date={self.date}, gmv={self.gmv}, "
            f"net_revenue={self.net_revenue})>"
        )
