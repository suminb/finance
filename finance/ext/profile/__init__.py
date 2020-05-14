"""
Extracts company profiles
"""
from finance.ext.profile.naver_finance import fetch_naver_profile


def fetch_profile(provider: str, symbol: str):
    """Fetches a company profile.

    Usage:

        >>> profile = fetch_profile("naver", "063170")
        >>> profile.name
        서울옥션
        >>> profile.current_price
        4300
        >>> profile.outstanding_shares
        16917500
        >>> profile.eps
        -395
        >>> profile.bps
        4344
    """
    if provider == "naver":
        return fetch_naver_profile(symbol)
    else:
        raise ValueError(f"Invalid profile provider: {provider}")


def is_valid_provider(provider: str):
    return provider in ["naver"]
