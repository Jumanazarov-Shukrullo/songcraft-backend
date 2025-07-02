"""Entity ID value objects"""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserId:
    value: int
    
    def __post_init__(self):
        if self.value <= 0:
            raise ValueError("User ID must be positive")


@dataclass(frozen=True)
class OrderId:
    value: int
    
    def __post_init__(self):
        if self.value <= 0:
            raise ValueError("Order ID must be positive")


@dataclass(frozen=True)
class SongId:
    value: int
    
    def __post_init__(self):
        if self.value <= 0:
            raise ValueError("Song ID must be positive") 