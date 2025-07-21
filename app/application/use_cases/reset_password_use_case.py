"""Reset password use case"""

from datetime import datetime
from ...core.security import get_password_hash

from ..dtos.user_dtos import ForgotPasswordResponse
from ...domain.repositories.unit_of_work import IUnitOfWork
from pydantic import BaseModel


class ResetPasswordDto(BaseModel):
    """DTO for reset password request"""
    token: str
    new_password: str


class ResetPasswordUseCase:
    """Use case for resetting password with token"""
    
    def __init__(self, unit_of_work: IUnitOfWork):
        self.unit_of_work = unit_of_work
    
    async def execute(self, request: ResetPasswordDto) -> ForgotPasswordResponse:
        """Execute reset password use case"""
        async with self.unit_of_work:
            user_repo = self.unit_of_work.users
            
            # Find user by reset token
            # Since we don't have a get_by_reset_token method, we'll need to iterate
            # In a real implementation, you'd add this method to the repository
            
            # For now, let's implement a basic version
            # TODO: Add proper repository method for finding by reset token
            
            try:
                # Use the existing get_by_reset_token method from repository
                user = await user_repo.get_by_reset_token(request.token)
                
                if not user:
                    return ForgotPasswordResponse(
                        message="Invalid or expired reset token.",
                        success=False
                    )
                
                # Additional validation (get_by_reset_token already checks expiration and used status)
                if (not user.password_reset_token or 
                    user.password_reset_token != request.token or
                    user.password_reset_used):
                    return ForgotPasswordResponse(
                        message="Invalid or expired reset token.",
                        success=False
                    )
                
                # Update password and mark token as used
                user.hashed_password = get_password_hash(request.new_password)
                user.password_reset_token = None
                user.password_reset_expires_at = None
                user.password_reset_used = True  # Mark as used
                user.updated_at = datetime.utcnow()
                
                # Save changes
                await user_repo.update(user)
                await self.unit_of_work.commit()
                
                return ForgotPasswordResponse(
                    message="Password has been successfully reset.",
                    success=True
                )
                
            except Exception as e:
                print(f"Error resetting password: {e}")
                return ForgotPasswordResponse(
                    message="An error occurred while resetting your password.",
                    success=False
                ) 