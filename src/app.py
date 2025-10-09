import os
from contextlib import asynccontextmanager

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI

from src.routers.github import router as github_router
from src.routers.kanban import router as kanban_router
from src.routers.prs import router as prs_router
from src.services.db import init_db

load_dotenv(find_dotenv())


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="FlowHub API",
    description="API de métriques Kanban & Pull Requests (avec snapshot) pour CI/CD et télémétrie. Swagger UI sur /docs.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(github_router)
app.include_router(kanban_router)
app.include_router(prs_router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
