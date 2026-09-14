"""0650 거래내역조회 exports into a normalized transaction table."""

import json
import os
from collections import Counter
from datetime import timezone
from decimal import Decimal
from typing import Iterable, List, Optional, Tuple

import pandas as pd

from nav.categories import CategoryMap
from nav.model import Transaction
from nav.symbols import SymbolMap

COLUMNS = [
    "date",
    "seq",
    "category",
    "name",
    "ticker",
    "currency",
    "amount",
    "unit_price",
    "quantity",
    "fees",
    "tax",
    "raw",
]

DECIMAL_COLUMNS = ["amount", "unit_price", "quantity", "fees", "tax"]
KEY_COLUMNS = ["date", "seq"]


class DuplicateKeyError(Exception):
    """Two distinct rows of one export share a (date, seq) key.

    Deduplication on (date, seq) is what makes re-importing a file a no-op,
    and that contract is only sound while the key is unique *within* a single
    export. If one file carries two rows under one key -- a 환전 pair sharing
    a 거래번호, say, which is exactly the two-row shape README §3 describes --
    `merge` would keep one and silently discard the other, and every later NAV
    figure would be wrong with no error anywhere.

    Within one file a repeated key can only be a violation of that key model;
    it can never be idempotency. So it is a hard error here, while a key
    repeated *across* files stays silent, which is the idempotency contract.
    """

    def __init__(self, keys: List[Tuple[object, object]], source: Optional[str] = None):
        self.keys = list(keys)
        self.source = source
        listed = ", ".join(
            "(date={}, seq={})".format(date, seq) for date, seq in self.keys
        )
        super().__init__(
            "{} (date, 거래번호) key(s) are each shared by more than one row{}: "
            "{}. nav deduplicates on that pair, so it must be unique within a "
            "single export; a repeat would make one of the rows silently "
            "vanish and every later NAV figure would be wrong. Correct the "
            "거래번호, or split the rows across separate exports, before "
            "importing.".format(
                len(self.keys),
                "" if source is None else " in {}".format(source),
                listed,
            )
        )


def assert_unique_keys(
    transactions: Iterable[Transaction], source: Optional[str] = None
) -> None:
    """Raises if two transactions from one export share a (date, seq) key."""
    counts = Counter((t.date, t.seq) for t in transactions)
    repeated = sorted(
        (key for key, count in counts.items() if count > 1),
        key=lambda k: (str(k[0]), k[1]),
    )
    if repeated:
        raise DuplicateKeyError(repeated, source=source)


def normalize(
    records: Iterable,
    symbol_map: SymbolMap,
    category_map: CategoryMap,
    source: Optional[str] = None,
) -> List[Transaction]:
    """Turns provider Records into normalized transactions.

    Resolution and validation happen up front over the whole batch, so an
    unmapped 종목명 or 거래종류 reports every offender at once and nothing is
    written. `records` must come from a single export: the (date, seq) key is
    checked for uniqueness across them (see `DuplicateKeyError`).
    """
    records = list(records)

    category_map.validate(r.category for r in records)
    names = sorted({r.name for r in records if r.name})
    resolved = symbol_map.resolve_all(names)

    transactions = []
    for record in records:
        symbol = resolved[record.name] if record.name else None
        transactions.append(
            Transaction(
                date=record.created_at.replace(tzinfo=timezone.utc),
                seq=int(record.seq),
                category=record.category,
                name=record.name,
                ticker=symbol.ticker if symbol else "",
                currency=record.currency,
                amount=record.amount,
                unit_price=record.unit_price,
                quantity=record.quantity,
                fees=record.fees,
                tax=record.tax,
                raw=json.dumps(record.raw_columns, ensure_ascii=False),
            )
        )
    assert_unique_keys(transactions, source=source)
    return transactions


def to_frame(transactions: Iterable[Transaction]) -> pd.DataFrame:
    rows = []
    for t in transactions:
        row = {
            "date": t.date,
            "seq": t.seq,
            "category": t.category,
            "name": t.name,
            "ticker": t.ticker,
            "currency": t.currency,
            "raw": t.raw,
        }
        for column in DECIMAL_COLUMNS:
            row[column] = str(getattr(t, column))
        rows.append(row)
    return pd.DataFrame(rows, columns=COLUMNS)


def from_frame(frame: pd.DataFrame) -> List[Transaction]:
    transactions = []
    for row in frame.to_dict("records"):
        values = {c: Decimal(row[c]) for c in DECIMAL_COLUMNS}
        date = pd.Timestamp(row["date"]).to_pydatetime()
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        transactions.append(
            Transaction(
                date=date,
                seq=int(row["seq"]),
                category=row["category"],
                name=row["name"],
                ticker=row["ticker"],
                currency=row["currency"],
                raw=row["raw"],
                **values,
            )
        )
    return transactions


def merge(existing: Optional[pd.DataFrame], new: pd.DataFrame) -> pd.DataFrame:
    """Combines transaction frames, keeping the later row for a repeated key.

    Deduplication is on (date, seq), so re-importing a file is a no-op and
    overlapping exports are safe -- including two overlapping exports handed
    to one `nav import` (which is what `nav rebuild` does with `imports/*.csv`).
    A key repeated here is therefore ambiguous between idempotency and data
    loss, and this function deliberately stays silent about it.

    The unambiguous case -- one export carrying two distinct rows under one key
    -- is rejected upstream, in `normalize`, where a repeat can only mean the
    key model is wrong. See `DuplicateKeyError`.
    """
    if existing is None or existing.empty:
        combined = new
    else:
        combined = pd.concat([existing, new], ignore_index=True)
    return (
        combined.drop_duplicates(subset=KEY_COLUMNS, keep="last")
        .sort_values(KEY_COLUMNS)
        .reset_index(drop=True)
    )


def load_frame(path: str) -> Optional[pd.DataFrame]:
    if not os.path.exists(path):
        return None
    return pd.read_parquet(path)


def save_frame(frame: pd.DataFrame, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    frame.to_parquet(path, index=False)
