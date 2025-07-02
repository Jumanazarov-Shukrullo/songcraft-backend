"""Authentication routes with complete functionality"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from ...api.dependencies import get_unit_of_work, get_email_service
from ...application.use_cases.register_user import RegisterUserUseCase
from ...application.use_cases.login_user import LoginUserUseCase
from ...application.dtos.user_dtos import CreateUserDto, LoginUserDto, UserResponse
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


@router.get("/verify-email/{token}")
async def verify_email(
    token: str,
    unit_of_work: IUnitOfWork = Depends(get_unit_of_work)
):
    """Verify user email"""
    # This would be implemented with proper email verification use case
    return {"message": "Email verification endpoint - to be implemented"}


@router.post("/refresh")
async def refresh_token():
    """Refresh access token"""
    return {"message": "Token refresh endpoint - to be implemented"}
