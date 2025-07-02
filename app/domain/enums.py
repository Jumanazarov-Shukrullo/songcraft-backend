"""
Domain Enums - Business domain enumerations
"""

from enum import Enum


class UserStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProductType(str, Enum):
    AUDIO_ONLY = "audio_only"
    AUDIO_VIDEO = "audio_video"


class MusicStyle(str, Enum):
    RAP = "rap"
    POP = "pop"
    ELECTROPOP = "electropop"
    JAZZ = "jazz"
    FUNK = "funk"
    ACOUSTIC = "acoustic"


class GenerationStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class EmotionalTone(str, Enum):
    EMOTIONAL = "emotional"
    ROMANTIC = "romantic"
    PLAYFUL = "playful"
    IRONIC = "ironic" 