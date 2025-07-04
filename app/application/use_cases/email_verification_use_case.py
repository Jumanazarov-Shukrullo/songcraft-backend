"""Email verification use case"""

from ...domain.repositories.unit_of_work import IUnitOfWork
from ...application.dtos.user_dtos import VerifyEmailDto
from ...domain.enums import UserStatus


class EmailVerificationUseCase:
    
    def __init__(self, unit_of_work: IUnitOfWork):
        self.unit_of_work = unit_of_work
    
    async def execute(self, request: VerifyEmailDto) -> bool:
        """Verify user email with token"""
        print(f"EmailVerificationUseCase: Looking up user with token: {request.token}")
        
        async with self.unit_of_work:
            # Find user by verification token
            user = await self.unit_of_work.users.get_by_verification_token(request.token)
            
            if not user:
                print(f"EmailVerificationUseCase: No user found with token: {request.token}")
                raise ValueError("Invalid verification token")
            
            print(f"EmailVerificationUseCase: Found user {user.email.value}, verified: {user.email_verified}")
            
            if user.email_verified:
                print(f"EmailVerificationUseCase: Email already verified for user: {user.email.value}")
                raise ValueError("Email already verified")
            
            # Verify email using domain business logic
            user.verify_email()
            
            print(f"EmailVerificationUseCase: Verifying email for user: {user.email.value}")
            
            # Save changes
            await self.unit_of_work.users.update(user)
            await self.unit_of_work.commit()
            
            print(f"EmailVerificationUseCase: Email verification completed for user: {user.email.value}")
            return True