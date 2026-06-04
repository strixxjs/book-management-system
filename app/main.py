from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.api.v1.books import router as books_router
from app.core.errors import register_exception_handlers
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Book Management API",
    version="0.1.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(books_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}
