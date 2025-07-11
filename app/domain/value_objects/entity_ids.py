"""Entity ID value objects"""

from dataclasses import dataclass
from uuid import UUID, uuid4
from typing import Union


@dataclass(frozen=True)
class UserId:
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise ValueError("User ID must be a valid UUID")
    
    @classmethod
    def generate(cls) -> 'UserId':
        """Generate a new random UUID"""
        return cls(uuid4())
    
    @classmethod
    def from_str(cls, uuid_str: str) -> 'UserId':
        """Create UserId from string representation"""
        return cls(UUID(uuid_str))


@dataclass(frozen=True)
class OrderId:
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise ValueError("Order ID must be a valid UUID")
    
    @classmethod
    def generate(cls) -> 'OrderId':
        """Generate a new random UUID"""
        return cls(uuid4())
    
    @classmethod
    def from_str(cls, uuid_str: str) -> 'OrderId':
        """Create OrderId from string representation"""
        return cls(UUID(uuid_str))


@dataclass(frozen=True)
class SongId:
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            raise ValueError("Song ID must be a valid UUID")
    
    @classmethod
    def generate(cls) -> 'SongId':
        """Generate a new random UUID"""
        return cls(uuid4())
    
    @classmethod
    def from_str(cls, uuid_str: str) -> 'SongId':
        """Create SongId from string representation"""
        return cls(UUID(uuid_str))