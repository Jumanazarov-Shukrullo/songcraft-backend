"""User entity with business logic"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from ..value_objects.email import Email
from ..value_objects.entity_ids import UserId
from ..enums import UserStatus, UserRole
from ..events.user_events import UserEmailVerified, UserSuspended


@dataclass
class User:
    id: UserId
    email: Email
    hashed_password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    role: UserRole = UserRole.USER
    email_verified: bool = False
    email_verification_token: Optional[str] = None
    password_reset_token: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Domain events
    _events: List = field(default_factory=list, init=False)
    
    def verify_email(self) -> None:
        """Business logic: verify user email"""
        if self.email_verified:
            raise ValueError("Email already verified")
        
        self.email_verified = True
        self.status = UserStatus.ACTIVE
        self.email_verification_token = None
        self.updated_at = datetime.utcnow()
        
        # Emit domain event
        self._events.append(UserEmailVerified(
            user_id=self.id,
            email=self.email,
            verified_at=datetime.utcnow()
        ))
    
    def suspend(self, reason: str) -> None:
        """Business logic: suspend user"""
        self.status = UserStatus.SUSPENDED
        self.updated_at = datetime.utcnow()
        
        self._events.append(UserSuspended(
            user_id=self.id,
            reason=reason
        ))
    
    def promote_to_admin(self) -> None:
        """Business logic: promote to admin"""
        if self.status != UserStatus.ACTIVE:
            raise ValueError("Can only promote active users")
        
        self.role = UserRole.ADMIN
        self.updated_at = datetime.utcnow()
    
    def record_login(self) -> None:
        """Record user login"""
        self.last_login = datetime.utcnow()
    
    @property
    def full_name(self) -> str:
        """Get full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or str(self.email)
    
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
    
    def get_events(self) -> List:
        """Get and clear domain events"""
        events = self._events.copy()
        self._events.clear()
        return events 