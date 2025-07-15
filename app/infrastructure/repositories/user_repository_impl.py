"""User repository implementation using existing models"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime

from ...domain.repositories.user_repository import IUserRepository
from ...domain.entities.user import User
from ...domain.value_objects.email import Email
from ...domain.value_objects.entity_ids import UserId
from ...domain.enums import UserStatus, UserRole
from ..orm.user_model import UserModel  # Fixed import for DDD architecture


class UserRepositoryImpl(IUserRepository):
    """Repository implementation for User aggregate"""

    def __init__(self, session: Session):
        self.session = session

    def save(self, user: User) -> User:
        """Save or update user"""
        existing = self.session.query(UserModel).filter(UserModel.id == user.id.value).first()
        
        if existing:
            # Update existing user
            self._update_model_from_entity(existing, user)
        else:
            # Create new user
            model = self._create_model_from_entity(user)
            self.session.add(model)
        
        self.session.flush()
        return user

    async def get_by_id(self, user_id: UserId) -> Optional[User]:
        """Get user by ID"""
        model = self.session.query(UserModel).filter(UserModel.id == user_id.value).first()
        return self._map_to_entity(model) if model else None

    async def get_by_email(self, email: Email) -> Optional[User]:
        """Get user by email"""
        model = self.session.query(UserModel).filter(UserModel.email == str(email)).first()
        return self._map_to_entity(model) if model else None

    async def get_by_reset_token(self, token: str) -> Optional[User]:
        """Get user by password reset token - Production ready method"""
        model = self.session.query(UserModel).filter(
            UserModel.password_reset_token == token,
            UserModel.password_reset_used == False,
            UserModel.password_reset_expires_at > datetime.utcnow()
        ).first()
        return self._map_to_entity(model) if model else None

    async def get_by_verification_token(self, token: str) -> Optional[User]:
        """Get user by email verification token"""
        model = self.session.query(UserModel).filter(
            UserModel.email_verification_token == token
        ).first()
        return self._map_to_entity(model) if model else None

    async def exists_by_email(self, email: Email) -> bool:
        """Check if user exists by email"""
        return self.session.query(UserModel).filter(UserModel.email == str(email)).first() is not None

    async def add(self, user: User) -> User:
        """Add a new user"""
        # Create model without ID for new users
        model_data = {
            'email': str(user.email),
            'hashed_password': user.hashed_password,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'status': user.status.value,
            'role': user.role.value,
            'email_verified': user.email_verified,
            'email_verification_token': user.email_verification_token,
            'password_reset_token': user.password_reset_token,
            'password_reset_expires_at': user.password_reset_expires_at,
            'password_reset_used': user.password_reset_used,
            'created_at': user.created_at,
            'updated_at': user.updated_at,
            'last_login': user.last_login,
            'song_credits': user.song_credits
        }
        
        model = UserModel(**model_data)
        self.session.add(model)
        self.session.flush()
        
        # Create a new User entity with the generated ID
        user_with_id = User(
            id=UserId(model.id),
            email=user.email,
            hashed_password=user.hashed_password,
            first_name=user.first_name,
            last_name=user.last_name,
            status=user.status,
            role=user.role,
            email_verified=user.email_verified,
            email_verification_token=user.email_verification_token,
            password_reset_token=user.password_reset_token,
            password_reset_expires_at=user.password_reset_expires_at,
            password_reset_used=user.password_reset_used,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
            song_credits=user.song_credits
        )
        
        return user_with_id

    async def update(self, user: User) -> User:
        """Update an existing user"""
        existing = self.session.query(UserModel).filter(UserModel.id == user.id.value).first()
        if existing:
            self._update_model_from_entity(existing, user)
            self.session.flush()
        return user

    async def count(self) -> int:
        """Count total users"""
        return self.session.query(UserModel).count()

    async def get_paginated(self, page: int, limit: int) -> List[User]:
        """Get paginated users"""
        offset = (page - 1) * limit
        models = self.session.query(UserModel).offset(offset).limit(limit).all()
        return [self._map_to_entity(model) for model in models]

    async def delete(self, user_id: UserId) -> None:
        """Delete user"""
        user = self.session.query(UserModel).filter(UserModel.id == user_id.value).first()
        if user:
            self.session.delete(user)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users (legacy method)"""
        models = self.session.query(UserModel).offset(skip).limit(limit).all()
        return [self._map_to_entity(model) for model in models]

    def count_total_users(self) -> int:
        """Count total users (legacy method)"""
        return self.session.query(UserModel).count()

    def _create_model_from_entity(self, user: User) -> UserModel:
        """Create ORM model from domain entity"""
        model_data = {
            'email': str(user.email),
            'hashed_password': user.hashed_password,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'status': user.status.value,
            'role': user.role.value,
            'email_verified': user.email_verified,
            'email_verification_token': user.email_verification_token,
            'password_reset_token': user.password_reset_token,
            'password_reset_expires_at': user.password_reset_expires_at,
            'password_reset_used': user.password_reset_used,
            'created_at': user.created_at,
            'updated_at': user.updated_at,
            'last_login': user.last_login,
            'song_credits': user.song_credits
        }
        
        # Only set ID if it exists (for updates)
        if user.id and user.id.value:
            model_data['id'] = user.id.value
            
        return UserModel(**model_data)

    def _update_model_from_entity(self, model: UserModel, user: User) -> None:
        """Update ORM model from domain entity"""
        model.email = str(user.email)
        model.hashed_password = user.hashed_password
        model.first_name = user.first_name
        model.last_name = user.last_name
        model.status = user.status.value
        model.role = user.role.value
        model.email_verified = user.email_verified
        model.email_verification_token = user.email_verification_token
        model.password_reset_token = user.password_reset_token
        model.password_reset_expires_at = user.password_reset_expires_at
        model.password_reset_used = user.password_reset_used
        model.updated_at = user.updated_at
        model.last_login = user.last_login
        model.song_credits = user.song_credits

    def _map_to_entity(self, model: UserModel) -> User:
        """Map ORM model to domain entity"""
        return User(
            id=UserId(model.id),
            email=Email(model.email),
            hashed_password=model.hashed_password,
            first_name=model.first_name,
            last_name=model.last_name,
            status=UserStatus(model.status),
            role=UserRole(model.role),
            email_verified=model.email_verified,
            email_verification_token=model.email_verification_token,
            password_reset_token=model.password_reset_token,
            password_reset_expires_at=getattr(model, 'password_reset_expires_at', None),
            password_reset_used=getattr(model, 'password_reset_used', False),
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_login=model.last_login,
            song_credits=getattr(model, 'song_credits', 0)
        ) 