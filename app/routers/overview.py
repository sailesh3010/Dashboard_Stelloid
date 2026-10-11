"""
GET /api/v1/overview — Brand overview summary KPI cards.

Aggregates daily metrics across the selected date range, optionally
filtered by channel and/or business scope.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyBrandMetric, DailyChannelMetric, Channel
from app.schemas import OverviewResponse, OverviewMetrics, DateRange

router = APIRouter(prefix="/api/v1", tags=["Overview"])


@router.get(
    "/overview",
    response_model=OverviewResponse,
    summary="Brand overview",
    description=(
        "Returns summary KPI cards (GMV, net revenue, contribution, "
        "returns/refunds, net orders, average order value) for the "
        "selected date range. Supports optional channel and business_scope filters."
    ),
)
def get_overview(
    start_date: Optional[date] = Query(None, description="Start of date range (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End of date range (YYYY-MM-DD)"),
    channel: Optional[str] = Query(None, description="Filter by channel name"),
    business_scope: Optional[str] = Query(None, description="Filter by business scope"),
    db: Session = Depends(get_db),
):
    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be on or before end_date.",
        )

    # If channel or business_scope filters are applied, aggregate from channel metrics
    if channel or business_scope:
        query = db.query(
            func.sum(DailyChannelMetric.gmv).label("gmv"),
            func.sum(DailyChannelMetric.net_revenue).label("net_revenue"),
            func.sum(DailyChannelMetric.contribution).label("contribution"),
            func.sum(DailyChannelMetric.returns_refunds).label("returns_refunds"),
            func.sum(DailyChannelMetric.net_orders).label("net_orders"),
        ).join(Channel, DailyChannelMetric.channel_id == Channel.id)

        if start_date:
            query = query.filter(DailyChannelMetric.date >= start_date)
        if end_date:
            query = query.filter(DailyChannelMetric.date <= end_date)
        if channel:
            query = query.filter(Channel.name == channel)
        if business_scope:
            query = query.filter(Channel.business_scope == business_scope)

        result = query.one()
    else:
        # Use pre-aggregated brand metrics
        query = db.query(
            func.sum(DailyBrandMetric.gmv).label("gmv"),
            func.sum(DailyBrandMetric.net_revenue).label("net_revenue"),
            func.sum(DailyBrandMetric.contribution).label("contribution"),
            func.sum(DailyBrandMetric.returns_refunds).label("returns_refunds"),
            func.sum(DailyBrandMetric.net_orders).label("net_orders"),
        )

        if start_date:
            query = query.filter(DailyBrandMetric.date >= start_date)
        if end_date:
            query = query.filter(DailyBrandMetric.date <= end_date)

        result = query.one()

    # Handle empty result set
    if result.gmv is None:
        raise HTTPException(
            status_code=404,
            detail="No data found for the specified filters.",
        )

    gmv = round(result.gmv, 2)
    net_revenue = round(result.net_revenue, 2)
    contribution = round(result.contribution, 2)
    returns_refunds = round(result.returns_refunds, 2)
    net_orders = int(result.net_orders)
    avg_order_value = round(gmv / net_orders, 2) if net_orders > 0 else 0.0

    # Resolve the actual date range used
    if channel or business_scope:
        date_query = db.query(
            func.min(DailyChannelMetric.date),
            func.max(DailyChannelMetric.date),
        ).join(Channel, DailyChannelMetric.channel_id == Channel.id)
        if start_date:
            date_query = date_query.filter(DailyChannelMetric.date >= start_date)
        if end_date:
            date_query = date_query.filter(DailyChannelMetric.date <= end_date)
        if channel:
            date_query = date_query.filter(Channel.name == channel)
        if business_scope:
            date_query = date_query.filter(Channel.business_scope == business_scope)
        min_date, max_date = date_query.one()
    else:
        date_query = db.query(
            func.min(DailyBrandMetric.date),
            func.max(DailyBrandMetric.date),
        )
        if start_date:
            date_query = date_query.filter(DailyBrandMetric.date >= start_date)
        if end_date:
            date_query = date_query.filter(DailyBrandMetric.date <= end_date)
        min_date, max_date = date_query.one()

    return OverviewResponse(
        date_range=DateRange(start=min_date, end=max_date),
        overview=OverviewMetrics(
            gmv=gmv,
            net_revenue=net_revenue,
            contribution=contribution,
            returns_refunds=returns_refunds,
            net_orders=net_orders,
            average_order_value=avg_order_value,
        ),
    )
