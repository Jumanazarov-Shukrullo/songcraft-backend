"""User repository interface"""

from abc import ABC, abstractmethod
from typing import Optional, List

from ..entities.user import User
from ..value_objects.email import Email
from ..value_objects.entity_ids import UserId


class IUserRepository(ABC):
    
    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> Optional[User]:
        pass
    
    @abstractmethod
    async def get_by_email(self, email: Email) -> Optional[User]:
        pass
    
    @abstractmethod
    async def get_by_reset_token(self, token: str) -> Optional[User]:
        """Get user by password reset token"""
        pass
    
    @abstractmethod
    async def get_by_verification_token(self, token: str) -> Optional[User]:
        """Get user by email verification token"""
        pass
    
    @abstractmethod
    async def add(self, user: User) -> User:
        pass
    
    @abstractmethod
    async def update(self, user: User) -> User:
        pass
    
    @abstractmethod
    async def delete(self, user_id: UserId) -> None:
        pass
    
    @abstractmethod
    async def exists_by_email(self, email: Email) -> bool:
        pass
    
    @abstractmethod
    async def count(self) -> int:
        pass
    
    @abstractmethod
    async def get_paginated(self, page: int, limit: int) -> List[User]:
        pass
