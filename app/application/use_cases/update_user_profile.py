"""Update user profile use case"""

from ...domain.value_objects.entity_ids import UserId
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...application.dtos.user_dtos import UserDto


class UpdateUserProfileRequest:
    def __init__(self, first_name: str = None, last_name: str = None):
        self.first_name = first_name
        self.last_name = last_name


class UpdateUserProfileUseCase:
    
    def __init__(self, unit_of_work: IUnitOfWork):
        self.unit_of_work = unit_of_work
    
    async def execute(self, user_id: int, request: UpdateUserProfileRequest) -> UserDto:
        """Update user profile"""
        async with self.unit_of_work:
            user = await self.unit_of_work.users.get_by_id(UserId(user_id))
            
            if not user:
                raise ValueError("User not found")
            
            # Update fields if provided
            if request.first_name is not None:
                user.first_name = request.first_name
            if request.last_name is not None:
                user.last_name = request.last_name
            
            # Save changes
            await self.unit_of_work.users.update(user)
            await self.unit_of_work.commit()
            
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