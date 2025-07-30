"""API dependencies for DDD architecture"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from ..core.config import settings
from ..core.security import verify_token
from ..db.database import get_db
from ..domain.repositories.unit_of_work import IUnitOfWork
from ..infrastructure.repositories.unit_of_work_impl import UnitOfWorkImpl
from ..infrastructure.external_services.ai_service import AIService
from ..infrastructure.external_services.payment_service import PaymentService
from ..infrastructure.external_services.payment_manager import PaymentManager
from ..infrastructure.external_services.storage_service import StorageService
from ..infrastructure.external_services.email_service import EmailService
from ..domain.entities.user import User
from ..infrastructure.orm.user_model import UserModel
from ..domain.enums import UserRole, UserStatus


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    try:
        # Verify token
        user_id = verify_token(credentials.credentials)
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user from database using repository
        unit_of_work = UnitOfWorkImpl(db)
        async with unit_of_work:
            from ..domain.value_objects.entity_ids import UserId
            user = await unit_of_work.users.get_by_id(UserId.from_str(user_id))
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            return user
            
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_user_model(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserModel:
    """Get current authenticated user as ORM model (for admin routes)"""
    try:
        # Verify token
        user_id = verify_token(credentials.credentials)
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user directly from database as ORM model
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current admin user"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_current_admin_user_model(current_user: UserModel = Depends(get_current_user_model)) -> UserModel:
    """Get current admin user as ORM model (for admin routes)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def get_unit_of_work(db: Session = Depends(get_db)) -> IUnitOfWork:
    """Get unit of work"""
    return UnitOfWorkImpl(db)


def get_ai_service() -> AIService:
    """Get AI service"""
    return AIService()


def get_payment_service() -> PaymentService:
    """Get payment service"""
    return PaymentService()


def get_payment_manager() -> PaymentManager:
    """Get payment manager with multi-provider support"""
    return PaymentManager()


def get_storage_service() -> StorageService:
    """Get storage service"""
    return StorageService()


def get_email_service() -> EmailService:
    """Get email service"""
    return EmailService() 