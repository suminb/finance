#
# FIXME: This module is under incubation. Will be go on a separate way later on...
#

import json

import requests
from sqlalchemy.exc import IntegrityError

from finance.models import Asset, AssetType, session


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


#
# Example:
# {'market': 'KRW-BTC', 'korean_name': '비트코인', 'english_name': 'Bitcoin'}
#
def fetch_supported_markets():
    url = "https://api.upbit.com/v1/market/all"
    resp = requests.get(url)

    data = json.loads(resp.text)
    return data


if __name__ == "__main__":
    records = fetch_supported_markets()
    for r in records:
        (base_currency, currency) = r["market"].split("-")
        try:
            Asset.create(
                type=AssetType.currency,
                name=r["english_name"],
                code=currency)
        except IntegrityError:
            session.rollback()

