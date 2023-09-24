from datetime import date, datetime
from math import nan

from logbook import Logger


log = Logger(__name__)
nan = float("nan")


class Financials:
    def __init__(self, data: dict):
        self.data = data
        if "symbol" in data:
            self.symbol = data["symbol"]
        else:
            self.symbol = "(unknown)"

    @property
    def market_cap(self):
        if "price" not in self.data:
            log.warn(f"Missing key 'price' {self.symbol} financials")
            return nan
        elif "marketCap" not in self.data["price"]:
            log.warn(f"Missing key 'price.marketCap' for {self.symbol} financials")
            return nan
        elif "raw" not in self.data["price"]["marketCap"]:
            log.warn(f"Missing key 'price.marketCap.raw' for {self.symbol} financials")
            return nan
        return self.data["price"]["marketCap"]["raw"]

    def _extract_raw_values_for_earnings(self, earnings: dict):
        return {
            "date": earnings["date"],
            "revenue": earnings["revenue"]["raw"],
            "earnings": earnings["earnings"]["raw"],
        }

    @property
    def yearly_earnings(self):
        if "earnings" not in self.data:
            log.warn(f"Missing key 'earnings' for {self.symbol} financials")
            return []
        elif "financialsChart" not in self.data["earnings"]:
            symbol = self.data["symbol"]
            log.warn(
                f"Missing key 'earnings.financialsChart' for {self.symbol} financials"
            )
            return []
        return [
            self._extract_raw_values_for_earnings(earnings)
            for earnings in self.data["earnings"]["financialsChart"]["yearly"]
        ]

    @property
    def quarterly_earnings(self):
        return [
            self._extract_raw_values_for_earnings(earnings)
            for earnings in self.data["earnings"]["financialsChart"]["quarterly"]
        ]

    @property
    def most_recent_yearly_earnings(self):
        earnings = self.yearly_earnings

        # As a matter of fact, `date` is actually year
        recent_year = max(x["date"] for x in earnings)

        # It seems like the annual earnings are in chronological order,
        # but there is no such guarantee and thus we added an assertion statement here.
        recent_earnings = earnings[-1]
        assert recent_earnings["date"] == recent_year

        return recent_earnings

    @property
    def most_recent_quarterly_earnings(self):
        earnings = self.quarterly_earnings

        # 'quarter' looks like "1Q2020", "4Q2019", etc.
        recent_quarter = max(x["date"].split("Q")[::-1] for x in earnings)
        recent_quarter = "Q".join(recent_quarter[::-1])

        # It seems like the quarterly earnings are in chronological order,
        # but there is no such guarantee and thus we added an assertion statement here.
        recent_earnings = earnings[-1]
        assert recent_earnings["date"] == recent_quarter

        return recent_earnings

    def yearly_growth_rates(self, key="revenue"):
        """Calculates annual growth rates."""
        assert key in ["revenue", "earnings"]

        def growth_rate(x, y):
            try:
                return (y[key] - x[key]) / x[key]
            except ZeroDivisionError:
                return nan

        return [
            growth_rate(x, y)
            for x, y in zip(self.yearly_earnings[:-1], self.yearly_earnings[1:])
        ]

    @property
    def yearly_growth_rates_by_revenue(self):
        return self.yearly_growth_rates("revenue")

    @property
    def yearly_growth_rates_by_earnings(self):
        return self.yearly_growth_rates("earnings")


class HistoricalData:
    def __init__(self, data: dict):
        self.data = data
        if "symbol" in data:
            self.symbol = data["symbol"]
        else:
            self.symbol = "(unknown)"

    @property
    def first_trade_date(self):
        if "firstTradeDate" not in self.data:
            return None
        timestamp = self.data["firstTradeDate"]
        return datetime.utcfromtimestamp(timestamp)

    def is_price_record(self, record):
        keys = ["date", "open", "high", "low", "close", "adjclose", "volume"]
        contains_key = [(k in record) and (record[k] is not None) for k in keys]
        return all(contains_key)

    @property
    def prices(self):
        """NOTE: The `prices` records contain different types of information
        such as dividend, and this method returns price records only.
        """
        if "prices" not in self.data:
            log.warn(f"Prices information not found in financials for {self.symbol}")
            return []
        return [
            {
                "date": datetime.utcfromtimestamp(d["date"]),
                "open": round(d["open"], 2),
                "high": round(d["high"], 2),
                "low": round(d["low"], 2),
                "close": round(d["close"], 2),
                "adjclose": round(d["adjclose"], 2),
                "volume": d["volume"],
            }
            for d in self.data["prices"]
            if self.is_price_record(d)
        ]

    @property
    def most_recent_price(self):
        try:
            return self.prices[0]["close"]
        except IndexError:
            return nan


class Profile:
    def __init__(self, data: dict, region: str):
        self.data = data
        self.region = region
        if "symbol" in data:
            self.symbol = data["symbol"]
        else:
            self.symbol = "(unknown)"

    @property
    def name(self) -> str:
        return self.data["quoteType"]["longName"]

    @property
    def quote_type(self) -> str:
        return self.data["quoteType"]["quoteType"]

    @property
    def exchange(self) -> str:
        return self.data["price"]["exchange"]

    @property
    def currency(self) -> str:
        return self.data["price"]["currency"]

    @property
    def market_cap(self) -> float:
        try:
            return self.data["price"]["marketCap"]["raw"]
        except KeyError:
            return nan

    @property
    def total_assets(self) -> float:
        # NOTE: What is the difference between total assets and market cap?
        try:
            return self.data["summaryDetail"]["totalAssets"]["raw"]
        except KeyError:
            return nan

    @property
    def close(self):
        return self.data["summaryDetail"]["previousClose"]["raw"]

    @property
    def volume(self):
        return self.data["summaryDetail"]["regularMarketVolume"]["raw"]

    @property
    def average_volume_10days(self):
        try:
            return self.data["summaryDetail"]["averageVolume10days"]["raw"]
        except KeyError:
            return nan

    @property
    def listed_date(self) -> date:
        raise NotImplementedError

    @property
    def sector(self) -> str:
        if "sector" not in self.data["assetProfile"]:
            return "Unknown"
        return self.data["assetProfile"]["sector"]

    @property
    def business_address(self) -> str:
        raise NotImplementedError

    # TODO: SEC filings
    # TODO: Calendar events
    # TODO: fundInceptionDate?


class Statistics:
    def __init__(self, data: dict, region: str):
        self.data = data
        self.region = region
        if "symbol" in data:
            self.symbol = data["symbol"]
        else:
            self.symbol = "(unknown)"

    @property
    def forward_eps(self):
        if (
            "defaultKeyStatistics" in self.data
            and "forwardEps" in self.data["defaultKeyStatistics"]
            and "raw" in self.data["defaultKeyStatistics"]["forwardEps"]
        ):
            return self.data["defaultKeyStatistics"]["forwardEps"]["raw"]

    @property
    def close(self) -> float:
        return self.data["financialData"]["currentPrice"][
            "raw"
        ]  # TODO: Not sure if this is the right key

    @property
    def currency(self) -> str:
        return self.data["summaryDetail"]["currency"]

    @property
    def market_cap(self) -> float:
        return self.data["summaryDetail"]["marketCap"]["raw"]

    @property
    def volume(self) -> float:
        return self.data["summaryDetail"]["volume"]["raw"]

    @property
    def exchange(self) -> str:
        return self.data["quoteType"]["exchange"]

    @property
    def name(self) -> str:
        return self.data["quoteType"]["longName"]

    @property
    def quote_type(self) -> str:
        return self.data["quoteType"]["quoteType"]
