"""Register user use case"""

from ...domain.entities.user import User
from ...domain.value_objects.email import Email
from ...domain.value_objects.entity_ids import UserId
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.external_services.email_service import EmailService
from ...application.dtos.user_dtos import CreateUserDto, UserResponse, UserDto, TokenDto
from ...core.security import get_password_hash, create_access_token, create_refresh_token


class RegisterUserUseCase:
    
    def __init__(self, unit_of_work: IUnitOfWork, email_service: EmailService):
        self.unit_of_work = unit_of_work
        self.email_service = email_service
    
    async def execute(self, request: CreateUserDto) -> UserResponse:
        async with self.unit_of_work:
            email = Email(request.email)
            
            # Check if user exists
            if self.unit_of_work.users.exists_by_email(email):
                raise ValueError("User with this email already exists")
            
            # Create user entity
            user = User.create(
                email=email,
                password=get_password_hash(request.password),
                first_name=request.first_name,
                last_name=request.last_name
            )
            
            # Save user
            user = await self.unit_of_work.users.add(user)
            await self.unit_of_work.commit()
            
            # Send verification email
            await self.email_service.send_verification_email(
                to_email=user.email.value,
                verification_token=user.email_verification_token
            )
            
            # Create tokens
            access_token = create_access_token(str(user.id.value))
            refresh_token = create_refresh_token(str(user.id.value))
            
            return UserResponse(
                user=UserDto(
                    id=user.id.value,
                    email=user.email.value,
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
