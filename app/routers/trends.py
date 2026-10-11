"""
GET /api/v1/trends — Time-series trend for net revenue and contribution.

Returns daily data points within the selected date range, optionally
filtered by channel and/or business scope.
"""

from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyBrandMetric, DailyChannelMetric, Channel
from app.schemas import TrendsResponse, TrendPoint, DateRange

router = APIRouter(prefix="/api/v1", tags=["Trends"])


@router.get(
    "/trends",
    response_model=TrendsResponse,
    summary="Revenue & contribution trend",
    description=(
        "Returns a time-series of daily net revenue and contribution "
        "for the selected date range. Used for the trend chart."
    ),
)
def get_trends(
    start_date: Optional[date] = Query(None, description="Start of date range (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End of date range (YYYY-MM-DD)"),
    channel: Optional[str] = Query(None, description="Filter by channel name"),
    business_scope: Optional[str] = Query(None, description="Filter by business scope"),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be on or before end_date.",
        )

    if channel or business_scope:
        # Aggregate channel metrics grouped by date
        query = db.query(
            DailyChannelMetric.date,
            func.sum(DailyChannelMetric.net_revenue).label("net_revenue"),
            func.sum(DailyChannelMetric.contribution).label("contribution"),
        ).join(Channel, DailyChannelMetric.channel_id == Channel.id)

        if start_date:
            query = query.filter(DailyChannelMetric.date >= start_date)
        if end_date:
            query = query.filter(DailyChannelMetric.date <= end_date)
        if channel:
            query = query.filter(Channel.name == channel)
        if business_scope:
            query = query.filter(Channel.business_scope == business_scope)

        rows = query.group_by(DailyChannelMetric.date).order_by(DailyChannelMetric.date).all()
    else:
        # Use pre-aggregated brand metrics
        query = db.query(
            DailyBrandMetric.date,
            DailyBrandMetric.net_revenue,
            DailyBrandMetric.contribution,
        )

        if start_date:
            query = query.filter(DailyBrandMetric.date >= start_date)
        if end_date:
            query = query.filter(DailyBrandMetric.date <= end_date)

        rows = query.order_by(DailyBrandMetric.date).all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No trend data found for the specified filters.",
        )

    trends = [
        TrendPoint(
            date=row.date,
            net_revenue=round(row.net_revenue, 2),
            contribution=round(row.contribution, 2),
        )
        for row in rows
    ]

    return TrendsResponse(
        date_range=DateRange(start=trends[0].date, end=trends[-1].date),
        trends=trends,
    )
