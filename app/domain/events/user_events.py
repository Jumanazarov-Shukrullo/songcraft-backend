"""User domain events"""

from dataclasses import dataclass
from datetime import datetime

from ..value_objects.email import Email
from ..value_objects.entity_ids import UserId


@dataclass(frozen=True)
class UserEmailVerified:
    user_id: UserId
    email: Email
    verified_at: datetime


@dataclass(frozen=True)
class UserSuspended:
    user_id: UserId
    reason: str


@dataclass(frozen=True)
class UserPromotedToAdmin:
    user_id: UserId
    promoted_at: datetime 