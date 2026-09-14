from datetime import datetime, timezone

import pandas as pd
import pytest

from nav import display, valuation


def utc(day):
    return datetime(2026, 9, day, tzinfo=timezone.utc)


FRAME = pd.DataFrame(
    [
        {"date": utc(1), "nav_krw": 1000.0, "nav_usd": 1.0, "holdings_krw": 900.0,
         "cash_krw": 100.0, "cash_usd": 0.0, "fx_usdkrw": 1000.0, "stale": ""},
        {"date": utc(2), "nav_krw": 1100.0, "nav_usd": 1.1, "holdings_krw": 1000.0,
         "cash_krw": 100.0, "cash_usd": 0.0, "fx_usdkrw": 1000.0, "stale": "AAPL"},
    ],
    columns=valuation.COLUMNS,
)


def test_summarize_uses_the_last_row_by_default():
    assert display.summarize(FRAME)["date"] == utc(2)


def test_summarize_reports_the_change_against_the_prior_row():
    summary = display.summarize(FRAME)
    assert summary["change_krw"] == pytest.approx(100.0)
    assert summary["change_pct"] == pytest.approx(0.1)


def test_summarize_on_the_first_row_has_no_change():
    summary = display.summarize(FRAME, when=utc(1))
    assert summary["change_krw"] == 0.0
    assert summary["change_pct"] == 0.0


def test_summarize_splits_stale_symbols():
    assert display.summarize(FRAME)["stale"] == ["AAPL"]
    assert display.summarize(FRAME, when=utc(1))["stale"] == []


def test_summarize_rejects_an_absent_date():
    with pytest.raises(KeyError):
        display.summarize(FRAME, when=utc(9))


def test_render_shows_both_currencies_and_a_stale_symbol_not_held():
    """The USD figure and the stale list are load-bearing, not decorative.

    The stale symbol (MSFT) is deliberately absent from holdings, so its
    appearance in the rendered text can only come from the stale
    annotation -- not incidentally from a holdings-table row that happens
    to share a ticker with the stale list (as AAPL would if reused here).
    """
    from rich.console import Console

    summary = {
        "date": utc(2),
        "nav_krw": 1100.0,
        "nav_usd": 1.1,
        "change_krw": 100.0,
        "change_pct": 0.1,
        "fx_usdkrw": 1000.0,
        "stale": ["MSFT"],
    }
    holdings = [
        {"ticker": "AAPL", "quantity": 10.0, "price_krw": 100.0,
         "value_krw": 1000.0, "is_cash": False, "weight": 0.9},
        {"ticker": "_KRW", "quantity": 100.0, "price_krw": 1.0,
         "value_krw": 100.0, "is_cash": True, "weight": 0.1},
    ]
    console = Console(record=True, width=100)
    console.print(display.render(summary, holdings))
    text = console.export_text()
    assert "AAPL" in text
    assert "1,100" in text
    assert "1.10 USD" in text
    assert "MSFT" in text
