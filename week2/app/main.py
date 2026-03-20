from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import init_db
from .exceptions import LLMUnavailableError
from .routers import action_items, notes


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Action Item Extractor", lifespan=lifespan)


@app.exception_handler(LLMUnavailableError)
async def llm_unavailable_handler(_request, exc: LLMUnavailableError):
    return JSONResponse(
        status_code=503,
        content={"detail": exc.message},
    )


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    settings = get_settings()
    html_path = settings.frontend_dir / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


app.include_router(notes.router)
app.include_router(action_items.router)

_static = get_settings().frontend_dir
app.mount("/static", StaticFiles(directory=str(_static)), name="static")
