class BaseProfile:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.name = ""
        self.current_price = 0
        self.outstanding_shares = 0
        raise NotImplementedError

    def parse(self, raw: str):
        raise NotImplementedError
