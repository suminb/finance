"""Reconciliation of the replayed inventory against a real statement."""

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

import pandas as pd

from finance.ext.models import Portfolio

from nav.model import cash_ticker
from nav.seed import Seed

# This is a "did the broker and I disagree" tolerance, not a "is this residue
# zero" tolerance -- that second question is finance.ext.models.QUANTITY_EPSILON
# (1e-9), which absorbs float drift from repeated += on a closed position.
# TOLERANCE only has to absorb the same kind of float noise on the *compare*
# side (float(Decimal(...)) conversions, subtraction), not model a real-world
# discrepancy, so it stays deliberately loose relative to float64 epsilon
# while remaining far tighter than any quantity or cash amount a broker
# statement would actually disagree by. Kept as a distinct constant rather
# than importing QUANTITY_EPSILON because the two answer different questions
# and a future change to one should not silently move the other.
TOLERANCE = 1e-6


@dataclass(frozen=True)
class Difference:
    ticker: str
    computed: float
    actual: float
    delta: float


def compare(portfolio: Portfolio, statement: Seed, when: datetime) -> List[Difference]:
    """Differences between the replayed inventory and a real 잔고.

    A non-empty result means the transaction export is missing something --
    most often a corporate action, which the export tends to omit.
    """
    computed = {t: float(q) for t, q in portfolio.eval_inventory(when).items()}
    actual = {t: float(q) for t, q in statement.positions.items()}
    actual.update(
        {cash_ticker(c): float(a) for c, a in statement.cash.items()}
    )

    differences = []
    for ticker in sorted(set(computed) | set(actual)):
        left = computed.get(ticker, 0.0)
        right = actual.get(ticker, 0.0)
        if abs(left - right) > TOLERANCE:
            differences.append(
                Difference(ticker=ticker, computed=left, actual=right, delta=right - left)
            )
    return differences


def suspicious_moves(
    historical: pd.DataFrame, tickers: Iterable[str], threshold: float = 0.4
) -> List[dict]:
    """Single-day price moves large enough to suggest a corporate action.

    Yahoo closes are split-adjusted while replayed quantities are not, so a
    split after the seed date silently breaks the NAV series. This does not
    correct for that -- it makes it visible.
    """
    flagged = []
    for ticker in tickers:
        rows = historical[historical["symbol"] == ticker].copy()
        if len(rows) < 2:
            continue
        rows["date"] = pd.to_datetime(rows["date"])
        rows = rows.sort_values("date")
        ratios = rows["close"].pct_change()
        for index, ratio in ratios.items():
            if pd.notna(ratio) and abs(ratio) >= threshold:
                flagged.append(
                    {
                        "symbol": ticker,
                        "date": rows.loc[index, "date"].date(),
                        "ratio": float(ratio),
                        "close": float(rows.loc[index, "close"]),
                    }
                )
    return flagged
