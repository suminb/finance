from datetime import datetime
import json

from finance.ext.rapidapi.yahoo.models import Financials, Profile, HistoricalData


def load_test_data(filename):
    with open(f"tests/ext/rapidapi/yahoo/{filename}") as fin:
        return json.loads(fin.read())


def test_financials():
    financials = Financials(load_test_data("financials-NET.json"))
    assert financials.market_cap == 25324675072

    assert financials.most_recent_yearly_earnings["date"] == 2019
    assert financials.most_recent_yearly_earnings["revenue"] == 287022000
    assert financials.most_recent_yearly_earnings["earnings"] == -105828000

    assert financials.most_recent_quarterly_earnings["date"] == "3Q2020"
    assert financials.most_recent_quarterly_earnings["revenue"] == 114162000
    assert financials.most_recent_quarterly_earnings["earnings"] == -26468000


def test_profile():
    profile = Profile(load_test_data("profile-TSLA.json"))
    assert profile.sector == "Consumer Cyclical"


def test_historical_data():
    historical_data = HistoricalData(load_test_data("historical_data-MSFT.json"))
    assert historical_data.first_trade_date == datetime(1986, 3, 13, 14, 30)
    assert historical_data.most_recent_price == 213.26
