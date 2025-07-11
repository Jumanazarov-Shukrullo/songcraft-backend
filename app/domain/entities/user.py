"""User entity with business logic"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List
import uuid

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
    
    # Password reset fields for production use
    password_reset_token: Optional[str] = None
    password_reset_expires_at: Optional[datetime] = None
    password_reset_used: bool = False
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Domain events
    _events: List = field(default_factory=list, init=False)
    
    @classmethod
    def create(
        cls,
        email: Email,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> 'User':
        """Factory method to create a new user with proper defaults"""
        return cls(
            id=UserId.generate(),  # Generate UUID for new user
            email=email,
            hashed_password=password,
            first_name=first_name,
            last_name=last_name,
            status=UserStatus.PENDING_VERIFICATION,
            role=UserRole.USER,
            email_verified=False,
            email_verification_token=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
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
    
    def generate_password_reset_token(self, expires_in_hours: int = 1) -> str:
        """Business logic: generate password reset token"""
        self.password_reset_token = str(uuid.uuid4())
        self.password_reset_expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        self.password_reset_used = False
        self.updated_at = datetime.utcnow()
        
        return self.password_reset_token
    
    def is_password_reset_token_valid(self, token: str) -> bool:
        """Business logic: validate password reset token"""
        if not self.password_reset_token:
            return False
        
        if self.password_reset_token != token:
            return False
        
        if self.password_reset_used:
            return False
        
        if not self.password_reset_expires_at:
            return False
        
        if datetime.utcnow() > self.password_reset_expires_at:
            return False
        
        return True
    
    def mark_password_reset_token_used(self) -> None:
        """Business logic: mark password reset token as used"""
        self.password_reset_used = True
        self.updated_at = datetime.utcnow()
    
    def clear_password_reset_token(self) -> None:
        """Business logic: clear password reset token"""
        self.password_reset_token = None
        self.password_reset_expires_at = None
        self.password_reset_used = False
        self.updated_at = datetime.utcnow()
    
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