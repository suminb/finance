from math import nan


class BaseProfile:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.name = None
        self.current_price = nan
        self.outstanding_shares = nan
        self.eps = nan
        self.bps = nan

    def parse(self, raw: str):
        raise NotImplementedError

    @property
    def market_cap(self):
        return self.current_price * self.outstanding_shares

    @property
    def per(self):
        if self.eps > 0:
            return self.current_price / self.eps
        else:
            return nan

    @property
    def pbr(self):
        return self.current_price / self.bps
