"""User routes for profile management"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...api.dependencies import get_current_user, get_db
from ...application.dtos.user_dtos import UserDto
from ...domain.entities.user import User

router = APIRouter()


@router.get("/me", response_model=UserDto)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return UserDto(
        id=current_user.id.value,
        email=str(current_user.email),
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        status=current_user.status.value,
        role=current_user.role.value,
        email_verified=current_user.email_verified,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    ) 