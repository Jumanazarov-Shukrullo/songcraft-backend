"""Forgot password use case"""

import uuid
from datetime import datetime, timedelta

from ..dtos.user_dtos import ForgotPasswordDto, ForgotPasswordResponse
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...infrastructure.external_services.email_service import EmailService


class ForgotPasswordUseCase:
    """Use case for handling forgot password requests"""
    
    def __init__(self, unit_of_work: IUnitOfWork, email_service: EmailService):
        self.unit_of_work = unit_of_work
        self.email_service = email_service
    
    async def execute(self, request: ForgotPasswordDto) -> ForgotPasswordResponse:
        """Execute forgot password use case - Production ready with database storage"""
        async with self.unit_of_work:
            # Check if user exists
            user_repo = self.unit_of_work.users
            user = await user_repo.get_by_email(request.email)
            
            if not user:
                # For security reasons, don't reveal if email exists or not
                # Return success message regardless
                return ForgotPasswordResponse(
                    message="If an account with that email exists, a password reset link has been sent.",
                    success=True
                )
            
            # Generate password reset token - Production ready approach
            reset_token = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
            
            # Store reset token in database using proper domain logic
            user.password_reset_token = reset_token
            user.password_reset_expires_at = expires_at
            user.password_reset_used = False
            user.updated_at = datetime.utcnow()
            
            # Save user with reset token to database
            await user_repo.update(user)
            await self.unit_of_work.commit()
            
            try:
                # Send password reset email
                await self.email_service.send_password_reset_email(
                    to_email=user.email,
                    reset_token=reset_token
                )
                
                return ForgotPasswordResponse(
                    message="If an account with that email exists, a password reset link has been sent.",
                    success=True
                )
                
            except Exception as e:
                # Log the error but don't expose internal details
                print(f"Error sending password reset email: {e}")
                # Even if email fails, token is stored in DB, so return success
                return ForgotPasswordResponse(
                    message="If an account with that email exists, a password reset link has been sent.",
                    success=True
                ) 