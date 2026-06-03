from fastapi import FastAPI

app = FastAPI(
    title="Book Management API",
    version="0.1.0",
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok"}