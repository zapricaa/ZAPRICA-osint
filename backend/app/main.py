"""ZAPRICA Backend — FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routes.investigations import router as investigations_router
from app.routes.tools import router as tools_router
from app.schemas import HealthResponse

logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("zaprica")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ZAPRICA backend...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down ZAPRICA backend")


app = FastAPI(
    title="ZAPRICA API",
    description="AI-powered OSINT investigation platform API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(investigations_router)
app.include_router(tools_router)


@app.get("/api/health", response_model=HealthResponse, tags=["health"])
async def health_check():
    db_status = "sqlite (development)"
    if "postgresql" in settings.database_url:
        db_status = "postgresql"

    return HealthResponse(
        status="healthy",
        version="0.1.0",
        database=db_status,
        services={
            "shell_worker": "disabled" if not settings.shell_worker_enabled else "enabled",
            "browser_worker": "disabled" if not settings.browser_worker_enabled else "enabled",
            "planner_llm": "configured" if settings.planner_llm_api_key else "not_configured",
            "extractor_llm": "configured" if settings.extractor_llm_api_key else "not_configured",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)
