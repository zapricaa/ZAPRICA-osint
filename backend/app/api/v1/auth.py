from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import UserCreate, UserLogin, TokenResponse, CurrentUserOut
from app.services.auth_service import AuthService
from app.api.deps import get_current_user
from app.models.users import User

router = APIRouter()


@router.post(
    "/auth/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account"
)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new user and initial workspace."""
    user, workspace, membership = await AuthService.register_user(db, data)
    login_data = UserLogin(email=data.email, password=data.password)
    return await AuthService.authenticate_user(db, login_data)


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Authenticate user and issue JWT"
)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate with email and password."""
    return await AuthService.authenticate_user(db, data)


@router.get(
    "/me",
    response_model=CurrentUserOut,
    summary="Get current authenticated user and workspace memberships"
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns the authenticated user's profile and active workspace memberships."""
    return await AuthService.get_current_user_profile(db, current_user.id)
