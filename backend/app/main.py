import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.routers.analyse import router as analyse_router
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.history import router as history_router
from app.services.database import init_schema


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        init_schema()
    except RuntimeError as exc:
        logger.warning("Database schema init skipped at startup: %s", exc)
    yield


app = FastAPI(title="Bloom API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(history_router)
app.include_router(analyse_router)
