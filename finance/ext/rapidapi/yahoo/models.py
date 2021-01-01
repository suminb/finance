from datetime import datetime


class Financials:
    def __init__(self, data: dict):
        self.data = data

    @property
    def market_cap(self):
        return self.data["price"]["marketCap"]["raw"]

    @property
    def most_recent_yearly_earnings(self):
        earnings = self.data["earnings"]["financialsChart"]["yearly"]

        # As a matter of fact, `date` is actually year
        recent_year = max(x["date"] for x in earnings)

        # It seems like the annual earnings are in chronological order,
        # but there is no such guarantee and thus we added an assertion statement here.
        recent_earnings = earnings[-1]
        assert recent_earnings["date"] == recent_year

        return {
            "date": recent_earnings["date"],
            "revenue": recent_earnings["revenue"]["raw"],
            "earnings": recent_earnings["earnings"]["raw"],
        }

    @property
    def most_recent_quarterly_earnings(self):
        earnings = self.data["earnings"]["financialsChart"]["quarterly"]

        # 'quarter' looks like "1Q2020", "4Q2019", etc.
        recent_quarter = max(x["date"].split("Q")[::-1] for x in earnings)
        recent_quarter = "Q".join(recent_quarter[::-1])

        # It seems like the quarterly earnings are in chronological order,
        # but there is no such guarantee and thus we added an assertion statement here.
        recent_earnings = earnings[-1]
        assert recent_earnings["date"] == recent_quarter

        return {
            "date": recent_earnings["date"],
            "revenue": recent_earnings["revenue"]["raw"],
            "earnings": recent_earnings["earnings"]["raw"],
        }


class HistoricalData:
    def __init__(self, data: dict):
        self.data = data

    @property
    def first_trade_date(self):
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
                "date": d["date"],
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
        return self.data["assetProfile"]["sector"]
