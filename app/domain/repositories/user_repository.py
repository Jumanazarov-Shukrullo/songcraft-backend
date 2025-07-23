"""User repository interface"""

from abc import ABC, abstractmethod
from typing import Optional, List

from ..entities.user import User
from ..value_objects.email import Email
from ..value_objects.entity_ids import UserId


class IUserRepository(ABC):
    
    @abstractmethod
    def get_by_id(self, user_id: UserId) -> Optional[User]:
        pass
    
    @abstractmethod
    def get_by_email(self, email: Email) -> Optional[User]:
        pass
    
    @abstractmethod
    def get_by_reset_token(self, token: str) -> Optional[User]:
        """Get user by password reset token"""
        pass
    
    @abstractmethod
    def get_by_verification_token(self, token: str) -> Optional[User]:
        """Get user by email verification token"""
        pass
    
    @abstractmethod
    def add(self, user: User) -> User:
        pass
    
    @abstractmethod
    def update(self, user: User) -> User:
        pass
    
    @abstractmethod
    def delete(self, user_id: UserId) -> None:
        pass
    
    @abstractmethod
    def exists_by_email(self, email: Email) -> bool:
        pass
    
    @abstractmethod
    def count(self) -> int:
        pass
    
    @abstractmethod
    def get_paginated(self, page: int, limit: int) -> List[User]:
        pass
