from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str | None = None
    rating: float
    lat: float
    lon: float


class UserPointIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    name: str | None = Field(default=None, max_length=100)


class UserPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    lat: float
    lon: float
    created_at: datetime
