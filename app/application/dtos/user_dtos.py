"""User DTOs for API layer"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class CreateUserDto(BaseModel):
    """DTO for user registration"""
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class LoginUserDto(BaseModel):
    """DTO for user login"""
    email: EmailStr
    password: str


class ForgotPasswordDto(BaseModel):
    """DTO for forgot password request"""
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """DTO for forgot password response"""
    message: str
    success: bool = True


class VerifyEmailDto(BaseModel):
    """DTO for email verification request"""
    token: str


class RefreshTokenDto(BaseModel):
    """DTO for refresh token request"""
    refresh_token: str


class GoogleOAuthDto(BaseModel):
    """DTO for Google OAuth request"""
    google_token: str


class GoogleOAuthCodeDto(BaseModel):
    """DTO for Google OAuth authorization code"""
    code: str
    state: Optional[str] = None


class GoogleOAuthUrlResponse(BaseModel):
    """DTO for Google OAuth authorization URL response"""
    authorization_url: str
    state: str


class UserDto(BaseModel):
    """DTO for user response"""
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: str
    role: str
    email_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class TokenDto(BaseModel):
    """DTO for authentication tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User response with token"""
    user: UserDto
    tokens: TokenDto