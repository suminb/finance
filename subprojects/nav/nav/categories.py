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
        # Generate stub by round-tripping through YAML to properly escape categories.
        # Each entry is: - {category: "...", handler: '???'}
        # where the category is quoted if it contains special characters.
        lines = []
        for category in self.categories:
            # Use safe_dump to escape the category properly, preserving Unicode.
            escaped_category = yaml.safe_dump(
                {"category": category}, default_flow_style=True, allow_unicode=True
            ).strip()
            # safe_dump produces "{category: '...'}\n", we want just the quoted value
            start = escaped_category.find("category: ") + len("category: ")
            quoted_category = escaped_category[start:escaped_category.rfind("}")]
            lines.append("- {{category: {}, handler: '???'}}".format(quoted_category))
        self.stub = "\n".join(lines)
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
    def __init__(self, entries: Iterable[Dict[str, str]]):
        self._mapping: Dict[str, str] = {}
        for entry in entries:
            category = entry["category"]
            handler = entry["handler"]
            if handler not in HANDLERS:
                raise ValueError(
                    "unknown handler {!r} for 거래종류 {!r}; known handlers: {}".format(
                        handler, category, ", ".join(sorted(HANDLERS))
                    )
                )
            # Check for duplicate categories with conflicting handlers
            existing_handler = self._mapping.get(category)
            if existing_handler is not None:
                if existing_handler != handler:
                    raise ValueError(
                        "duplicate category '{}': handlers '{}' and '{}'".format(
                            category, existing_handler, handler
                        )
                    )
                # Exact duplicate (same category, same handler) is allowed, so just continue
                continue
            self._mapping[category] = handler

    def validate(self, categories: Iterable[str]) -> None:
        missing = sorted({c for c in categories if c not in self._mapping})
        if missing:
            raise UnknownCategoryError(missing)

    def legs_for(self, transaction: Transaction) -> List[Leg]:
        try:
            handler_name = self._mapping[transaction.category]
        except KeyError:
            raise UnknownCategoryError([transaction.category]) from None
        return HANDLERS[handler_name](transaction)


def load(path: str) -> CategoryMap:
    with open(path, encoding="utf-8") as fin:
        entries = yaml.safe_load(fin) or []
    return CategoryMap(entries)
