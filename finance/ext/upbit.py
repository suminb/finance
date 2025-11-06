#
# Upbit API client for fetching cryptocurrency data
#

from datetime import datetime
import json
import time

import requests

from finance.models import Granularity


#
# Example:
# {'market': 'KRW-BTC', 'korean_name': '비트코인', 'english_name': 'Bitcoin'}
#
def fetch_supported_markets():
    """Fetch supported markets from Upbit API."""
    url = "https://api.upbit.com/v1/market/all"
    resp = requests.get(url)
    data = json.loads(resp.text)
    return data


#
# Example:
# [
#   {
#     "market":"KRW-BTC",
#     "candle_date_time_utc":"2018-04-10T05:20:00",
#     "candle_date_time_kst":"2018-04-10T14:20:00",
#     "opening_price":7349000.00000000,
#     "high_price":7372000.00000000,
#     "low_price":7342000.00000000,
#     "trade_price":7360000.00000000,
#     "timestamp":1523337903151,
#     "candle_acc_trade_price":579251226.31283000,
#     "candle_acc_trade_volume":78.73143540,
#     "unit":5
#   },
#   ...
# ]
#
def fetch_tickers(currency, base_currency="KRW", minutes=15, until=datetime.utcnow()):
    """Fetch ticker data from Upbit API."""
    url = f"https://api.upbit.com/v1/candles/minutes/{minutes}"
    params = {
        "market": f"{base_currency}-{currency}",
        "count": 200,
        "to": until.strftime("%Y-%m-%d %H:%M:%H"),
    }
    resp = requests.get(url, params=params)
    data = json.loads(resp.text)
    return data


def fetch_tickers_continuously(
    currency, base_currency="KRW", minutes=15, until=datetime.utcnow()
):
    """Fetch tickers continuously, going back in time."""
    while True:
        result = fetch_tickers(currency, base_currency, minutes, until)
        if result:
            for r in result:
                yield r
        else:
            break
        last_datetime_str = result[-1]["candle_date_time_utc"]
        until = datetime.strptime(last_datetime_str, "%Y-%m-%dT%H:%M:%S")
        time.sleep(0.1)


# Granularity to minutes mapping for Upbit API
granularity_to_minutes = {
    Granularity.min: 1,
    Granularity.three_min: 3,
    Granularity.five_min: 5,
    Granularity.fifteen_min: 15,
    Granularity.hour: 60,
    Granularity.four_hour: 240,
}


def get_ticker_data(
    currency: str,
    base_currency="KRW",
    granularity: str = Granularity.fifteen_min,
    until=datetime.utcnow(),
):
    """Get ticker data as a list of dictionaries.

    Returns a generator of standardized ticker records.

    :param currency: Currency code (e.g., 'BTC')
    :param base_currency: Base currency code (default: 'KRW')
    :param granularity: Time granularity (from Granularity enum)
    :param until: Fetch data until this datetime
    :return: Generator of ticker records with standardized fields
    """
    records = fetch_tickers_continuously(
        currency, base_currency, granularity_to_minutes[granularity], until
    )

    for r in records:
        evaluated_at = datetime.strptime(r["candle_date_time_utc"], "%Y-%m-%dT%H:%M:%S")
        yield {
            "symbol": currency,
            "base_currency": base_currency,
            "evaluated_at": evaluated_at,
            "open": r["opening_price"],
            "close": r["trade_price"],
            "low": r["low_price"],
            "high": r["high_price"],
            "volume": r["candle_acc_trade_volume"],
            "granularity": granularity,
            "source": "upbit",
        }
