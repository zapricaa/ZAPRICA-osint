from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.investigations import router as investigations_router
from app.api.v1.tools import router as tools_router
from app.api.v1.admin_tools import router as admin_tools_router
from app.api.v1.admin_users import router as admin_users_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="ZAPRICA AI-powered OSINT Investigation Platform API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
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


@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": "0.1.0",
        "status": "operational",
        "docs": f"{settings.API_V1_STR}/docs"
    }
