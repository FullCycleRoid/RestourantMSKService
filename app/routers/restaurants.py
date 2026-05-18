from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Restaurant
from app.schemas import RestaurantOut

router = APIRouter(tags=["restaurants"])


@router.get("/restaurants", response_model=list[RestaurantOut])
async def list_restaurants(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> list[RestaurantOut]:
    ring = request.app.state.garden_ring
    result = await session.execute(select(Restaurant).order_by(Restaurant.id))
    rows = result.scalars().all()
    return [
        RestaurantOut.model_validate(r)
        for r in rows
        if ring.contains(r.lat, r.lon)
    ]
