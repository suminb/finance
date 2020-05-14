from math import nan


class BaseProfile:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.name = None
        self.current_price = nan
        self.outstanding_shares = nan

    def parse(self, raw: str):
        raise NotImplementedError
