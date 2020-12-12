from datetime import datetime
import json
import os

import requests

API_HOST = "apidojo-yahoo-finance-v1.p.rapidapi.com"

headers = {
    "x-rapidapi-key": os.environ.get("SBF_RAPIDAPI_KEY"),
    "x-rapidapi-host": API_HOST,
}


def get_financials(symbol: str, region="US"):
    url = f"https://{API_HOST}/stock/v2/get-financials"
    params = {"symbol": symbol, "region": region}
    resp = requests.get(url, headers=headers, params=params)

    return json.loads(resp.text)


def get_market_cap(financials: dict):
    return financials["price"]["marketCap"]["raw"]


def get_most_recent_yearly_earnings(financials: dict):
    earnings = financials["earnings"]["financialsChart"]["yearly"]

    # As a matter of fact, `date` is actually year
    recent_year = max(x["date"] for x in earnings)

    # It seems like the annual earnings are in chronological order,
    # but there is no such guarantee and thus we added an assertion statement here.
    recent_earnings = earnings[-1]
    assert recent_earnings["date"] == recent_year

    return recent_earnings


def get_most_recent_quarterly_earnings(financials: dict):
    earnings = financials["earnings"]["financialsChart"]["quarterly"]

    # 'quarter' looks like "1Q2020", "4Q2019", etc.
    recent_quarter = max(x["date"].split("Q")[::-1] for x in earnings)
    recent_quarter = "Q".join(recent_quarter[::-1])

    # It seems like the quarterly earnings are in chronological order,
    # but there is no such guarantee and thus we added an assertion statement here.
    recent_earnings = earnings[-1]
    assert recent_earnings["date"] == recent_quarter

    return recent_earnings


def get_historical_data(symbol: str, region="US"):
    """See https://rapidapi.com/apidojo/api/yahoo-finance1?endpoint=apiendpoint_2c81ebb5-60ab-41e4-8cd2-2056b26e93c2 for more details.
    """
    url = f"https://{API_HOST}/stock/v2/get-historical-data"
    params = {"symbol": symbol, "region": region}
    resp = requests.get(url, headers=headers, params=params)

    return json.loads(resp.text)


def get_first_trade_date(historical_data: dict):
    timestamp = historical_data["firstTradeDate"]
    return datetime.utcfromtimestamp(timestamp)


def get_profile(symbol: str, region="US"):
    """See https://rapidapi.com/apidojo/api/yahoo-finance1?endpoint=apiendpoint_f787ce0f-17f7-40cf-a731-f141fd61cc08 for more details.
    """
    url = f"https://{API_HOST}/stock/v2/get-profile"
    params = {"symbol": symbol, "region": region}
    resp = requests.get(url, headers=headers, params=params)

    return json.loads(resp.text)


def get_sector(profile: dict):
    return profile["assetProfile"]["sector"]