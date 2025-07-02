"""Login user use case"""

from datetime import datetime

from ...domain.value_objects.email import Email
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...application.dtos.user_dtos import LoginUserDto, UserResponse, UserDto, TokenDto
from ...core.security import verify_password, create_access_token, create_refresh_token


class LoginUserUseCase:
    
    def __init__(self, unit_of_work: IUnitOfWork):
        self.unit_of_work = unit_of_work
    
    async def execute(self, request: LoginUserDto) -> UserResponse:
        async with self.unit_of_work:
            email = Email(request.email)
            
            # Get user by email
            user = await self.unit_of_work.users.get_by_email(email)
            if not user:
                raise ValueError("Invalid email or password")
            
            # Verify password
            if not verify_password(request.password, user.hashed_password):
                raise ValueError("Invalid email or password")
            
            # Update last login
            user.last_login = datetime.utcnow()
            await self.unit_of_work.users.update(user)
            await self.unit_of_work.commit()
            
            # Create tokens
            access_token = create_access_token(str(user.id.value))
            refresh_token = create_refresh_token(str(user.id.value))
            
            return UserResponse(
                user=UserDto(
                    id=user.id.value,
                    email=str(user.email),
                    first_name=user.first_name,
                    last_name=user.last_name,
                    status=user.status.value,
                    role=user.role.value,
                    email_verified=user.email_verified,
                    created_at=user.created_at,
                    last_login=user.last_login
                ),
                tokens=TokenDto(
                    access_token=access_token,
                    refresh_token=refresh_token
                )
            )
