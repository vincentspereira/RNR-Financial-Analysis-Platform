"""
Authentication API endpoints
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.schemas.auth import (
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    RegisterRequest,
    UserResponse,
)
from app.services.auth.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_client_info(request: Request) -> tuple[str, str]:
    """Extract client IP and user agent from request"""
    # Get real IP address (considering proxies)
    ip_address = (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.headers.get("X-Real-IP", "").strip()
        or request.client.host
        if request.client
        else "unknown"
    )
    
    user_agent = request.headers.get("User-Agent", "unknown")
    return ip_address, user_agent


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Register a new user account with email and password",
    responses={
        201: {"description": "User registered successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        409: {"model": ErrorResponse, "description": "User already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def register(
    request: Request,
    user_data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    Register a new user account
    
    - **email**: Valid email address (will be used for login)
    - **password**: Strong password (min 8 chars, must include uppercase, lowercase, digit, special char)
    - **first_name**: User's first name
    - **last_name**: User's last name
    
    Returns the created user information (without password)
    """
    ip_address, user_agent = get_client_info(request)
    
    user, error = await auth_service.register_user(
        email=user_data.email,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        db=db,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    if error:
        if "already exists" in error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
    
    return UserResponse.from_orm(user)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate user and return access/refresh tokens",
    responses={
        200: {"description": "Login successful"},
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        403: {"model": ErrorResponse, "description": "Account inactive"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def login(
    request: Request,
    credentials: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    Authenticate user and create session
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns access token, refresh token, and user information
    """
    ip_address, user_agent = get_client_info(request)
    
    # Authenticate user
    user, error = await auth_service.authenticate_user(
        email=credentials.email,
        password=credentials.password,
        db=db,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    if error:
        if "inactive" in error.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error
            )
    
    # Create session and tokens
    tokens, session_error = await auth_service.create_user_session(
        user=user,
        db=db,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    if session_error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=session_error
        )
    
    return LoginResponse(**tokens)


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token",
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"model": ErrorResponse, "description": "Invalid or expired refresh token"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def refresh_token(
    request: Request,
    token_data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    Refresh access token using refresh token
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token (refresh token remains the same)
    """
    ip_address, user_agent = get_client_info(request)
    
    tokens, error = await auth_service.refresh_token(
        refresh_token=token_data.refresh_token,
        db=db,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error
        )
    
    return RefreshTokenResponse(**tokens)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="User logout",
    description="Logout user and revoke session",
    responses={
        200: {"description": "Logout successful"},
        401: {"model": ErrorResponse, "description": "Invalid token"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def logout(
    request: Request,
    authorization: Annotated[Optional[str], Header()] = None,
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    """
    Logout user and revoke current session
    
    Requires Authorization header with Bearer token
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    access_token = authorization.split(" ")[1]
    ip_address, user_agent = get_client_info(request)
    
    success, error = await auth_service.logout_user(
        access_token=access_token,
        db=db,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error
        )
    
    return MessageResponse(message="Logout successful")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get current authenticated user information",
    responses={
        200: {"description": "User information retrieved"},
        401: {"model": ErrorResponse, "description": "Invalid or expired token"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
    db: Annotated[AsyncSession, Depends(get_async_session)] = None,
):
    """
    Get current authenticated user information
    
    Requires Authorization header with Bearer token
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    access_token = authorization.split(" ")[1]
    
    user = await auth_service.verify_session(access_token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return UserResponse.from_orm(user)