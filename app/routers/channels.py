"""
GET /api/v1/channels — List all available sales channels.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Channel
from app.schemas import ChannelOut

router = APIRouter(prefix="/api/v1", tags=["Channels"])


@router.get(
    "/channels",
    response_model=List[ChannelOut],
    summary="List all channels",
    description="Returns every available sales channel with its business scope.",
)
def list_channels(db: Session = Depends(get_db)):
    channels = db.query(Channel).order_by(Channel.id).all()
    return channels
