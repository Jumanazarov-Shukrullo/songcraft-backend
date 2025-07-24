"""Authentication routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from ...api.dependencies import get_unit_of_work, get_email_service
from ...application.use_cases.register_user import RegisterUserUseCase
from ...application.use_cases.login_user import LoginUserUseCase
from ...application.use_cases.forgot_password_use_case import ForgotPasswordUseCase
from ...application.use_cases.reset_password_use_case import ResetPasswordUseCase, ResetPasswordDto
from ...application.use_cases.email_verification_use_case import EmailVerificationUseCase
from ...application.use_cases.google_oauth_use_case import GoogleOAuthUseCase
from ...application.use_cases.google_oauth_redirect_use_case import GoogleOAuthRedirectUseCase
from ...application.dtos.user_dtos import CreateUserDto, LoginUserDto, UserResponse, ForgotPasswordDto, ForgotPasswordResponse, VerifyEmailDto, RefreshTokenDto, GoogleOAuthDto, GoogleOAuthCodeDto, GoogleOAuthUrlResponse
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.external_services.email_service import EmailService

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: CreateUserDto,
    unit_of_work: IUnitOfWork = Depends(get_unit_of_work),
    email_service: EmailService = Depends(get_email_service)
):
    """Register a new user"""
    use_case = RegisterUserUseCase(unit_of_work, email_service)
    try:
        return await use_case.execute(user_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login", response_model=UserResponse)
async def login_user(
    login_data: LoginUserDto,
    unit_of_work: IUnitOfWork = Depends(get_unit_of_work)
):
    """Login user"""
    use_case = LoginUserUseCase(unit_of_work)
    try:
        return await use_case.execute(login_data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    request: ForgotPasswordDto,
    unit_of_work: IUnitOfWork = Depends(get_unit_of_work),
    email_service: EmailService = Depends(get_email_service)
):
    """Handle forgot password request"""
    use_case = ForgotPasswordUseCase(unit_of_work, email_service)
    try:
        return await use_case.execute(request)
    except Exception as e:
        return ForgotPasswordResponse(
            message="If an account with that email exists, a password reset link has been sent.",
            success=True
        )


@router.post("/reset-password", response_model=ForgotPasswordResponse)
async def reset_password(
    request: ResetPasswordDto,
    unit_of_work: IUnitOfWork = Depends(get_unit_of_work)
):
    """Reset password with token"""
    use_case = ResetPasswordUseCase(unit_of_work)
    try:
        return await use_case.execute(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailDto,
    unit_of_work: IUnitOfWork = Depends(get_unit_of_work)
):
    """Verify user email with token"""
    use_case = EmailVerificationUseCase(unit_of_work)
    try:
        await use_case.execute(request)
        return {"message": "Email verified successfully", "success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/google/url", response_model=GoogleOAuthUrlResponse)
async def get_google_oauth_url():
    """Get Google OAuth authorization URL"""
    try:
        use_case = GoogleOAuthRedirectUseCase()  # Don't need unit_of_work for URL generation
        return use_case.get_authorization_url()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to generate Google OAuth URL")


@router.post("/google/callback", response_model=UserResponse)
async def google_oauth_callback(
    request: GoogleOAuthCodeDto,
    unit_of_work: IUnitOfWork = Depends(get_unit_of_work)
):
    """Handle Google OAuth callback with authorization code"""
    use_case = GoogleOAuthRedirectUseCase(unit_of_work)
    try:
        return await use_case.handle_callback(request.code, request.state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Google authentication failed")


@router.post("/google", response_model=UserResponse)
async def google_oauth_token(
    request: GoogleOAuthDto,
    unit_of_work: IUnitOfWork = Depends(get_unit_of_work)
):
    """Google OAuth authentication with ID token"""
    use_case = GoogleOAuthRedirectUseCase(unit_of_work)
    try:
        return await use_case.handle_id_token(request.google_token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Google authentication failed")


@router.post("/refresh")
async def refresh_token(
    request: RefreshTokenDto,
    unit_of_work: IUnitOfWork = Depends(get_unit_of_work)
):
    """Refresh access token"""
    from ...core.security import verify_refresh_token, create_access_token
    try:
        user_id = verify_refresh_token(request.refresh_token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        new_access_token = create_access_token(user_id)
        return {"access_token": new_access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")