from typing import List, Optional
from datetime import datetime

from ...domain.entities.user import User
from ...domain.value_objects.email import Email
from ...domain.value_objects.entity_ids import UserId
from ...domain.repositories.unit_of_work import IUnitOfWork


"""User use case: UserLoginUseCase:"""

class UserLoginUseCase:
    """Use case for user authentication"""
    
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow
    
    async def execute(self, dto: LoginUserDto) -> TokenDto:
        """Authenticate user and return tokens"""
        async with self.uow:
            # Get user by email
            email_vo = Email(dto.email)
            user_aggregate = await self.uow.users.get_by_email(email_vo)
            
            if not user_aggregate:
                raise NotFoundError("User not found")
            
            user = user_aggregate.user
            
            # Verify password
            if not verify_password(dto.password, user.hashed_password):
                raise ValidationError("Invalid credentials")
            
            # Check user status
            if not user.email_verified:
                raise BusinessRuleViolationError("Email not verified")
            
            if user.status != UserStatus.ACTIVE:
                raise BusinessRuleViolationError("Account is not active")
            
            # Record login
            user.record_login()
            await self.uow.users.save(user_aggregate)
            await self.uow.commit()
            
            # Create tokens
            access_token = create_access_token(subject=str(user.id.value))
            refresh_token = create_refresh_token(subject=str(user.id.value))
            
            return TokenDto(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer"
            )


