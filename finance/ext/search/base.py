class Listing:
    def __init__(self, symbol, name, url, price, volume):
        self.symbol = symbol
        self.name = name
        self.url = url
        self.price = price
        self.volume = volume

    def __repr__(self):
        return f"Listing({self.symbol}, {self.name}, {self.url}, {self.price}, {self.volume})"
