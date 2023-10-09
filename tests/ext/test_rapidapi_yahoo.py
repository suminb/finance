from datetime import datetime
from finance.ext.rapidapi.yahoo import (
    cache_exists,
    get_financials,
    get_historical_data,
    get_profile,
)
import os

from finance.ext.rapidapi.yahoo.models import Financials, Profile, HistoricalData


BASE_PATH = os.path.abspath(os.path.dirname(__file__))
CACHE_DIR = BASE_PATH + "/rapidapi/yahoo"


def test_cache():
    assert cache_exists("profile", "NET", "US", CACHE_DIR, check_stale_data=False)


def test_financials():
    financials = get_financials("NET", cache_dir=CACHE_DIR)
    assert financials.market_cap == 25324675072

    assert financials.most_recent_yearly_earnings["date"] == 2019
    assert financials.most_recent_yearly_earnings["revenue"] == 287022000
    assert financials.most_recent_yearly_earnings["earnings"] == -105828000

    assert financials.most_recent_quarterly_earnings["date"] == "3Q2020"
    assert financials.most_recent_quarterly_earnings["revenue"] == 114162000
    assert financials.most_recent_quarterly_earnings["earnings"] == -26468000


def test_profile():
    profile = get_profile("TSLA", cache_dir=CACHE_DIR)
    assert profile.sector == "Consumer Cyclical"


def test_historical_data():
    historical_data = get_historical_data("MSFT", cache_dir=CACHE_DIR)
    assert historical_data.first_trade_date == datetime(1986, 3, 13, 14, 30)
    assert historical_data.most_recent_price == 213.26


def test_malformed_historical_data():
    """We have noticed historical data of PS contains malformed data. Some of
    the price information, such as close, open, low, high, close, adjclose,
    and volume, is None."""
    historical_data = get_historical_data("PS", cache_dir=CACHE_DIR)
    [x for x in historical_data.prices]
