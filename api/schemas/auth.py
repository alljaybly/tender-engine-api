from typing import Optional
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Payload for user registration."""
    email: str = Field(
        ...,
        description="User email address (used as login identifier)",
        examples=["user@example.com"],
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    )
    password: str = Field(
        ...,
        min_length=6,
        description="Password (minimum 6 characters)",
        examples=["secure_password_123"],
    )
    full_name: str = Field(
        default="",
        description="Optional display name",
        examples=["John Doe"],
    )


class LoginRequest(BaseModel):
    """Payload for user login."""
    email: str = Field(
        ...,
        description="Registered email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        description="Account password",
        examples=["secure_password_123"],
    )


class TokenResponse(BaseModel):
    """Response returned after successful login/registration."""
    access_token: str = Field(..., description="JWT access token (Bearer token)")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(default=86400, description="Token expiration in seconds")


class UserResponse(BaseModel):
    """Public user profile returned by the API."""
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    full_name: str = Field(default="", description="Display name")
    plan: str = Field(default="free", description="Subscription plan")
    is_active: bool = Field(default=True, description="Whether the account is active")
    created_at: Optional[str] = Field(default=None, description="Account creation timestamp")


class ErrorDetail(BaseModel):
    """Standard error detail for auth failures."""
    detail: str = Field(..., description="Error message")