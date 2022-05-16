import json
import os
from typing import Callable

from logbook import Logger
import requests

from finance.ext.rapidapi.yahoo.models import Financials, HistoricalData, Profile

log = Logger(__name__)

API_HOST = "apidojo-yahoo-finance-v1.p.rapidapi.com"
DEFAULT_CACHE_DIR = ".cache"
SBF_RAPIDAPI_KEY = ""

if "SBF_RAPIDAPI_KEY" in os.environ:
    SBF_RAPIDAPI_KEY = os.environ["SBF_RAPIDAPI_KEY"]
else:
    log.warn("SBF_RAPIDAPI_KEY is not set")

headers = {
    "x-rapidapi-key": SBF_RAPIDAPI_KEY,
    "x-rapidapi-host": API_HOST,
}


def get_cache_filename(topic, symbol, region, cache_dir=DEFAULT_CACHE_DIR):
    return f"{cache_dir}/{topic}_{symbol}_{region}.json"


def cache_exists(topic, symbol, region, cache_dir=DEFAULT_CACHE_DIR):
    path = get_cache_filename(topic, symbol, region, cache_dir)
    return os.path.exists(path)


def load_cache(topic, symbol, region, cache_dir=DEFAULT_CACHE_DIR):
    path = get_cache_filename(topic, symbol, region, cache_dir)
    with open(path, "r") as fin:
        return json.loads(fin.read())


def save_cache(topic, symbol, region, data, cache_dir=DEFAULT_CACHE_DIR):
    if not os.path.exists(cache_dir):
        log.info(f"Cache directory {cache_dir} does not exist. Creating one...")
        os.makedirs(cache_dir)
    path = get_cache_filename(topic, symbol, region, cache_dir)
    with open(path, "w") as fout:
        fout.write(json.dumps(data))


def fetch_or_load_cache(
    topic, symbol, region, fetch: Callable, use_cache=True, cache_dir=DEFAULT_CACHE_DIR
):
    if use_cache and cache_exists(topic, symbol, region, cache_dir):
        data = load_cache(topic, symbol, region, cache_dir)
    else:
        data = fetch(symbol, region)
        save_cache(topic, symbol, region, data, cache_dir)
    return data


def fetch_financials(symbol: str, region="US"):
    """See https://rapidapi.com/apidojo/api/yahoo-finance1?endpoint=apiendpoint_2e0b16d4-a66b-469e-bc18-b60cec60661b for more details."""
    log.info(f"Fetching financials for {symbol}")
    url = f"https://{API_HOST}/stock/v2/get-financials"
    params = {"symbol": symbol, "region": region}
    resp = requests.get(url, headers=headers, params=params)

    return json.loads(resp.text)


# TODO: Introduce a common layer for cache
def get_financials(
    symbol: str,
    region="US",
    fetch=fetch_financials,
    use_cache=True,
    cache_dir=DEFAULT_CACHE_DIR,
):
    topic = "financials"
    data = fetch_or_load_cache(topic, symbol, region, fetch, use_cache, cache_dir)
    return Financials(data)


def fetch_historical_data(symbol: str, region="US"):
    """See https://rapidapi.com/apidojo/api/yahoo-finance1?endpoint=apiendpoint_2c81ebb5-60ab-41e4-8cd2-2056b26e93c2 for more details."""
    log.info(f"Fetching historical data for {symbol}")
    url = f"https://{API_HOST}/stock/v2/get-historical-data"
    params = {"symbol": symbol, "region": region}
    resp = requests.get(url, headers=headers, params=params)

    return json.loads(resp.text)


def get_historical_data(
    symbol: str,
    region="US",
    fetch=fetch_historical_data,
    use_cache=True,
    cache_dir=DEFAULT_CACHE_DIR,
):
    topic = "historical_data"
    data = fetch_or_load_cache(topic, symbol, region, fetch, use_cache, cache_dir)
    return HistoricalData(data)


def fetch_profile(symbol: str, region="US"):
    """See https://rapidapi.com/apidojo/api/yahoo-finance1?endpoint=apiendpoint_f787ce0f-17f7-40cf-a731-f141fd61cc08 for more details."""
    log.info(f"Fetching profile for {symbol}")
    url = f"https://{API_HOST}/stock/v2/get-profile"
    params = {"symbol": symbol, "region": region}
    resp = requests.get(url, headers=headers, params=params)

    return json.loads(resp.text)


def get_profile(
    symbol: str,
    region="US",
    fetch=fetch_profile,
    use_cache=True,
    cache_dir=DEFAULT_CACHE_DIR,
):
    topic = "profile"
    data = fetch_or_load_cache(topic, symbol, region, fetch, use_cache, cache_dir)
    return Profile(data)
