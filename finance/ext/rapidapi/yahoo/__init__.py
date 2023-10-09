from datetime import datetime
import json
import os

from logbook import Logger
import requests

from finance.ext.rapidapi.yahoo.models import (
    Financials,
    HistoricalData,
    Profile,
    Statistics,
)

from typing import Callable, Generator


log = Logger(__name__)
nan = float("NaN")

API_HOST = "yh-finance.p.rapidapi.com"
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


def cache_exists(
    topic, symbol, region, cache_dir=DEFAULT_CACHE_DIR, check_stale_data=True
):
    """Check if the cache file exists.

    :param check_stale_data: If True, check if the cache file is older than 7 days.
    """
    path = get_cache_filename(topic, symbol, region, cache_dir)
    if os.path.exists(path):
        if check_stale_data and os.path.getmtime(path) < datetime.now().timestamp() - (
            86400 * 7
        ):
            log.info(f"Cache file {path} is older than 7 days. Skipping...")
            return False
        else:
            return True
    else:
        return False


def load_cache(topic, symbol, region, cache_dir=DEFAULT_CACHE_DIR):
    path = get_cache_filename(topic, symbol, region, cache_dir)
    with open(path, "r") as fin:
        parsed = json.loads(fin.read())
        if int(parsed.get("status_code", 0)) // 100 == 3:
            log.warn(f"Cache file contains some sort of redirection. Skipping...")
            return None
        return parsed


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
        # This may return None if the cache file is invalid
        data = load_cache(topic, symbol, region, cache_dir)
    else:
        data = None

    if data is None:
        data = fetch(symbol, region)
        save_cache(topic, symbol, region, data, cache_dir)
    return data


def handle_http_request(symbol: str, url, headers, params):
    resp = requests.get(url, headers=headers, params=params, allow_redirects=True)
    if resp.status_code == 200:
        return json.loads(resp.text)
    elif resp.status_code // 100 == 3 and "Location" in resp.headers:
        resp = requests.get(resp.headers["Location"], headers=headers)
        if resp.status_code == 200:
            return json.loads(resp.text)

    return {
        "symbol": symbol,
        "status_code": resp.status_code,
        "message": resp.text,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def fetch_financials(symbol: str, region="US"):
    """See https://rapidapi.com/apidojo/api/yh-finance/ for more details."""
    log.info(f"Fetching financials for {symbol}")
    url = f"https://{API_HOST}/stock/v2/get-financials"
    params = {"symbol": symbol, "region": region}
    return handle_http_request(symbol, url, headers, params)


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
    """See https://rapidapi.com/apidojo/api/yh-finance/ for more details."""
    log.info(f"Fetching historical data for {symbol}")
    url = f"https://{API_HOST}/stock/v3/get-historical-data"
    params = {"symbol": symbol, "region": region}
    return handle_http_request(symbol, url, headers, params)


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
    return handle_http_request(symbol, url, headers, params)


def get_profile(
    symbol: str,
    region="US",
    fetch=fetch_profile,
    use_cache=True,
    cache_dir=DEFAULT_CACHE_DIR,
):
    topic = "profile"
    data = fetch_or_load_cache(topic, symbol, region, fetch, use_cache, cache_dir)
    return Profile(data, region)


def fetch_statistics(symbol: str, region="US"):
    log.info(f"Fetching statistics for {symbol}")
    url = f"https://{API_HOST}/stock/v3/get-statistics"
    params = {"symbol": symbol}
    return handle_http_request(symbol, url, headers, params)


def get_statistics(
    symbol: str,
    region="US",
    fetch=fetch_statistics,
    use_cache=True,
    cache_dir=DEFAULT_CACHE_DIR,
):
    topic = "statistics"
    data = fetch_or_load_cache(topic, symbol, region, fetch, use_cache, cache_dir)
    return Statistics(data, region)


def get_statistics_list(symbols, region="US") -> Generator:
    for symbol in symbols:
        try:
            statistics = get_statistics(symbol, region)
            properties = [
                "symbol",
                "region",
                "quote_type",
                "currency",
                "name",
                "close",
                "volume",
                "market_cap",
            ]
            data = {k: getattr(statistics, k) for k in properties}
        except Exception as e:
            print(f"Failed to get statistics for {symbol}: {e}")
        else:
            data["fetched_at"] = datetime.utcnow()
            yield data


# FIXME: quotes? stocks? tickers? What should we call this?
def discover_quotes(screen_ids="MOST_ACTIVES") -> Generator:
    tickers = _discover_quotes(screen_ids)
    fetched_at = datetime.utcnow()
    for quote in tickers["finance"]["result"][0]["quotes"]:
        yield {
            "symbol": quote["symbol"],
            "region": "US",
            "quote_type": quote["quoteType"],
            "currency": quote["currency"],
            "name": quote["longName"],
            "close": nan,  # FIXME: It would be nice if these values can be directly obtained
            "volume": nan,
            "market_cap": nan,
            "fetched_at": fetched_at,
        }


def _discover_quotes(screen_ids="MOST_ACTIVES"):
    log.info(f"Discovering tickers (screen_ids={screen_ids})")
    url = f"https://{API_HOST}/screeners/get-symbols-by-predefined"
    params = {"scrIds": screen_ids}
    resp = requests.get(url, headers=headers, params=params)

    if resp.status_code == 200:
        return json.loads(resp.text)
    else:
        log.error(resp.text)
