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


def _write_export(path, rows):
    """Writes a euc-kr 0650 export with the sample's real 25-column header."""
    with open(SAMPLE, encoding="euc-kr") as fin:
        header = fin.readline().rstrip("\n")
    path.write_text(
        "\n".join([header] + list(rows)) + "\n", encoding="euc-kr"
    )
    return str(path)


# A 환전 pair: KRW out and USD in, emitted as two rows under ONE 거래번호.
# README §3 describes exactly this two-row shape, and whether real 미래에셋
# exports give the legs distinct 거래번호 is unknown -- which is why a shared
# key has to be loud rather than guessed at.
FX_PAIR_ROWS = [
    '2026/09/05,7,출금,환전출금,KRW,"1,300,000","1,300,000",0,,,0,0,0,0,'
    "0,0,,110000,HTS,,,,,,",
    '2026/09/05,7,입금,환전입금,USD,"1,000.00","1,000.00",0,,,0,0,0,0,'
    "0,0,,110000,HTS,,,,,,",
]


def test_two_rows_of_one_export_sharing_a_key_is_a_hard_error(maps, tmp_path):
    """The colliding-key data loss: 2 rows in, 1 row out, no error.

    Before this check, merge's drop_duplicates(keep="last") kept only the USD
    leg and the ₩1,300,000 KRW leg vanished -- "2 rows read, 1 new, 1 total",
    exit 0, every later NAV figure wrong. A repeat within one export can only
    be a key-model violation, so it must abort the import.
    """
    symbol_map, _ = maps
    category_map = categories.CategoryMap(
        [{"category": "출금", "handler": "cash_out"},
         {"category": "입금", "handler": "cash_in"}]
    )
    path = _write_export(tmp_path / "fx.csv", FX_PAIR_ROWS)

    with pytest.raises(ingest.DuplicateKeyError) as excinfo:
        ingest.normalize(
            Miraeasset().read_records(path), symbol_map, category_map, source=path
        )

    assert [seq for _, seq in excinfo.value.keys] == [7]
    assert "거래번호" in str(excinfo.value)
    assert path in str(excinfo.value)


def test_distinct_keys_in_one_export_are_accepted(maps, tmp_path):
    """The same 환전 pair with distinct 거래번호 imports as two rows.

    Guards against the check rejecting the legitimate shape too: only the
    shared key is the error, not the pair itself.
    """
    symbol_map, _ = maps
    category_map = categories.CategoryMap(
        [{"category": "출금", "handler": "cash_out"},
         {"category": "입금", "handler": "cash_in"}]
    )
    rows = [FX_PAIR_ROWS[0], FX_PAIR_ROWS[1].replace("2026/09/05,7,", "2026/09/05,8,")]
    path = _write_export(tmp_path / "fx-ok.csv", rows)

    transactions = ingest.normalize(
        Miraeasset().read_records(path), symbol_map, category_map, source=path
    )

    assert [t.seq for t in transactions] == [7, 8]
    assert len(ingest.merge(None, ingest.to_frame(transactions))) == 2


def test_merge_is_idempotent(maps):
    """Re-importing the same file stays a no-op.

    This is the behaviour the within-export duplicate check must NOT be
    conflated with: a key repeated across imports is idempotency and stays
    silent, a key repeated inside one export is data loss and raises.
    """
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
