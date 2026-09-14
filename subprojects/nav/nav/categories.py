"""거래종류 to inventory-movement mapping.

categories.yaml maps each Korean 거래종류 string to the name of a handler. It
holds no arithmetic: what varies between exports is which string means what,
and that belongs in data, while the arithmetic is fixed and belongs in tested
code.
"""

from typing import Callable, Dict, Iterable, List

import yaml

from nav.model import Leg, Transaction, cash_ticker


class UnknownCategoryError(Exception):
    def __init__(self, categories: List[str]):
        self.categories = list(categories)
        self.stub = "\n".join(
            "- {category: %s, handler: ???}" % c for c in self.categories
        )
        super().__init__(
            "Unmapped 거래종류 ({}). Add to categories.yaml:\n{}".format(
                len(self.categories), self.stub
            )
        )


def _require_ticker(transaction: Transaction) -> str:
    if not transaction.ticker:
        raise ValueError(
            "{} requires a ticker but 종목명 was empty (seq {} on {})".format(
                transaction.category, transaction.seq, transaction.date.date()
            )
        )
    return transaction.ticker


def buy(t: Transaction) -> List[Leg]:
    return [
        Leg(_require_ticker(t), t.quantity),
        Leg(cash_ticker(t.currency), -(t.amount + t.fees + t.tax)),
    ]


def sell(t: Transaction) -> List[Leg]:
    return [
        Leg(_require_ticker(t), -t.quantity),
        Leg(cash_ticker(t.currency), t.amount - t.fees - t.tax),
    ]


def cash_in(t: Transaction) -> List[Leg]:
    return [Leg(cash_ticker(t.currency), t.amount)]


def cash_out(t: Transaction) -> List[Leg]:
    return [Leg(cash_ticker(t.currency), -t.amount)]


def dividend(t: Transaction) -> List[Leg]:
    return [Leg(cash_ticker(t.currency), t.amount - t.tax)]


def interest(t: Transaction) -> List[Leg]:
    return [Leg(cash_ticker(t.currency), t.amount - t.tax)]


def fee(t: Transaction) -> List[Leg]:
    return [Leg(cash_ticker(t.currency), -(t.amount + t.fees + t.tax))]


def noop(t: Transaction) -> List[Leg]:
    return []


HANDLERS: Dict[str, Callable[[Transaction], List[Leg]]] = {
    "buy": buy,
    "sell": sell,
    "cash_in": cash_in,
    "cash_out": cash_out,
    "dividend": dividend,
    "interest": interest,
    "fee": fee,
    "noop": noop,
}


class CategoryMap:
    def __init__(self, mapping: Dict[str, str]):
        for category, handler in mapping.items():
            if handler not in HANDLERS:
                raise ValueError(
                    "unknown handler {!r} for 거래종류 {!r}; known handlers: {}".format(
                        handler, category, ", ".join(sorted(HANDLERS))
                    )
                )
        self._mapping = dict(mapping)

    def validate(self, categories: Iterable[str]) -> None:
        missing = sorted({c for c in categories if c not in self._mapping})
        if missing:
            raise UnknownCategoryError(missing)

    def legs_for(self, transaction: Transaction) -> List[Leg]:
        try:
            handler_name = self._mapping[transaction.category]
        except KeyError:
            raise UnknownCategoryError([transaction.category])
        return HANDLERS[handler_name](transaction)


def load(path: str) -> CategoryMap:
    with open(path, encoding="utf-8") as fin:
        entries = yaml.safe_load(fin) or []
    return CategoryMap({e["category"]: e["handler"] for e in entries})
