"""
Authentication routes: register, login, current user profile.

Uses SQLite for persistence, bcrypt for password hashing, and JWT for tokens.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from ..services.auth import hash_password, verify_password, create_access_token, decode_access_token, JWT_EXPIRY_HOURS
from ..services.database import get_db, close_db

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

# HTTPBearer extracts the Bearer token from the Authorization header
security = HTTPBearer(auto_error=False)


def get_expires_in() -> int:
    """Return JWT expiration in seconds."""
    return JWT_EXPIRY_HOURS * 3600


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    FastAPI dependency that extracts and verifies the JWT Bearer token,
    then returns the authenticated user dict.

    Usage in protected routes:
        @router.get("/protected")
        async def protected_route(current_user: dict = Depends(get_current_user)):
            ...
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Fetch user from database
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        user = dict(row)

        # Check account active
        if not user.get("is_active"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        return user
    finally:
        await close_db(db)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(payload: RegisterRequest):
    """
    Create a new user account with email and password.

    - Email must be unique (not already registered)
    - Password must be at least 6 characters
    - Returns a JWT access token on success (auto-login after registration)
    """
    logger.info("[AUTH] Registration attempt: email=%s", payload.email)

    db = await get_db()
    try:
        # Check if email already exists
        cursor = await db.execute("SELECT id FROM users WHERE email = ?", (payload.email,))
        existing = await cursor.fetchone()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        # Hash the password
        hashed = hash_password(payload.password)

        # Insert new user
        cursor = await db.execute(
            "INSERT INTO users (email, hashed_password, full_name) VALUES (?, ?, ?)",
            (payload.email, hashed, payload.full_name),
        )
        await db.commit()
        user_id = cursor.lastrowid

        logger.info("[AUTH] User registered: id=%s, email=%s", user_id, payload.email)

        # Create JWT token (auto-login after registration)
        token = create_access_token(
            data={"sub": str(user_id), "email": payload.email},
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=get_expires_in(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[AUTH] Registration error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again.",
        )
    finally:
        await close_db(db)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive a JWT token",
)
async def login(payload: LoginRequest):
    """
    Authenticate with email and password.

    - Returns a JWT access token valid for 24 hours (configurable via JWT_EXPIRY_HOURS env var)
    - Include this token in the `Authorization: Bearer <token>` header for protected endpoints
    """
    logger.info("[AUTH] Login attempt: email=%s", payload.email)

    db = await get_db()
    try:
        # Look up user by email
        cursor = await db.execute("SELECT * FROM users WHERE email = ?", (payload.email,))
        row = await cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        user = dict(row)

        # Check account active
        if not user.get("is_active"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        # Verify password
        if not verify_password(payload.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        logger.info("[AUTH] Login successful: id=%s, email=%s", user["id"], payload.email)

        # Create JWT token
        token = create_access_token(
            data={"sub": str(user["id"]), "email": user["email"]},
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=get_expires_in(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[AUTH] Login error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again.",
        )
    finally:
        await close_db(db)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Return the profile of the currently authenticated user.

    Requires a valid Bearer token in the `Authorization` header.
    """
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user.get("full_name", ""),
        plan=current_user.get("plan", "free"),
        is_active=bool(current_user.get("is_active", True)),
        created_at=current_user.get("created_at"),
    )