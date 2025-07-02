from typing import List, Optional
from datetime import datetime

from ...domain.entities.user import User
from ...domain.value_objects.email import Email
from ...domain.value_objects.entity_ids import UserId
from ...domain.repositories.unit_of_work import IUnitOfWork


"""User use case: GetUserUseCase:"""

class GetUserUseCase:
    """Use case for getting user information"""
    
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow
    
    async def execute(self, user_id: int) -> UserDto:
        """Get user by ID"""
        async with self.uow:
            user_id_vo = UserId(user_id)
            user_aggregate = await self.uow.users.get_by_id(user_id_vo)
            
            if not user_aggregate:
                raise NotFoundError("User not found")
            
            user = user_aggregate.user
            
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