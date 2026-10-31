from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health/live", response_model=HealthResponse, summary="Liveness probe")
async def liveness():
    """Returns 200 if the process is alive."""
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=HealthResponse, summary="Readiness probe")
async def readiness(
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Verifies that database connection is healthy."""
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ok" if db_status == "healthy" else "degraded",
        dependencies={"database": db_status}
    )
