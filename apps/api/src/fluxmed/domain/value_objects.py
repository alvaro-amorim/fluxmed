from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Money:
    """BRL monetary value with deterministic cent precision."""

    amount: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("Money amount must be a Decimal")
        if not self.amount.is_finite():
            raise ValueError("Money amount must be finite")
        object.__setattr__(self, "amount", self.amount.quantize(_CENT, rounding=ROUND_HALF_UP))

    @classmethod
    def zero(cls) -> Money:
        return cls(Decimal("0"))

    def __add__(self, other: object) -> Money:
        if not isinstance(other, Money):
            raise TypeError("Money can only be added to Money")
        return Money(self.amount + other.amount)

    def __sub__(self, other: object) -> Money:
        if not isinstance(other, Money):
            raise TypeError("Money can only be subtracted from Money")
        return Money(self.amount - other.amount)

    def multiply(self, factor: Decimal) -> Money:
        if not isinstance(factor, Decimal):
            raise TypeError("Money factor must be a Decimal")
        if not factor.is_finite():
            raise ValueError("Money factor must be finite")
        return Money(self.amount * factor)
