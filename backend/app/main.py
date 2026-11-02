import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.safe_mode import safe_mode_controller
from app.ai.model_registry import registry
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.investigations import router as investigations_router
from app.api.v1.tools import router as tools_router
from app.api.v1.admin_tools import router as admin_tools_router
from app.api.v1.admin_users import router as admin_users_router
from app.api.v1.browser import router as browser_router
from app.api.v1.terminal import router as terminal_router
from app.api.v1.agents import router as agents_router
from app.api.v1.collection import router as collection_router

logger = logging.getLogger("zaprica.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Safe Startup Lifecycle:
    1. Start normally.
    2. Read-only database health check.
    3. Initialize AI provider configuration without executing AI tasks.
    4. Set Main Head, Browser Head, Terminal Head to IDLE state.
    5. Set all worker execution to DISABLED.
    6. Ensure terminal execution is disabled by default.
    7. No automated background jobs or tool installs.
    """
    logger.info("Initializing ZAPRICA in Safe Startup Mode (ZAPRICA_SAFE_MODE=%s)...", settings.ZAPRICA_SAFE_MODE)

    # 1. Read-only database connectivity verification
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        logger.info("[Safe Startup] Database health check passed (read-only verification).")
    except Exception as e:
        logger.error("[Safe Startup] Database connection check failed: %s", e)

    # 2. AI Brain Provider Initialization (passive config only, no automatic task execution)
    try:
        active_provider = registry.get_provider()
        logger.info("[Safe Startup] AI Provider configured: %s (Passive readiness)", active_provider.__class__.__name__)
    except Exception as e:
        logger.warning("[Safe Startup] AI Provider config warning: %s", e)

    # 3. Agent States: IDLE, Workers: DISABLED
    safe_mode_controller.set_agent_state("main_head", "IDLE")
    safe_mode_controller.set_agent_state("browser_head", "IDLE")
    safe_mode_controller.set_agent_state("terminal_head", "IDLE")
    safe_mode_controller.set_workers_state("DISABLED")

    logger.info(
        "[Safe Startup] Agents initialized in IDLE state. Workers DISABLED. Terminal Execution: %s",
        safe_mode_controller.is_terminal_execution_enabled,
    )

    yield

    logger.info("ZAPRICA application shutdown completed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="ZAPRICA AI-powered OSINT Investigation Platform API with Safe Startup Mode",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    msg = first_error.get("msg", "Request validation failed.")
    loc = " -> ".join(str(l) for l in first_error.get("loc", []))
    detail = f"{loc}: {msg}" if loc else msg

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "validation_failed",
            "detail": detail,
            "status_code": status.HTTP_400_BAD_REQUEST,
            "validation_errors": exc.errors(),
        },
    )


# Mount routers
app.include_router(health_router, tags=["Health"])
app.include_router(auth_router, prefix=settings.API_V1_STR, tags=["Identity", "Authentication"])
app.include_router(investigations_router, prefix=settings.API_V1_STR, tags=["Investigations"])
app.include_router(tools_router, prefix=settings.API_V1_STR, tags=["Tools"])
app.include_router(admin_tools_router, prefix=settings.API_V1_STR, tags=["Administration", "Tools"])
app.include_router(admin_users_router, prefix=settings.API_V1_STR, tags=["Administration", "Users"])
app.include_router(browser_router, prefix=settings.API_V1_STR, tags=["Browser Head & Dedicated Browser"])
app.include_router(terminal_router, prefix=settings.API_V1_STR, tags=["Terminal Head & Isolated Sandbox"])
app.include_router(agents_router, prefix=settings.API_V1_STR, tags=["Multi-Agent Fleet & Supervision"])
app.include_router(collection_router, prefix=settings.API_V1_STR, tags=["Data Collection Engine (DCE)"])

from app.api.deps import get_current_user
from app.services.auth_service import AuthService
from app.schemas.auth import CurrentUserOut
from app.models.users import User
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession


@app.get(f"{settings.API_V1_STR}/me", response_model=CurrentUserOut, tags=["Identity"])
async def me_shortcut(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await AuthService.get_current_user_profile(db, current_user.id)


@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "0.1.0",
        "status": "operational",
        "safe_mode": safe_mode_controller.is_safe_mode,
        "terminal_execution": safe_mode_controller.is_terminal_execution_enabled,
        "docs": f"{settings.API_V1_STR}/docs",
    }
