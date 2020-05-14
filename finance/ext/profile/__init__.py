"""
Extracts company profiles
"""
from finance.ext.profile.naver_finance import fetch_naver_profile


def fetch_profile(provider: str, symbol: str):
    if provider == "naver":
        return fetch_naver_profile(symbol)
    else:
        raise ValueError(f"Invalid profile provider: {provider}")


def is_valid_provider(provider: str):
    return provider in ["naver"]
