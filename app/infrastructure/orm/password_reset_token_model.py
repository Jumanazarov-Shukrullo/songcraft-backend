"""Password reset token ORM model"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4

from ...db.models import Base


class PasswordResetTokenORM(Base):
    """Password reset token ORM model"""
    
    __tablename__ = "password_reset_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship (optional - depends on if UserORM wants back_populates)
    # user = relationship("UserORM", back_populates="password_reset_tokens")
    
    def __repr__(self):
        return f"<PasswordResetTokenORM(id={self.id}, user_id={self.user_id}, token={self.token[:8]}..., expires_at={self.expires_at})>" 