"""Order ORM Model"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

from ...db.models import Base
from ...domain.enums import OrderStatus, ProductType


class OrderModel(Base):
    __tablename__ = 'orders'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    
    # Payment details (Lemon Squeezy + domain compatibility)
    lemon_squeezy_order_id = Column(String, unique=True, nullable=True)
    lemon_squeezy_payment_id = Column(String, unique=True, nullable=True)
    payment_provider_id = Column(String, nullable=True, index=True)  # For domain model compatibility
    
    # Order details
    product_type = Column(SQLEnum(ProductType), nullable=False)
    amount = Column(Integer, nullable=False)  # Amount in cents
    currency = Column(String, default='USD', nullable=False)
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship('UserModel', back_populates='orders')
    song = relationship('SongModel', back_populates='order', uselist=False)


class AuditLogModel(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    details = Column(String, nullable=True)  # JSON string
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship('UserModel', back_populates='audit_logs')


class EmailVerificationModel(Base):
    __tablename__ = 'email_verifications'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class TaskResultModel(Base):
    __tablename__ = 'task_results'
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, nullable=False)
    task_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    result = Column(String, nullable=True)  # JSON string
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now()) 