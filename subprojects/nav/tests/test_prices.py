from datetime import datetime, timezone

import pandas as pd
import pytest

from nav import prices, symbols

SYMBOLS_YAML = """
- {name: 애플, ticker: AAPL, currency: USD}
- {name: 삼성전자보통주, ticker: 005930.KS, currency: KRW}
"""


@pytest.fixture
def symbol_map(tmp_path):
    path = tmp_path / "symbols.yaml"
    path.write_text(SYMBOLS_YAML, encoding="utf-8")
    return symbols.load(str(path))


def utc(day):
    return datetime(2026, 9, day, tzinfo=timezone.utc)


HISTORICAL = pd.DataFrame(
    [
        {"symbol": "AAPL", "date": pd.Timestamp("2026-09-01"), "close": 150.0},
        {"symbol": "AAPL", "date": pd.Timestamp("2026-09-02"), "close": 155.0},
        {"symbol": "005930.KS", "date": pd.Timestamp("2026-09-01"), "close": 71000.0},
        {"symbol": "005930.KS", "date": pd.Timestamp("2026-09-02"), "close": 72000.0},
        {"symbol": "USDKRW=X", "date": pd.Timestamp("2026-09-01"), "close": 1300.0},
        {"symbol": "USDKRW=X", "date": pd.Timestamp("2026-09-02"), "close": 1310.0},
    ]
)


def test_fx_symbol_for_a_foreign_currency():
    assert prices.fx_symbol("USD", "KRW") == "USDKRW=X"
    assert prices.fx_symbol("JPY", "KRW") == "JPYKRW=X"


def test_fx_symbol_for_the_base_currency_is_none():
    assert prices.fx_symbol("KRW", "KRW") is None


def test_region_for():
    assert prices.region_for("005930.KS") == "KR"
    assert prices.region_for("035720.KQ") == "KR"
    assert prices.region_for("USDKRW=X") == "FX"
    assert prices.region_for("AAPL") == "US"


def test_required_symbols_includes_holdings_and_fx(symbol_map):
    assert prices.required_symbols(["AAPL", "005930.KS"], symbol_map, "KRW") == [
        "005930.KS",
        "AAPL",
        "USDKRW=X",
    ]


def test_required_symbols_honours_extra_currencies(symbol_map):
    assert prices.required_symbols(
        ["005930.KS"], symbol_map, "KRW", extra_currencies=["USD"]
    ) == ["005930.KS", "USDKRW=X"]


def test_extra_currencies_are_priced_even_when_nothing_is_held_in_them(symbol_map):
    table, _ = prices.build_price_table(
        HISTORICAL, ["005930.KS"], symbol_map, [utc(2)], "KRW", extra_currencies=["USD"]
    )
    assert table[utc(2)]["_USD"] == pytest.approx(1310.0)


def test_prices_are_converted_to_the_base_currency(symbol_map):
    table, _ = prices.build_price_table(
        HISTORICAL, ["AAPL", "005930.KS"], symbol_map, [utc(2)], "KRW"
    )
    assert table[utc(2)]["AAPL"] == pytest.approx(155.0 * 1310.0)
    assert table[utc(2)]["005930.KS"] == pytest.approx(72000.0)


def test_cash_tickers_are_priced_at_the_fx_rate(symbol_map):
    table, _ = prices.build_price_table(
        HISTORICAL, ["AAPL"], symbol_map, [utc(2)], "KRW"
    )
    assert table[utc(2)]["_USD"] == pytest.approx(1310.0)
    assert table[utc(2)]["_KRW"] == 1.0


def test_a_missing_close_carries_the_last_one_forward(symbol_map):
    table, stale = prices.build_price_table(
        HISTORICAL, ["AAPL"], symbol_map, [utc(3)], "KRW"
    )
    assert table[utc(3)]["AAPL"] == pytest.approx(155.0 * 1310.0)
    assert "AAPL" in stale[utc(3)]


def test_a_fresh_close_is_not_marked_stale(symbol_map):
    _, stale = prices.build_price_table(
        HISTORICAL, ["AAPL"], symbol_map, [utc(2)], "KRW"
    )
    assert stale[utc(2)] == []


def test_a_date_before_any_close_raises(symbol_map):
    with pytest.raises(prices.NoPriceHistoryError, match="AAPL"):
        prices.build_price_table(
            HISTORICAL, ["AAPL"], symbol_map, [datetime(2025, 1, 1, tzinfo=timezone.utc)], "KRW"
        )
