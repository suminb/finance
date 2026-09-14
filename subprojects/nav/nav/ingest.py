"""0650 거래내역조회 exports into a normalized transaction table."""

import json
import os
from datetime import timezone
from decimal import Decimal
from typing import Iterable, List, Optional

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


def normalize(
    records: Iterable, symbol_map: SymbolMap, category_map: CategoryMap
) -> List[Transaction]:
    """Turns provider Records into normalized transactions.

    Resolution and validation happen up front over the whole batch, so an
    unmapped 종목명 or 거래종류 reports every offender at once and nothing is
    written.
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
    overlapping exports are safe.
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
