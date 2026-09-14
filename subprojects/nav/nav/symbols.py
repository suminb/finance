"""Resolution of 미래에셋 종목명 to a ticker and a currency.

미래에셋 truncates 종목명 inconsistently between export vintages, so several
names legitimately map to one ticker. Nothing is inferred: a name that is not
listed is an error, because a NAV series that is silently wrong is worse than
one that refuses to build.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List

import yaml


@dataclass(frozen=True)
class Symbol:
    name: str
    ticker: str
    currency: str


class UnknownSymbolError(Exception):
    def __init__(self, names: List[str]):
        self.names = list(names)
        self.stub = "\n".join(
            "- {name: %s, ticker: ???, currency: ???}" % name for name in self.names
        )
        super().__init__(
            "Unmapped 종목명 ({}). Add to symbols.yaml:\n{}".format(
                len(self.names), self.stub
            )
        )


class SymbolMap:
    def __init__(self, symbols: Iterable[Symbol]):
        self._by_name: Dict[str, Symbol] = {}
        self._currency_by_ticker: Dict[str, str] = {}
        for symbol in symbols:
            self._by_name[symbol.name] = symbol
            existing = self._currency_by_ticker.get(symbol.ticker)
            if existing is not None and existing != symbol.currency:
                raise ValueError(
                    "conflicting currency for {}: {} and {}".format(
                        symbol.ticker, existing, symbol.currency
                    )
                )
            self._currency_by_ticker[symbol.ticker] = symbol.currency

    def resolve(self, name: str) -> Symbol:
        try:
            return self._by_name[name]
        except KeyError:
            raise UnknownSymbolError([name])

    def resolve_all(self, names: Iterable[str]) -> Dict[str, Symbol]:
        names = list(names)
        missing = sorted({n for n in names if n not in self._by_name})
        if missing:
            raise UnknownSymbolError(missing)
        return {n: self._by_name[n] for n in names}

    def currency_of(self, ticker: str) -> str:
        return self._currency_by_ticker[ticker]

    def tickers(self) -> List[str]:
        return sorted(self._currency_by_ticker)


def load(path: str) -> SymbolMap:
    with open(path, encoding="utf-8") as fin:
        entries = yaml.safe_load(fin) or []
    return SymbolMap(
        Symbol(name=e["name"], ticker=e["ticker"], currency=e["currency"])
        for e in entries
    )
