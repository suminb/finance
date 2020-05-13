"""
Extracts company profiles
"""
from finance.ext.profile.naver_finance import *




def fetch_profile(provider: str, symbol: str):
    assert is_valid_provider(provider), f"Invalid profile provider: {provider}"
    if provider == "naver":
        return fetch_naver_profile(symbol)


def is_valid_provider(provider: str):
    return provider in ["naver"]