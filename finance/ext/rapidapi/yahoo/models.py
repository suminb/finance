from datetime import datetime
from math import nan

from logbook import Logger


log = Logger(__name__)


class Financials:
    def __init__(self, data: dict):
        self.data = data

    @property
    def market_cap(self):
        if "raw" not in self.data["price"]["marketCap"]:
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
        if "financialsChart" not in self.data["earnings"]:
            symbol = self.data["symbol"]
            log.warn(f"financialsChart does not exist ({symbol})")
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

    @property
    def yearly_growth_rates(self, key="revenue"):
        """Calculates annual growth rates."""
        assert key in ["revenue", "earnings"]

        def growth_rate(x, y):
            try:
                return y[key] - x[key] / x[key]
            except ZeroDivisionError:
                return nan

        return [
            growth_rate(x, y)
            for x, y in zip(self.yearly_earnings[:-1], self.yearly_earnings[1:])
        ]


class HistoricalData:
    def __init__(self, data: dict):
        self.data = data

    @property
    def first_trade_date(self):
        if "firstTradeDate" not in self.data:
            return None
        timestamp = self.data["firstTradeDate"]
        return datetime.utcfromtimestamp(timestamp)

    def is_price_record(self, record):
        keys = ["date", "open", "high", "low", "close", "adjclose", "volume"]
        contains_key = [(k in record) for k in keys]
        return all(contains_key)

    @property
    def prices(self):
        """NOTE: The `prices` records contain different types of information
        such as dividend, and this method returns price records only.
        """
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
        return self.prices[0]["close"]


class Profile:
    def __init__(self, data: dict):
        self.data = data

    @property
    def sector(self):
        if "sector" not in self.data["assetProfile"]:
            return "Unknown"
        return self.data["assetProfile"]["sector"]
