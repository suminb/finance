from datetime import datetime
import json

from finance.ext.rapidapi.yahoo.models import Financials, Profile, HistoricalData


def load_test_data(filename):
    with open(f"tests/ext/rapidapi/yahoo/{filename}") as fin:
        return json.loads(fin.read())


def test_financials():
    financials = Financials(load_test_data("financials-NET.json"))
    assert financials.market_cap == 25324675072


def test_profile():
    profile = Profile(load_test_data("profile-TSLA.json"))
    assert profile.sector == "Consumer Cyclical"


def test_historical_data():
    historical_data = HistoricalData(load_test_data("historical_data-MSFT.json"))
    assert historical_data.first_trade_date == datetime(1986, 3, 13, 14, 30)
