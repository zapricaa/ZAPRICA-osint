import uuid
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    workspace_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class WorkspaceMembershipOut(BaseModel):
    workspace_id: uuid.UUID
    workspace_name: str
    workspace_slug: str
    role: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class CurrentUserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    status: str
    memberships: List[WorkspaceMembershipOut] = []

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: CurrentUserOut
    active_workspace_id: Optional[uuid.UUID] = None
