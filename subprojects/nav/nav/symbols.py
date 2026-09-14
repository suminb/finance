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
        # Generate stub by round-tripping through YAML to properly escape names.
        # Each entry is: - {name: "...", ticker: ???, currency: ???}
        # where the name is quoted if it contains special characters.
        lines = []
        for name in self.names:
            # Use safe_dump to escape the name properly, preserving Unicode.
            # Extract the quoted form from the dumped YAML.
            escaped_name = yaml.safe_dump(
                {"name": name}, default_flow_style=True, allow_unicode=True
            ).strip()
            # safe_dump produces "{name: '...'}\n", we want just the quoted value
            # Extract the value after "name: "
            start = escaped_name.find("name: ") + len("name: ")
            quoted_name = escaped_name[start:escaped_name.rfind("}")]
            lines.append("- {{name: {}, ticker: '???', currency: '???'}}".format(quoted_name))
        self.stub = "\n".join(lines)
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
            # Check for duplicate names with conflicting mappings
            existing_symbol = self._by_name.get(symbol.name)
            if existing_symbol is not None:
                if (existing_symbol.ticker != symbol.ticker or
                    existing_symbol.currency != symbol.currency):
                    raise ValueError(
                        "duplicate name '{}': ({}, {}) and ({}, {})".format(
                            symbol.name,
                            existing_symbol.ticker, existing_symbol.currency,
                            symbol.ticker, symbol.currency
                        )
                    )
                # Exact duplicate (same name, ticker, currency) is allowed, so just continue
                continue

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
            raise UnknownSymbolError([name]) from None

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
