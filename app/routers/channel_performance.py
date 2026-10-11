"""
GET /api/v1/channel-performance — Full performance metrics per channel.

Returns all core KPIs for each channel, aggregated over the selected date range.
Used for the channel performance comparison table/section on the dashboard.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyChannelMetric, Channel
from app.schemas import ChannelPerformanceResponse, ChannelPerformanceEntry, DateRange

router = APIRouter(prefix="/api/v1", tags=["Channel Performance"])


@router.get(
    "/channel-performance",
    response_model=ChannelPerformanceResponse,
    summary="Channel performance",
    description=(
        "Returns full performance metrics (GMV, net revenue, contribution, "
        "returns/refunds, net orders, average order value) for each channel "
        "within the selected date range."
    ),
)
def get_channel_performance(
    start_date: Optional[date] = Query(None, description="Start of date range (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End of date range (YYYY-MM-DD)"),
    channel: Optional[str] = Query(None, description="Filter by channel name"),
    business_scope: Optional[str] = Query(None, description="Filter by business scope"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Max channels to return (pagination)"),
    offset: int = Query(0, ge=0, description="Number of channels to skip (pagination)"),
    db: Session = Depends(get_db),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be on or before end_date.",
        )

    query = db.query(
        Channel.name.label("channel"),
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

    rows = query.group_by(Channel.name).order_by(func.sum(DailyChannelMetric.gmv).desc()).all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No channel performance data found for the specified filters.",
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

    total_count = len(rows)
    paged_rows = rows[offset : offset + limit] if limit is not None else rows[offset:]

    channels_out = []
    for row in paged_rows:
        gmv = round(row.gmv, 2)
        net_orders = int(row.net_orders)
        avg_order_value = round(gmv / net_orders, 2) if net_orders > 0 else 0.0

        channels_out.append(
            ChannelPerformanceEntry(
                channel=row.channel,
                gmv=gmv,
                net_revenue=round(row.net_revenue, 2),
                contribution=round(row.contribution, 2),
                returns_refunds=round(row.returns_refunds, 2),
                net_orders=net_orders,
                average_order_value=avg_order_value,
            )
        )

    return ChannelPerformanceResponse(
        date_range=DateRange(start=min_date, end=max_date),
        total_count=total_count,
        channels=channels_out,
    )
