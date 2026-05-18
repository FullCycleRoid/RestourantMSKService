from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import get_settings
from app.geo import GardenRing

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.garden_ring = GardenRing.load_default()
    app.state.jinja = Environment(
        loader=FileSystemLoader(str(FRONTEND_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Restaurants in Garden Ring", lifespan=lifespan)

    if (FRONTEND_DIR / "static").exists():
        app.mount(
            "/static",
            StaticFiles(directory=FRONTEND_DIR / "static"),
            name="static",
        )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    async def index():
        tpl = app.state.jinja.get_template("index.html")
        html = tpl.render(yandex_js_api_key=get_settings().yandex_js_api_key)
        return HTMLResponse(html)

    # Routers registered in later tasks
    from app.routers import garden_ring, restaurants, user_points
    app.include_router(garden_ring.router, prefix="/api")
    app.include_router(restaurants.router, prefix="/api")
    app.include_router(user_points.router, prefix="/api")

    return app


app = create_app()
