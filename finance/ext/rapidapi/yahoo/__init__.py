import json
import os

import requests

from finance.ext.rapidapi.yahoo.models import Financials, HistoricalData, Profile

API_HOST = "apidojo-yahoo-finance-v1.p.rapidapi.com"

headers = {
    "x-rapidapi-key": os.environ.get("SBF_RAPIDAPI_KEY"),
    "x-rapidapi-host": API_HOST,
}


def fetch_financials(symbol: str, region="US"):
    """See https://rapidapi.com/apidojo/api/yahoo-finance1?endpoint=apiendpoint_2e0b16d4-a66b-469e-bc18-b60cec60661b for more details."""
    url = f"https://{API_HOST}/stock/v2/get-financials"
    params = {"symbol": symbol, "region": region}
    resp = requests.get(url, headers=headers, params=params)

    return json.loads(resp.text)


def get_financials(symbol: str, region="US", fetch=fetch_financials):
    return Financials(fetch(symbol, region))


def fetch_historical_data(symbol: str, region="US"):
    """See https://rapidapi.com/apidojo/api/yahoo-finance1?endpoint=apiendpoint_2c81ebb5-60ab-41e4-8cd2-2056b26e93c2 for more details."""
    url = f"https://{API_HOST}/stock/v2/get-historical-data"
    params = {"symbol": symbol, "region": region}
    resp = requests.get(url, headers=headers, params=params)

    return json.loads(resp.text)


def get_historical_data(symbol: str, region="US", fetch=fetch_historical_data):
    return HistoricalData(fetch_historical_data(symbol, region))


def fetch_profile(symbol: str, region="US"):
    """See https://rapidapi.com/apidojo/api/yahoo-finance1?endpoint=apiendpoint_f787ce0f-17f7-40cf-a731-f141fd61cc08 for more details."""
    url = f"https://{API_HOST}/stock/v2/get-profile"
    params = {"symbol": symbol, "region": region}
    resp = requests.get(url, headers=headers, params=params)

    return json.loads(resp.text)


def get_profile(symbol: str, region="US", fetch=fetch_profile):
    return Profile(fetch(symbol, region))
