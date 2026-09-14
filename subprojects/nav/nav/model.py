"""Shared value types for nav."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

# This constant is also defined in finance.ext.models; duplication is intentional.
# nav.model must remain a pure value module free of heavy dependencies (like pandas),
# while finance.ext.models imports pandas.
CASH_PREFIX = "_"


@dataclass(frozen=True)
class Transaction:
    """One normalized line of a 거래내역조회 (0650) export."""

    date: datetime
    seq: int
    category: str
    name: str
    ticker: str
    currency: str
    amount: Decimal
    unit_price: Decimal
    quantity: Decimal
    fees: Decimal
    tax: Decimal
    raw: str


@dataclass(frozen=True)
class Leg:
    """A signed change to one inventory entry."""

    ticker: str
    quantity: Decimal


def cash_ticker(currency: str) -> str:
    """Pseudo-ticker under which cash of a currency is held.

    Extends the `_USD` convention already used by finance.ext.models.
    """
    return CASH_PREFIX + currency
