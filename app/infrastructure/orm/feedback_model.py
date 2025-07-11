from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .user_model import Base

class FeedbackModel(Base):
    """User feedback model for storing user feedback and suggestions"""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Allow null for anonymous
    email = Column(String(255), nullable=True)  # For anonymous users
    name = Column(String(255), nullable=True)  # For anonymous users
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default="general")  # general, bug, feature, improvement
    status = Column(String(20), nullable=False, default="pending")  # pending, in_progress, resolved, dismissed
    admin_response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("UserModel", back_populates="feedback")

    def __repr__(self):
        return f"<Feedback(id={self.id}, user_id={self.user_id}, subject='{self.subject}', status='{self.status}')>" 