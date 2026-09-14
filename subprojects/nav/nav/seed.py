"""The opening 잔고 that replay starts from."""

from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import Dict

import yaml

from nav.symbols import SymbolMap


@dataclass(frozen=True)
class Seed:
    seed_date: date_type
    positions: Dict[str, Decimal]
    cash: Dict[str, Decimal]


def load(path: str, symbol_map: SymbolMap) -> Seed:
    with open(path, encoding="utf-8") as fin:
        content = yaml.safe_load(fin) or {}

    if "seed_date" not in content:
        raise ValueError("seed_date is required in {}".format(path))
    seed_date = content["seed_date"]
    # datetime is a subclass of date, so a bare isinstance(seed_date, date)
    # check would silently accept a timestamp with a time component (e.g. a
    # value pasted straight from a 잔고 export). Reject that explicitly with
    # type() so only a true date passes.
    if isinstance(seed_date, datetime):
        raise ValueError(
            "seed_date must not have a time component, got {!r}; "
            "drop the time and keep only the date".format(seed_date)
        )
    if type(seed_date) is not date_type:
        raise ValueError("seed_date must be a date, got {!r}".format(seed_date))

    positions: Dict[str, Decimal] = {}
    for entry in content.get("positions") or []:
        ticker = entry["ticker"]
        try:
            symbol_map.currency_of(ticker)
        except KeyError:
            raise ValueError(
                "{} in {} is not listed in symbols.yaml".format(ticker, path)
            )
        positions[ticker] = Decimal(str(entry["quantity"]))

    cash = {
        currency: Decimal(str(amount))
        for currency, amount in (content.get("cash") or {}).items()
    }
    return Seed(seed_date=seed_date, positions=positions, cash=cash)
