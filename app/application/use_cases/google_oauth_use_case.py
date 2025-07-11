"""Google OAuth authentication use case"""

from datetime import datetime
from typing import Optional
from google.oauth2 import id_token
from google.auth.transport import requests
import httpx

from ...domain.entities.user import User
from ...domain.value_objects.email import Email
from ...domain.value_objects.entity_ids import UserId
from ...domain.repositories.unit_of_work import IUnitOfWork
from ...domain.enums import UserStatus, UserRole
from ...application.dtos.user_dtos import UserResponse, UserDto, TokenDto
from ...core.security import create_access_token, create_refresh_token
from ...core.config import settings


class GoogleOAuthUseCase:
    
    def __init__(self, unit_of_work: IUnitOfWork):
        self.unit_of_work = unit_of_work
    
    async def execute(self, google_token: str) -> UserResponse:
        """Authenticate user with Google OAuth token"""
        try:
            # Check if Google OAuth is configured
            if not settings.GOOGLE_CLIENT_ID:
                raise ValueError("Google OAuth is not configured on the server")
            
            # Verify Google token
            idinfo = id_token.verify_oauth2_token(
                google_token, 
                requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )
            
            # Extract user info from Google token
            google_user_id = idinfo['sub']
            email = idinfo['email']
            email_verified = idinfo.get('email_verified', False)
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            
            async with self.unit_of_work:
                email_vo = Email(email)
                
                # Check if user exists
                existing_user = await self.unit_of_work.users.get_by_email(email_vo)
                
                if existing_user:
                    # Update existing user's Google info and verify email if not already verified
                    if not existing_user.email_verified and email_verified:
                        existing_user.verify_email()
                        await self.unit_of_work.users.update(existing_user)
                    
                    # Update last login
                    existing_user.last_login = datetime.utcnow()
                    await self.unit_of_work.users.update(existing_user)
                    await self.unit_of_work.commit()
                    
                    user = existing_user
                else:
                    # Create new user from Google info
                    user = User(
                        id=UserId(0),  # Repository will assign real ID
                        email=email_vo,
                        hashed_password="google_oauth",  # Placeholder for OAuth users
                        first_name=first_name,
                        last_name=last_name,
                        status=UserStatus.ACTIVE,  # Google users are active immediately
                        role=UserRole.USER,
                        email_verified=email_verified,  # Use Google's email verification status
                        email_verification_token=None,  # Not needed for Google users
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        last_login=datetime.utcnow()
                    )
                    
                    # Save new user
                    user = await self.unit_of_work.users.add(user)
                    await self.unit_of_work.commit()
                
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
                
        except ValueError as e:
            raise ValueError(f"Google authentication failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Google authentication error: {str(e)}") 