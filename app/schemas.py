"""
Pydantic response schemas for the Stelloid Command Center API.

These define the JSON contract between the backend and any frontend consumer.
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- Shared ----------

class DateRange(BaseModel):
    """Date range included in response payloads."""
    start: date
    end: date


# ---------- /channels ----------

class ChannelOut(BaseModel):
    """Schema for a single sales channel."""
    id: int
    name: str
    business_scope: str

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "Shopify",
                "business_scope": "DTC"
            }
        }
    }


# ---------- /overview ----------

class OverviewMetrics(BaseModel):
    """Summary KPI values for the brand overview cards."""
    gmv: float = Field(..., description="Gross Merchandise Value")
    net_revenue: float = Field(..., description="Net Revenue after returns and discounts")
    contribution: float = Field(..., description="Contribution margin")
    returns_refunds: float = Field(..., description="Total returns and refunds amount")
    net_orders: int = Field(..., description="Total net order count")
    average_order_value: float = Field(
        ..., description="Average Order Value (GMV / net_orders)"
    )


class OverviewResponse(BaseModel):
    """Response for GET /api/v1/overview."""
    date_range: DateRange
    overview: OverviewMetrics

    model_config = {
        "json_schema_extra": {
            "example": {
                "date_range": {"start": "2026-09-05", "end": "2026-10-04"},
                "overview": {
                    "gmv": 446792.50,
                    "net_revenue": 404360.20,
                    "contribution": 248120.10,
                    "returns_refunds": 42432.30,
                    "net_orders": 3950,
                    "average_order_value": 113.11
                }
            }
        }
    }


# ---------- /trends ----------

class TrendPoint(BaseModel):
    """A single data point in the time-series trend."""
    date: date
    net_revenue: float
    contribution: float


class TrendsResponse(BaseModel):
    """Response for GET /api/v1/trends."""
    date_range: DateRange
    trends: List[TrendPoint]

    model_config = {
        "json_schema_extra": {
            "example": {
                "date_range": {"start": "2026-09-05", "end": "2026-10-04"},
                "trends": [
                    {"date": "2026-09-05", "net_revenue": 13420.50, "contribution": 8120.30},
                    {"date": "2026-09-06", "net_revenue": 14100.00, "contribution": 8650.00}
                ]
            }
        }
    }


# ---------- /channel-distribution ----------

class DistributionEntry(BaseModel):
    """Per-channel value for a single metric."""
    channel: str
    value: float


class ChannelDistributionResponse(BaseModel):
    """Response for GET /api/v1/channel-distribution."""
    date_range: DateRange
    metric: str
    distribution: List[DistributionEntry]

    model_config = {
        "json_schema_extra": {
            "example": {
                "date_range": {"start": "2026-09-05", "end": "2026-10-04"},
                "metric": "gmv",
                "distribution": [
                    {"channel": "Amazon US", "value": 245100.00},
                    {"channel": "Shopify", "value": 142300.00},
                    {"channel": "Walmart Marketplace", "value": 59392.50}
                ]
            }
        }
    }


# ---------- /channel-performance ----------

class ChannelPerformanceEntry(BaseModel):
    """Full performance metrics for a single channel."""
    channel: str
    gmv: float
    net_revenue: float
    contribution: float
    returns_refunds: float
    net_orders: int
    average_order_value: float


class ChannelPerformanceResponse(BaseModel):
    """Response for GET /api/v1/channel-performance."""
    date_range: DateRange
    total_count: int = Field(default=3, description="Total number of channels matching filters")
    channels: List[ChannelPerformanceEntry]

    model_config = {
        "json_schema_extra": {
            "example": {
                "date_range": {"start": "2026-09-05", "end": "2026-10-04"},
                "total_count": 3,
                "channels": [
                    {
                        "channel": "Amazon US",
                        "gmv": 245100.00,
                        "net_revenue": 221000.00,
                        "contribution": 132600.00,
                        "returns_refunds": 24100.00,
                        "net_orders": 2150,
                        "average_order_value": 114.00
                    }
                ]
            }
        }
    }


# ---------- Error ----------

class ErrorResponse(BaseModel):
    """Standard error payload."""
    detail: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "start_date must be on or before end_date."
            }
        }
    }
