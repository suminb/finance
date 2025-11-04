"""Simple data models and enums without database dependencies."""


class Granularity:
    """Time granularity constants for asset value data."""

    sec = "1sec"
    min = "1min"
    three_min = "3min"
    five_min = "5min"
    fifteen_min = "15min"
    hour = "1hour"
    four_hour = "4hour"
    day = "1day"
    week = "1week"
    month = "1month"
    year = "1year"

    @classmethod
    def is_valid(cls, value):
        return value in (
            cls.sec,
            cls.min,
            cls.three_min,
            cls.five_min,
            cls.fifteen_min,
            cls.hour,
            cls.four_hour,
            cls.day,
            cls.week,
            cls.month,
            cls.year,
        )


class AssetType:
    """Asset type constants."""

    fiat_currency = "fiat_currency"
    crypto_currency = "crypto_currency"
    stock = "stock"
    bond = "bond"
    p2p_bond = "p2p_bond"
    security = "security"
    fund = "fund"
    commodity = "commodity"


class AccountType:
    """Account type constants."""

    checking = "checking"
    savings = "savings"
    investment = "investment"
    credit_card = "credit card"
    virtual = "virtual"


class FinancialGranularity:
    """Financial reporting granularity."""

    quarterly = "quarterly"
    annual = "annual"


class TransactionState:
    """Transaction state constants."""

    initiated = "initiated"
    closed = "closed"
    pending = "pending"
    invalid = "invalid"


class RecordType:
    """Record type constants."""

    deposit = "deposit"
    withdraw = "withdraw"
    balance_adjustment = "balance_adjustment"
