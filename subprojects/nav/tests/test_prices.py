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


def test_region_for_a_tokyo_listing_is_not_us():
    """symbols.yaml ships 넥슨 일본 -> 3659.T, and this returned "US".

    The warehouse deduplicates on (date, region, symbol), so a symbol filed
    under the wrong region would duplicate rather than replace its own
    history once the region was corrected.
    """
    assert prices.region_for("3659.T") == "JP"


def test_region_for_an_unlisted_suffix_is_still_not_us():
    """Only US listings are unsuffixed, so a dot never means US.

    An unknown suffix falls back to itself: stable across runs, which is all
    the dedup key needs, and never colliding with "US".
    """
    assert prices.region_for("0700.HK") == "HK"
    assert prices.region_for("SOMETHING.XYZ") == "XYZ"
    assert prices.region_for("BRK-B") == "US"  # a dash is not a suffix


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


# --------------------------------------------------------------------------
# refresh(): the only function that writes the shared repo-root warehouse.
# Its yfinance call is monkeypatched away -- no test here touches the network.
# --------------------------------------------------------------------------


def _fetched(symbol, region, day, close, updated_at="2026-09-10"):
    """A frame shaped like finance.ext.warehouse.preprocess_historical_data's."""
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp(day),
                "close": close,
                "region": region,
                "symbol": symbol,
                "updated_at": pd.Timestamp(updated_at),
            }
        ]
    )


@pytest.fixture
def fake_fetch(monkeypatch):
    """Records every (symbol, region, period) refresh asks for."""
    calls = []

    def fetch(symbol, region="US", period="5y"):
        calls.append((symbol, region, period))
        return _fetched(symbol, region, "2026-09-02", 100.0 + len(calls))

    monkeypatch.setattr("finance.ext.warehouse.fetch_historical_data", fetch)
    return calls


def test_refresh_creates_the_warehouse_when_there_is_none(tmp_path, fake_fetch):
    """The `existing is None` branch, plus the makedirs of a missing parent."""
    path = tmp_path / "nested" / "historical.parquet"

    result = prices.refresh(["AAPL", "005930.KS"], str(path), delay_factor=0)

    assert path.exists()
    assert [c[0] for c in fake_fetch] == ["AAPL", "005930.KS"]
    assert [c[1] for c in fake_fetch] == ["US", "KR"]  # region_for, per symbol
    stored = pd.read_parquet(path)
    assert set(stored["symbol"]) == {"AAPL", "005930.KS"}
    assert len(result) == len(stored) == 2


def test_refresh_merges_into_an_existing_warehouse(tmp_path, fake_fetch):
    """An unrelated stored row survives; a re-fetched one is replaced, not doubled."""
    path = tmp_path / "historical.parquet"
    pd.concat(
        [
            _fetched("MSFT", "US", "2026-09-02", 400.0, updated_at="2026-09-01"),
            _fetched("AAPL", "US", "2026-09-02", 1.0, updated_at="2026-09-01"),
        ],
        ignore_index=True,
    ).to_parquet(path, index=False)

    result = prices.refresh(["AAPL"], str(path), delay_factor=0)

    stored = pd.read_parquet(path)
    assert sorted(stored["symbol"]) == ["AAPL", "MSFT"]
    aapl = stored[stored["symbol"] == "AAPL"]
    assert len(aapl) == 1
    assert float(aapl.iloc[0]["close"]) == 101.0  # the freshly fetched close
    assert len(result) == 2


def test_refresh_without_symbols_and_without_a_warehouse_raises(tmp_path, fake_fetch):
    with pytest.raises(ValueError, match="No symbols to refresh"):
        prices.refresh([], str(tmp_path / "historical.parquet"), delay_factor=0)
    assert fake_fetch == []


def test_refresh_spaces_out_its_yfinance_calls(tmp_path, fake_fetch, monkeypatch):
    """A 30-ticker account used to make 30 back-to-back yfinance calls per sync.

    The parent's own bulk fetcher sleeps between symbols; this asserts the
    equivalent, and that the wait comes between calls rather than before the
    first or after the last.
    """
    slept = []
    monkeypatch.setattr("time.sleep", lambda seconds: slept.append(seconds))

    prices.refresh(["AAPL", "MSFT", "005930.KS"], str(tmp_path / "h.parquet"))

    assert len(slept) == 2  # three symbols, two gaps
    assert all(0 <= s <= prices.DEFAULT_DELAY_FACTOR for s in slept)


def test_refresh_can_be_told_not_to_wait(tmp_path, fake_fetch, monkeypatch):
    slept = []
    monkeypatch.setattr("time.sleep", lambda seconds: slept.append(seconds))

    prices.refresh(["AAPL", "MSFT"], str(tmp_path / "h.parquet"), delay_factor=0)

    assert slept == []


def test_refresh_asks_for_the_documented_period(tmp_path, fake_fetch):
    """README's 5y cap is a real constraint on how old a seed_date may be."""
    prices.refresh(["AAPL"], str(tmp_path / "h.parquet"), delay_factor=0)
    assert fake_fetch[0][2] == prices.FETCH_PERIOD == "5y"
