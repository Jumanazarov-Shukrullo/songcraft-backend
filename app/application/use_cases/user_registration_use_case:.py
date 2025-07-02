from typing import List, Optional
from datetime import datetime

from ...domain.entities.user import User
from ...domain.value_objects.email import Email
from ...domain.value_objects.entity_ids import UserId
from ...domain.repositories.unit_of_work import IUnitOfWork


"""User use case: UserRegistrationUseCase:"""

class UserRegistrationUseCase:
    """Use case for user registration"""
    
    def __init__(self, uow: IUnitOfWork, email_service):
        self.uow = uow
        self.email_service = email_service
    
    async def execute(self, dto: CreateUserDto) -> UserDto:
        """Register a new user"""
        try:
            async with self.uow:
                # Check if user already exists
                email_vo = Email(dto.email)
                existing_user = await self.uow.users.get_by_email(email_vo)
                
                if existing_user:
                    raise BusinessRuleViolationError("User with this email already exists")
                
                # Create user entity
                user_id = UserId(value=0)  # Will be set by repository
                hashed_password = get_password_hash(dto.password)
                
                user = User(
                    id=user_id,
                    email=email_vo,
                    hashed_password=hashed_password,
                    first_name=dto.first_name,
                    last_name=dto.last_name,
                    status=UserStatus.PENDING_VERIFICATION,
                    role=UserRole.USER
                )
                
                # Create aggregate
                user_aggregate = UserAggregate(user)
                
                # Save user
                saved_aggregate = await self.uow.users.save(user_aggregate)
                await self.uow.commit()
                
                # Send verification email
                await self._send_verification_email(saved_aggregate.user)
                
                # Convert to DTO
                return self._to_dto(saved_aggregate.user)
                
        except Exception as e:
            await self.uow.rollback()
            logger.error(f"Error registering user: {e}")
            raise
    
    async def _send_verification_email(self, user: User) -> None:
        """Send verification email to user"""
        try:
            verification_url = f"https://yourapp.com/verify-email?token={user.email_verification_token}"
            await self.email_service.send_verification_email(
                str(user.email),
                user.full_name,
                verification_url
            )
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            # Don't fail registration if email fails
    
    def _to_dto(self, user: User) -> UserDto:
        """Convert User entity to DTO"""
        return UserDto(
            id=user.id.value,
            email=str(user.email),
            first_name=user.first_name,
            last_name=user.last_name,
            status=user.status.value,
            role=user.role.value,
            email_verified=user.email_verified,
            created_at=user.created_at,
            last_login=user.last_login
        )


