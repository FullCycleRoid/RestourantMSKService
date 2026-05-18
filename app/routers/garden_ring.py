from fastapi import APIRouter, Request

router = APIRouter(tags=["garden-ring"])


@router.get("/garden-ring")
async def get_garden_ring(request: Request) -> dict:
    return request.app.state.garden_ring.as_geojson()
