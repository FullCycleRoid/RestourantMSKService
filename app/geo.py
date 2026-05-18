import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shapely.geometry import Point, shape
from shapely.geometry.polygon import Polygon

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "garden_ring.geojson"


@dataclass(frozen=True)
class GardenRing:
    polygon: Polygon
    feature: dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> "GardenRing":
        feature = json.loads(path.read_text(encoding="utf-8"))
        poly = shape(feature["geometry"])
        if not isinstance(poly, Polygon):
            raise ValueError("GeoJSON geometry must be a Polygon")
        return cls(polygon=poly, feature=feature)

    @classmethod
    def load_default(cls) -> "GardenRing":
        return cls.load(DEFAULT_PATH)

    def contains(self, lat: float, lon: float) -> bool:
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"lat out of range: {lat}")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"lon out of range: {lon}")
        return self.polygon.contains(Point(lon, lat))

    def as_geojson(self) -> dict[str, Any]:
        return self.feature
