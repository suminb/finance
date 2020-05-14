import os

import pytest

from finance.ext.profile import fetch_profile
from finance.ext.profile.base import BaseProfile
from finance.ext.profile.naver_finance import NaverProfile

BASE_PATH = os.path.abspath(os.path.dirname(__file__))


def test_base_profile():
    with pytest.raises(NotImplementedError):
        BaseProfile()


def test_invalid_provider():
    with pytest.raises(ValueError):
        fetch_profile("unknown", "063170")


def test_naver_profile():
    path = os.path.join(BASE_PATH, "063170.html")
    with open(path) as fin:
        raw_sample = fin.read()

    profile = NaverProfile("063170")
    profile.parse(raw_sample)

    assert profile.name == "서울옥션"
    assert profile.current_price == 4470
    assert profile.outstanding_shares == 16917500


def test_fetch_naver_profile():
    profile = fetch_profile("naver", "063170")

    assert profile.name == "서울옥션"
    # NOTE: Testing with live data. Some information is unknown at the time of
    # writing code.
    assert profile.current_price > 0
    assert profile.outstanding_shares > 0
