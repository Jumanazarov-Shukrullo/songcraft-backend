from typing import List, Optional
from datetime import datetime

from ...domain.entities.user import User
from ...domain.value_objects.email import Email
from ...domain.value_objects.entity_ids import UserId
from ...domain.repositories.unit_of_work import IUnitOfWork


"""User use case: EmailVerificationUseCase:"""

class EmailVerificationUseCase:
    """Use case for email verification"""
    
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow
    
    async def execute(self, dto: VerifyEmailTokenDto) -> UserDto:
        """Verify user email with token"""
        async with self.uow:
            # Find user by verification token
            # This would need a repository method to find by token
            # For now, simplified implementation
            
            # Verify token and get user
            user_aggregate = await self._get_user_by_verification_token(dto.token)
            
            if not user_aggregate:
                raise ValidationError("Invalid or expired verification token")
            
            # Verify email
            user_aggregate.user.verify_email()
            
            # Save user
            await self.uow.users.save(user_aggregate)
            await self.uow.commit()
            
            # Convert to DTO
            return UserDto(
                id=user_aggregate.user.id.value,
                email=str(user_aggregate.user.email),
                first_name=user_aggregate.user.first_name,
                last_name=user_aggregate.user.last_name,
                status=user_aggregate.user.status.value,
                role=user_aggregate.user.role.value,
                email_verified=user_aggregate.user.email_verified,
                created_at=user_aggregate.user.created_at,
                last_login=user_aggregate.user.last_login
            )
    
    async def _get_user_by_verification_token(self, token: str) -> Optional[UserAggregate]:
        """Get user by verification token - simplified implementation"""
        # This would be implemented in the repository
        # For now, return None
        return None


