from datetime import datetime
from finance.ext.rapidapi.yahoo import cache_exists, load_cache
import json
import os

from finance.ext.rapidapi.yahoo.models import Financials, Profile, HistoricalData


BASE_PATH = os.path.abspath(os.path.dirname(__file__))
CACHE_DIR = BASE_PATH + "/rapidapi/yahoo"


def test_cache():
    assert cache_exists("profile", "NET", "US", CACHE_DIR)


def test_financials():
    financials = Financials(load_cache("financials", "NET", "US", CACHE_DIR))
    assert financials.market_cap == 25324675072

    assert financials.most_recent_yearly_earnings["date"] == 2019
    assert financials.most_recent_yearly_earnings["revenue"] == 287022000
    assert financials.most_recent_yearly_earnings["earnings"] == -105828000

    assert financials.most_recent_quarterly_earnings["date"] == "3Q2020"
    assert financials.most_recent_quarterly_earnings["revenue"] == 114162000
    assert financials.most_recent_quarterly_earnings["earnings"] == -26468000


def test_profile():
    profile = Profile(load_cache("profile", "TSLA", "US", CACHE_DIR))
    assert profile.sector == "Consumer Cyclical"


def test_historical_data():
    historical_data = HistoricalData(load_cache("historical_data", "MSFT", "US", CACHE_DIR))
    assert historical_data.first_trade_date == datetime(1986, 3, 13, 14, 30)
    assert historical_data.most_recent_price == 213.26
