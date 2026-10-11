"""
GET /api/v1/channel-distribution — Per-channel comparison for a chosen metric.

Returns aggregated values per channel for the selected metric and date range.
Used for the horizontal bar chart on the dashboard.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyChannelMetric, Channel
from app.schemas import ChannelDistributionResponse, DistributionEntry, DateRange

router = APIRouter(prefix="/api/v1", tags=["Channel Distribution"])

VALID_METRICS = {"gmv", "net_revenue", "contribution", "returns_refunds", "net_orders"}


@router.get(
    "/channel-distribution",
    response_model=ChannelDistributionResponse,
    summary="Channel distribution by metric",
    description=(
        "Compares channels by a chosen metric within the selected date range. "
        "Valid metrics: gmv, net_revenue, contribution, returns_refunds, net_orders."
    ),
)
def get_channel_distribution(
    start_date: Optional[date] = Query(None, description="Start of date range (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End of date range (YYYY-MM-DD)"),
    metric: str = Query("net_revenue", description="Metric to compare"),
    business_scope: Optional[str] = Query(None, description="Filter by business scope"),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be on or before end_date.",
        )

    if metric not in VALID_METRICS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric '{metric}'. Must be one of: {', '.join(sorted(VALID_METRICS))}.",
        )

    # Dynamically select the metric column
    metric_column = getattr(DailyChannelMetric, metric)

    query = db.query(
        Channel.name.label("channel"),
        func.sum(metric_column).label("value"),
    ).join(Channel, DailyChannelMetric.channel_id == Channel.id)

    if start_date:
        query = query.filter(DailyChannelMetric.date >= start_date)
    if end_date:
        query = query.filter(DailyChannelMetric.date <= end_date)
    if business_scope:
        query = query.filter(Channel.business_scope == business_scope)

    rows = query.group_by(Channel.name).order_by(func.sum(metric_column).desc()).all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No distribution data found for the specified filters.",
        )

    # Get actual date range
    date_query = db.query(
        func.min(DailyChannelMetric.date),
        func.max(DailyChannelMetric.date),
    )
    if start_date:
        date_query = date_query.filter(DailyChannelMetric.date >= start_date)
    if end_date:
        date_query = date_query.filter(DailyChannelMetric.date <= end_date)
    min_date, max_date = date_query.one()

    distribution = [
        DistributionEntry(
            channel=row.channel,
            value=round(row.value, 2),
        )
        for row in rows
    ]

    return ChannelDistributionResponse(
        date_range=DateRange(start=min_date, end=max_date),
        metric=metric,
        distribution=distribution,
    )
