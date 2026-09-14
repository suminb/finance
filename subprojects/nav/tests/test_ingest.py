from datetime import datetime, timezone
from decimal import Decimal

import pytest

from finance.providers.miraeasset import Miraeasset
from nav import categories, ingest, symbols

SAMPLE = "subprojects/nav/tests/samples/miraeasset_0650_sample.csv"

SYMBOLS_YAML = """
- {name: 애플, ticker: AAPL, currency: USD}
- {name: 삼성전자보통주, ticker: 005930.KS, currency: KRW}
"""

CATEGORIES_YAML = """
- {category: 현금매수, handler: buy}
- {category: 배당금, handler: dividend}
- {category: 출금, handler: cash_out}
"""


@pytest.fixture
def maps(tmp_path):
    s = tmp_path / "symbols.yaml"
    s.write_text(SYMBOLS_YAML, encoding="utf-8")
    c = tmp_path / "categories.yaml"
    c.write_text(CATEGORIES_YAML, encoding="utf-8")
    return symbols.load(str(s)), categories.load(str(c))


def normalized(maps):
    symbol_map, category_map = maps
    records = Miraeasset().read_records(SAMPLE)
    return ingest.normalize(records, symbol_map, category_map)


def test_normalizes_every_row(maps):
    assert len(normalized(maps)) == 4


def test_resolves_ticker_and_keeps_currency(maps):
    first = normalized(maps)[0]
    assert first.ticker == "AAPL"
    assert first.currency == "USD"
    assert first.amount == Decimal("1500.00")


def test_rows_without_a_symbol_have_an_empty_ticker(maps):
    withdrawal = [t for t in normalized(maps) if t.category == "출금"][0]
    assert withdrawal.ticker == ""
    assert withdrawal.name == ""


def test_dates_are_utc_aware(maps):
    assert normalized(maps)[0].date.tzinfo is timezone.utc


def test_unmapped_symbol_raises_before_any_row_is_written(tmp_path):
    s = tmp_path / "symbols.yaml"
    s.write_text("- {name: 애플, ticker: AAPL, currency: USD}\n", encoding="utf-8")
    c = tmp_path / "categories.yaml"
    c.write_text(CATEGORIES_YAML, encoding="utf-8")
    with pytest.raises(symbols.UnknownSymbolError) as excinfo:
        ingest.normalize(
            Miraeasset().read_records(SAMPLE), symbols.load(str(s)), categories.load(str(c))
        )
    assert excinfo.value.names == ["삼성전자보통주"]


def test_unmapped_category_raises(tmp_path):
    s = tmp_path / "symbols.yaml"
    s.write_text(SYMBOLS_YAML, encoding="utf-8")
    c = tmp_path / "categories.yaml"
    c.write_text("- {category: 현금매수, handler: buy}\n", encoding="utf-8")
    with pytest.raises(categories.UnknownCategoryError) as excinfo:
        ingest.normalize(
            Miraeasset().read_records(SAMPLE), symbols.load(str(s)), categories.load(str(c))
        )
    assert excinfo.value.categories == ["배당금", "출금"]


def test_frame_round_trip_preserves_decimals(maps):
    transactions = normalized(maps)
    assert ingest.from_frame(ingest.to_frame(transactions)) == transactions


def test_merge_is_idempotent(maps):
    frame = ingest.to_frame(normalized(maps))
    assert len(ingest.merge(frame, frame)) == len(frame)


def test_merge_keeps_the_newer_row_for_a_duplicate_key(maps):
    frame = ingest.to_frame(normalized(maps))
    updated = frame.copy()
    updated.loc[0, "category"] = "정정된거래"
    merged = ingest.merge(frame, updated)
    assert len(merged) == len(frame)
    assert "정정된거래" in set(merged["category"])


def test_merge_accepts_no_existing_frame(maps):
    frame = ingest.to_frame(normalized(maps))
    assert len(ingest.merge(None, frame)) == len(frame)


def test_save_and_load_round_trip(maps, tmp_path):
    path = tmp_path / "transaction.parquet"
    frame = ingest.to_frame(normalized(maps))
    ingest.save_frame(frame, str(path))
    assert ingest.from_frame(ingest.load_frame(str(path))) == ingest.from_frame(frame)


def test_load_frame_returns_none_when_absent(tmp_path):
    assert ingest.load_frame(str(tmp_path / "nope.parquet")) is None
