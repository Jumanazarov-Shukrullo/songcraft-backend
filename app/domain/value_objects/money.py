"""Money value object with currency"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if not self.currency:
            raise ValueError("Currency required")
    
    def to_cents(self) -> int:
        return int(self.amount * 100)
    
    @classmethod
    def from_cents(cls, cents: int, currency: str = "USD") -> "Money":
        return cls(amount=Decimal(cents) / 100, currency=currency)
    
    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}" 