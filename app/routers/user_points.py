from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import UserPoint
from app.schemas import UserPointIn, UserPointOut

router = APIRouter(tags=["user-points"])


@router.get("/user-points", response_model=list[UserPointOut])
async def list_points(
    session: AsyncSession = Depends(get_session),
) -> list[UserPointOut]:
    result = await session.execute(select(UserPoint).order_by(UserPoint.id))
    return [UserPointOut.model_validate(p) for p in result.scalars().all()]


@router.post(
    "/user-points",
    response_model=UserPointOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_point(
    payload: UserPointIn,
    session: AsyncSession = Depends(get_session),
) -> UserPointOut:
    point = UserPoint(lat=payload.lat, lon=payload.lon, name=payload.name)
    session.add(point)
    await session.commit()
    await session.refresh(point)
    return UserPointOut.model_validate(point)


@router.delete("/user-points/{point_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_point(
    point_id: int,
    session: AsyncSession = Depends(get_session),
) -> Response:
    result = await session.execute(
        delete(UserPoint).where(UserPoint.id == point_id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="point not found")
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
