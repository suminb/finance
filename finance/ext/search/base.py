class Listing:
    def __init__(self, symbol, name, url):
        self.symbol = symbol
        self.name = name
        self.url = url

    def __repr__(self):
        return f"Listing({self.symbol}, {self.name}, {self.url})"
