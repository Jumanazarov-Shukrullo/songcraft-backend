"""Get user profile use case"""

from typing import Optional

from ...domain.entities.user import User
from ...domain.value_objects.entity_ids import UserId
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...application.dtos.user_dtos import UserDto


class GetUserProfileUseCase:
    
    def __init__(self, unit_of_work: IUnitOfWork):
        self.unit_of_work = unit_of_work
    
    async def execute(self, user_id: int) -> Optional[UserDto]:
        """Get user profile by ID"""
        async with self.unit_of_work:
            user = await self.unit_of_work.users.get_by_id(UserId(user_id))
            
            if not user:
                return None
            
            return UserDto(
                id=user.id.value,
                email=user.email.address,
                first_name=user.first_name,
                last_name=user.last_name,
                status=user.status.value,
                role=user.role.value,
                email_verified=user.email_verified,
                created_at=user.created_at,
                last_login=user.last_login
            ) 