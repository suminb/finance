# NAV Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Track the daily net asset value of a 미래에셋증권 account — KR/US stock holdings plus KRW/USD cash — and report it in both currencies.

**Architecture:** 거래내역 (0650) CSV exports are replayed into a daily inventory starting from a hand-written 잔고 seed, then priced from the parent repo's parquet warehouse. Generic portfolio math lives upstream in `finance/ext/models.py`; the subproject owns 미래에셋-specific ingest, the 거래종류 taxonomy, the CLI, and a self-contained HTML report.

**Tech Stack:** Python 3.9+, click, pandas, pyarrow, PyYAML, rich, yfinance (via `finance.ext.warehouse`), pytest.

**Spec:** `subprojects/nav/README.md`

## Global Constraints

- Base currency for all internal math is **KRW**. `nav_usd` is derived as `nav_krw / fx_usdkrw`.
- Cash is an inventory entry with an underscore-prefixed pseudo-ticker: `_KRW`, `_USD`, `_JPY`. This extends the existing `_USD` convention in `finance/ext/models.py`.
- Prices handed to `Portfolio` are **already converted to the base currency**. `Portfolio` performs no FX.
- An unmapped 종목명, an unmapped 거래종류, or an unknown handler name is a **hard error**. Never skip, never guess, never default.
- Table, file, and dataframe names are **singular**: `transaction.parquet`, not `transactions.parquet`.
- Python 3.9 compatible: use `Optional[X]` and `Dict[K, V]`-style builtin generics (`dict[str, float]` is fine at runtime in 3.9); do **not** use `X | Y` union syntax.
- Tests run from the repo root with `PYTHONPATH=.` (matching `.github/workflows`).
- Every commit message ends with the line `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- Never commit `seed.yaml`, `imports/`, or `data/` — they hold real balances.

## File Structure

| File | Responsibility |
| --- | --- |
| `subprojects/nav/pyproject.toml` | Package metadata, `nav` console script. |
| `subprojects/nav/.gitignore` | Excludes real financial data. |
| `subprojects/nav/nav/cli.py` | click command group. Thin; delegates everything. |
| `subprojects/nav/nav/probe.py` | Raw-CSV format discovery for `nav categories`. No dependency on the parser. |
| `subprojects/nav/nav/model.py` | Shared value types: `Transaction`, `Leg`, `cash_ticker`. |
| `subprojects/nav/nav/symbols.py` | `symbols.yaml` loading, 종목명 → (ticker, currency). |
| `subprojects/nav/nav/categories.py` | `categories.yaml` loading, 거래종류 → handler, handler implementations. |
| `subprojects/nav/nav/ingest.py` | 0650 CSV → normalized `transaction.parquet`. |
| `subprojects/nav/nav/seed.py` | `seed.yaml` loading and validation. |
| `subprojects/nav/nav/replay.py` | seed + transactions → `Portfolio` with legs. |
| `subprojects/nav/nav/prices.py` | Warehouse access, FX symbols, base-currency price table with carry-forward. |
| `subprojects/nav/nav/valuation.py` | Daily NAV series → `nav_daily.parquet`. |
| `subprojects/nav/nav/display.py` | Terminal rendering for `nav show`. |
| `subprojects/nav/nav/report.py` | Self-contained HTML. |
| `subprojects/nav/nav/check.py` | Reconciliation and corporate-action detection. |
| `finance/providers/record.py` | **Modify:** comma-tolerant numeric fields. |
| `finance/providers/miraeasset.py` | **Modify:** fractional quantity. |
| `finance/ext/models.py` | **Modify:** generalized cash tickers, `eval_nav`, daily NAV series. |

---

### Task 1: Subproject scaffolding and `nav categories`

Discovery task. `nav categories` reads the CSV with the stdlib only — deliberately **not** through `finance.providers.miraeasset` — so it works even if the existing parser chokes on the real file. Its output drives Tasks 3 and 4.

**Files:**
- Create: `subprojects/nav/pyproject.toml`
- Create: `subprojects/nav/.gitignore`
- Create: `subprojects/nav/nav/__init__.py`
- Create: `subprojects/nav/nav/probe.py`
- Create: `subprojects/nav/nav/cli.py`
- Create: `subprojects/nav/tests/__init__.py`
- Create: `subprojects/nav/tests/samples/miraeasset_0650_sample.csv`
- Test: `subprojects/nav/tests/test_probe.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `probe.read_rows(path) -> tuple[list[str], list[list[str]]]` returning `(headers, rows)`; `probe.summarize_categories(headers, rows) -> list[CategorySummary]` where `CategorySummary` is a dataclass with fields `category: str`, `count: int`, `sample: dict[str, str]`; `probe.format_report(headers, rows) -> str`.

- [ ] **Step 1: Create the sample fixture**

The real 0650 export is euc-kr with 25 columns. The existing parser only addresses ten of them by name, so the fixture carries those ten plus filler columns at realistic positions. Numbers include thousands separators, which is what Korean brokerage exports typically emit.

Create `subprojects/nav/tests/samples/miraeasset_0650_sample.csv`, encoded **euc-kr**:

```
거래일자,거래번호,거래종류,적요명,통화코드,거래금액,정산금액,예수금잔고,종목번호,종목명,수량,단가,수수료,제세금합,연체이자,변제금액,대출일자,처리시각,매체구분,상대계좌,상대성명,비고1,비고2,비고3,비고4
2026/09/01,1,현금매수,주식매수,USD,"1,500.00","1,503.50",0,AAPL,애플,10,150.00,3.50,0.00,0,0,,090131,HTS,,,,,,
2026/09/02,1,배당금,배당금입금,USD,"12.30","10.46",0,AAPL,애플,0,0,0.00,1.84,0,0,,090500,HTS,,,,,,
2026/09/03,1,현금매수,주식매수,KRW,"7,100,000","7,101,065",0,005930,삼성전자보통주,100,71000,1065,0,0,0,,091500,HTS,,,,,,
2026/09/04,1,출금,외화출금,KRW,"1,000,000","1,000,000",0,,,0,0,0,0,0,0,,100000,HTS,,,,,,
```

Write it with Python so the encoding is unambiguous:

```python
import pathlib
rows = [
    "거래일자,거래번호,거래종류,적요명,통화코드,거래금액,정산금액,예수금잔고,종목번호,종목명,수량,단가,수수료,제세금합,연체이자,변제금액,대출일자,처리시각,매체구분,상대계좌,상대성명,비고1,비고2,비고3,비고4",
    '2026/09/01,1,현금매수,주식매수,USD,"1,500.00","1,503.50",0,AAPL,애플,10,150.00,3.50,0.00,0,0,,090131,HTS,,,,,,',
    '2026/09/02,1,배당금,배당금입금,USD,"12.30","10.46",0,AAPL,애플,0,0,0.00,1.84,0,0,,090500,HTS,,,,,,',
    '2026/09/03,1,현금매수,주식매수,KRW,"7,100,000","7,101,065",0,005930,삼성전자보통주,100,71000,1065,0,0,0,,091500,HTS,,,,,,',
    '2026/09/04,1,출금,외화출금,KRW,"1,000,000","1,000,000",0,,,0,0,0,0,0,0,,100000,HTS,,,,,,',
]
p = pathlib.Path("subprojects/nav/tests/samples/miraeasset_0650_sample.csv")
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text("\n".join(rows) + "\n", encoding="euc-kr")
```

- [ ] **Step 2: Write the failing test**

Create `subprojects/nav/tests/test_probe.py`:

```python
from nav import probe

SAMPLE = "subprojects/nav/tests/samples/miraeasset_0650_sample.csv"


def test_read_rows_returns_25_columns():
    headers, rows = probe.read_rows(SAMPLE)
    assert len(headers) == 25
    assert headers[0] == "거래일자"
    assert len(rows) == 4
    assert all(len(r) == 25 for r in rows)


def test_read_rows_preserves_quoted_commas():
    _, rows = probe.read_rows(SAMPLE)
    assert rows[0][5] == "1,500.00"


def test_summarize_categories_counts_and_samples():
    headers, rows = probe.read_rows(SAMPLE)
    summaries = probe.summarize_categories(headers, rows)
    by_name = {s.category: s for s in summaries}
    assert by_name["현금매수"].count == 2
    assert by_name["배당금"].count == 1
    assert by_name["출금"].count == 1
    assert by_name["현금매수"].sample["종목명"] == "애플"


def test_summarize_categories_sorted_by_count_desc():
    headers, rows = probe.read_rows(SAMPLE)
    counts = [s.count for s in probe.summarize_categories(headers, rows)]
    assert counts == sorted(counts, reverse=True)


def test_format_report_flags_thousands_separators():
    headers, rows = probe.read_rows(SAMPLE)
    report = probe.format_report(headers, rows)
    assert "거래금액" in report
    assert "thousands separators" in report


def test_format_report_lists_distinct_symbol_names():
    headers, rows = probe.read_rows(SAMPLE)
    report = probe.format_report(headers, rows)
    assert "애플" in report
    assert "삼성전자보통주" in report
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_probe.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nav'`

- [ ] **Step 4: Create the package scaffolding**

`subprojects/nav/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "nav"
version = "0.1.0"
description = "Daily net asset value tracking for a 미래에셋증권 account"
requires-python = ">=3.9"
dependencies = [
    "click>=8.0,<9.0",
    "pandas>=2.0.0",
    "pyarrow>=10.0",
    "PyYAML>=6.0,<6.1",
    "rich>=13.6,<14.0",
]

[project.scripts]
nav = "nav.cli:cli"

[tool.setuptools.packages.find]
include = ["nav*"]
```

`subprojects/nav/.gitignore`:

```
seed.yaml
imports/
data/
nav.html
```

`subprojects/nav/nav/__init__.py`:

```python
"""Daily net asset value tracking for a 미래에셋증권 account."""

__version__ = "0.1.0"
```

`subprojects/nav/tests/__init__.py`: empty file.

- [ ] **Step 5: Implement `probe.py`**

```python
"""Format discovery for 미래에셋 거래내역조회 (0650) exports.

This module reads the raw CSV with the standard library only. It deliberately
avoids finance.providers.miraeasset so that it still works when the export
does not match that parser's expectations -- finding out how the export is
actually shaped is the whole point.
"""

import codecs
import csv
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Tuple

DEFAULT_ENCODING = "euc-kr"
CATEGORY_COLUMN = "거래종류"
NAME_COLUMN = "종목명"


@dataclass
class CategorySummary:
    category: str
    count: int
    sample: Dict[str, str]


def read_rows(path: str, encoding: str = DEFAULT_ENCODING) -> Tuple[List[str], List[List[str]]]:
    """Reads a 0650 export into a header list and a list of row lists."""
    with codecs.open(path, "r", encoding=encoding) as fin:
        reader = csv.reader(fin)
        headers = [h.strip() for h in next(reader)]
        rows = [[c.strip() for c in row] for row in reader if any(c.strip() for c in row)]
    return headers, rows


def summarize_categories(headers: List[str], rows: List[List[str]]) -> List[CategorySummary]:
    """Counts distinct 거래종류 values, keeping one sample row for each."""
    index = headers.index(CATEGORY_COLUMN)
    counts: Counter = Counter(row[index] for row in rows)
    samples: Dict[str, Dict[str, str]] = {}
    for row in rows:
        samples.setdefault(row[index], dict(zip(headers, row)))
    return [
        CategorySummary(category=category, count=count, sample=samples[category])
        for category, count in counts.most_common()
    ]


def _looks_numeric(value: str) -> bool:
    stripped = value.replace(",", "").replace("-", "").replace(".", "")
    return bool(stripped) and stripped.isdigit()


def format_report(headers: List[str], rows: List[List[str]]) -> str:
    """Renders everything Tasks 3 and 4 need in order to write the YAML files."""
    lines = [
        f"columns: {len(headers)}",
        f"rows: {len(rows)}",
        "",
        "== 거래종류 ==",
    ]
    for summary in summarize_categories(headers, rows):
        lines.append(f"  {summary.category}  x{summary.count}")
        for key in (NAME_COLUMN, "통화코드", "거래금액", "수량", "단가", "수수료", "제세금합"):
            if key in summary.sample:
                lines.append(f"      {key}: {summary.sample[key]!r}")

    comma_columns = sorted(
        {
            headers[i]
            for row in rows
            for i in range(len(row))
            if "," in row[i] and _looks_numeric(row[i])
        }
    )
    fractional_columns = sorted(
        {
            headers[i]
            for row in rows
            for i in range(len(row))
            if "." in row[i] and _looks_numeric(row[i])
        }
    )

    lines += ["", "== numeric formats =="]
    lines.append(
        "  thousands separators: " + (", ".join(comma_columns) if comma_columns else "(none)")
    )
    lines.append(
        "  fractional values: " + (", ".join(fractional_columns) if fractional_columns else "(none)")
    )

    if NAME_COLUMN in headers:
        name_index = headers.index(NAME_COLUMN)
        names = sorted({row[name_index] for row in rows if row[name_index]})
        lines += ["", "== 종목명 =="]
        lines += [f"  {name}" for name in names]

    return "\n".join(lines)
```

- [ ] **Step 6: Implement the CLI**

`subprojects/nav/nav/cli.py`:

```python
"""Command line interface for nav."""

import click


@click.group()
def cli():
    """Daily net asset value tracking."""


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--encoding", default="euc-kr", show_default=True)
def categories(path: str, encoding: str):
    """Print the 거래종류 vocabulary and numeric formats of a 0650 export."""
    from nav import probe

    headers, rows = probe.read_rows(path, encoding=encoding)
    click.echo(probe.format_report(headers, rows))


if __name__ == "__main__":
    cli()
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_probe.py -v`
Expected: 6 passed

- [ ] **Step 8: Verify the CLI installs and runs**

```bash
pip install -e subprojects/nav
nav categories subprojects/nav/tests/samples/miraeasset_0650_sample.csv
```

Expected: a report listing `현금매수 x2`, `배당금 x1`, `출금 x1`, and `thousands separators: 거래금액, 정산금액`.

- [ ] **Step 9: Commit**

```bash
git add subprojects/nav/pyproject.toml subprojects/nav/.gitignore \
        subprojects/nav/nav subprojects/nav/tests
git commit -m "$(cat <<'EOF'
feat(nav): Scaffold subproject and add `nav categories`

Reads a 0650 export with the standard library only, so format discovery
works even when finance.providers.miraeasset cannot parse the file.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 10: HUMAN CHECKPOINT — run against a real export**

Ask the account holder to export 거래내역조회 (0650) covering at least the last
twelve months, drop it at `subprojects/nav/imports/`, and run:

```bash
nav categories subprojects/nav/imports/<the-file>.csv
```

Record the output. Tasks 3 and 4 are written from it — the real 거래종류
vocabulary and the real 종목명 spellings cannot be guessed. Do not proceed to
Task 3 without this output.

If `read_rows` raises or the column count is not 25, capture the error and the
first two lines of the file; the fixture and `probe.read_rows` need adjusting
before anything downstream is built.

---

### Task 2: Make the existing parser tolerate real numeric formats

Korean brokerage exports thousands-separate their numbers, and 미래에셋 supports
fractional overseas shares. The existing field descriptors handle neither:
`Decimal("1,500.00")` raises `InvalidOperation` and `Integer()` cannot hold
`0.5` shares.

Both changes are strictly more permissive — no existing input stops working.

**Files:**
- Modify: `finance/providers/record.py`
- Modify: `finance/providers/miraeasset.py`
- Test: `tests/providers/test_record.py`
- Test: `tests/providers/test_miraeasset.py`

**Interfaces:**
- Consumes: `nav/tests/samples/miraeasset_0650_sample.csv` from Task 1.
- Produces: `finance.providers.miraeasset.Miraeasset().read_records(path)` yielding `Record` objects whose `amount`, `unit_price`, `quantity`, `fees` and `tax` are `decimal.Decimal`, parsed correctly from comma-separated strings.

- [ ] **Step 1: Write the failing tests**

Create `tests/providers/__init__.py` (empty) and `tests/providers/test_record.py`:

```python
import decimal

import pytest

from finance.providers.record import Decimal as DecimalField
from finance.providers.record import Integer as IntegerField


class Holder:
    amount = DecimalField()
    count = IntegerField()


def test_decimal_field_accepts_thousands_separators():
    h = Holder()
    h.amount = "1,500.00"
    assert h.amount == decimal.Decimal("1500.00")


def test_decimal_field_accepts_plain_values():
    h = Holder()
    h.amount = "42.5"
    assert h.amount == decimal.Decimal("42.5")


def test_decimal_field_accepts_numeric_types():
    h = Holder()
    h.amount = 7
    assert h.amount == decimal.Decimal(7)


def test_decimal_field_treats_blank_as_zero():
    h = Holder()
    h.amount = ""
    assert h.amount == decimal.Decimal(0)


def test_integer_field_accepts_thousands_separators():
    h = Holder()
    h.count = "1,200"
    assert h.count == 1200


def test_integer_field_rejects_garbage():
    h = Holder()
    with pytest.raises(decimal.InvalidOperation):
        h.count = "abc"
```

Create `tests/providers/test_miraeasset.py`:

```python
import decimal

from finance.providers.miraeasset import Miraeasset

SAMPLE = "subprojects/nav/tests/samples/miraeasset_0650_sample.csv"


def records():
    return list(Miraeasset().read_records(SAMPLE))


def test_reads_every_row():
    assert len(records()) == 4


def test_parses_comma_separated_amount():
    assert records()[0].amount == decimal.Decimal("1500.00")


def test_parses_fractional_quantity():
    rs = records()
    assert rs[0].quantity == decimal.Decimal(10)
    assert isinstance(rs[0].quantity, decimal.Decimal)


def test_parses_category_and_currency():
    r = records()[0]
    assert r.category == "현금매수"
    assert r.currency == "USD"


def test_parses_date():
    assert records()[0].created_at.strftime("%Y-%m-%d") == "2026-09-01"


def test_keeps_raw_columns():
    assert len(records()[0].raw_columns) == 25
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=. pytest tests/providers -v`
Expected: FAIL — `decimal.InvalidOperation` on the comma tests, and `test_parses_fractional_quantity` fails because `quantity` is an `int`.

- [ ] **Step 3: Make the numeric fields comma-tolerant**

In `finance/providers/record.py`, replace the `Decimal` and `Integer` classes:

```python
def _clean_number(value):
    """Normalizes a numeric string as it appears in brokerage exports.

    Thousands separators and surrounding whitespace are stripped, and an empty
    value is treated as zero -- exports leave numeric cells blank rather than
    writing a zero.
    """
    if isinstance(value, str):
        value = value.strip().replace(",", "")
        if not value:
            return "0"
    return value


class Decimal(AbstractField):
    def __set__(self, instance, value):
        self._values[instance] = decimal.Decimal(_clean_number(value))


class Integer(AbstractField):
    def __set__(self, instance, value):
        self._values[instance] = int(decimal.Decimal(_clean_number(value)))
```

`Integer` routes through `Decimal` so that `"1,200"` and `"1200.0"` both work
and garbage raises `decimal.InvalidOperation` rather than `ValueError`.

- [ ] **Step 4: Parse the CSV with `csv.reader` and allow fractional quantities**

`parse_records` currently splits each line with `line.strip().split(",")`,
which cannot survive a quoted field: `"1,500.00"` becomes two columns and the
25-column assertion fails. Replace the hand-rolled splitting with the `csv`
module.

In `finance/providers/miraeasset.py`, add `import csv` at the top and replace
the body of `parse_records` down to the `for line in fin:` loop header:

```python
    def parse_records(self, fin):
        """거래내역조회 (0650)"""
        reader = csv.reader(fin)
        headers = [h.strip() for h in next(reader)]

        col_count = len(headers)
        assert col_count == 25, "Invalid column count ({})".format(col_count)

        column_indices = self.find_header_column_indices(headers)

        for row in reader:
            columns = [x.strip() for x in row]
            if not any(columns):
                continue
            assert len(columns) == col_count, "Invalid column count ({})".format(
                len(columns)
            )
```

The rest of the loop body is unchanged.

In the same file, change the `quantity` descriptor on `Record` from `Integer()`
to `Decimal()`:

```python
    quantity = Decimal()
```

`Decimal` is already imported there. Fractional overseas shares are supported
by 미래에셋, and an `int` silently truncating 0.5 shares would corrupt the
inventory. `Integer` stays imported for `seq`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `PYTHONPATH=. pytest tests/providers -v`
Expected: 12 passed

- [ ] **Step 6: Verify nothing else regressed**

Run: `PYTHONPATH=. pytest tests -v`
Expected: no new failures compared to the run before this task. Tests skipped
for missing parquet data files stay skipped.

- [ ] **Step 7: Commit**

```bash
git add finance/providers/record.py finance/providers/miraeasset.py tests/providers
git commit -m "$(cat <<'EOF'
fix(providers): Parse quoted, comma-separated and fractional numbers

Korean brokerage exports thousands-separate their numbers, so
Decimal("1,500.00") raised InvalidOperation -- and the hand-rolled
line.split(",") broke the column count before it even got that far.
미래에셋 also supports fractional overseas shares, which an Integer
quantity truncated.

All three changes are strictly more permissive; no previously valid
input parses differently.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Symbol resolution

**Files:**
- Create: `subprojects/nav/nav/symbols.py`
- Create: `subprojects/nav/symbols.yaml`
- Test: `subprojects/nav/tests/test_symbols.py`

**Interfaces:**
- Consumes: the 종목명 list printed by `nav categories` in Task 1.
- Produces: `symbols.Symbol` (frozen dataclass, fields `name: str`, `ticker: str`, `currency: str`); `symbols.load(path) -> SymbolMap`; `SymbolMap.resolve(name) -> Symbol` raising `UnknownSymbolError`; `SymbolMap.resolve_all(names) -> dict[str, Symbol]` raising once for all misses; `SymbolMap.currency_of(ticker) -> str`; `symbols.UnknownSymbolError` with a `.names` list and a `.stub` YAML string.

- [ ] **Step 1: Write the failing test**

Create `subprojects/nav/tests/test_symbols.py`:

```python
import pytest

from nav import symbols

YAML = """
- {name: 애플, ticker: AAPL, currency: USD}
- {name: Advanced Micro Devic, ticker: AMD, currency: USD}
- {name: AMD, ticker: AMD, currency: USD}
- {name: 삼성전자보통주, ticker: 005930.KS, currency: KRW}
"""


@pytest.fixture
def symbol_map(tmp_path):
    path = tmp_path / "symbols.yaml"
    path.write_text(YAML, encoding="utf-8")
    return symbols.load(str(path))


def test_resolves_a_known_name(symbol_map):
    assert symbol_map.resolve("애플").ticker == "AAPL"
    assert symbol_map.resolve("애플").currency == "USD"


def test_many_names_map_to_one_ticker(symbol_map):
    assert symbol_map.resolve("AMD").ticker == "AMD"
    assert symbol_map.resolve("Advanced Micro Devic").ticker == "AMD"


def test_unknown_name_raises(symbol_map):
    with pytest.raises(symbols.UnknownSymbolError):
        symbol_map.resolve("없는종목")


def test_resolve_all_reports_every_miss_at_once(symbol_map):
    with pytest.raises(symbols.UnknownSymbolError) as excinfo:
        symbol_map.resolve_all(["애플", "없는종목1", "없는종목2"])
    assert excinfo.value.names == ["없는종목1", "없는종목2"]


def test_error_carries_a_paste_ready_stub(symbol_map):
    with pytest.raises(symbols.UnknownSymbolError) as excinfo:
        symbol_map.resolve_all(["없는종목1"])
    assert "- {name: 없는종목1, ticker: ???, currency: ???}" in excinfo.value.stub


def test_currency_of_ticker(symbol_map):
    assert symbol_map.currency_of("005930.KS") == "KRW"


def test_conflicting_currency_for_one_ticker_is_rejected(tmp_path):
    path = tmp_path / "symbols.yaml"
    path.write_text(
        "- {name: A, ticker: X, currency: USD}\n- {name: B, ticker: X, currency: KRW}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="conflicting currency"):
        symbols.load(str(path))


def test_shipped_symbols_file_loads():
    symbols.load("subprojects/nav/symbols.yaml")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_symbols.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nav.symbols'`

- [ ] **Step 3: Implement `symbols.py`**

```python
"""Resolution of 미래에셋 종목명 to a ticker and a currency.

미래에셋 truncates 종목명 inconsistently between export vintages, so several
names legitimately map to one ticker. Nothing is inferred: a name that is not
listed is an error, because a NAV series that is silently wrong is worse than
one that refuses to build.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List

import yaml


@dataclass(frozen=True)
class Symbol:
    name: str
    ticker: str
    currency: str


class UnknownSymbolError(Exception):
    def __init__(self, names: List[str]):
        self.names = list(names)
        self.stub = "\n".join(
            "- {name: %s, ticker: ???, currency: ???}" % name for name in self.names
        )
        super().__init__(
            "Unmapped 종목명 ({}). Add to symbols.yaml:\n{}".format(
                len(self.names), self.stub
            )
        )


class SymbolMap:
    def __init__(self, symbols: Iterable[Symbol]):
        self._by_name: Dict[str, Symbol] = {}
        self._currency_by_ticker: Dict[str, str] = {}
        for symbol in symbols:
            self._by_name[symbol.name] = symbol
            existing = self._currency_by_ticker.get(symbol.ticker)
            if existing is not None and existing != symbol.currency:
                raise ValueError(
                    "conflicting currency for {}: {} and {}".format(
                        symbol.ticker, existing, symbol.currency
                    )
                )
            self._currency_by_ticker[symbol.ticker] = symbol.currency

    def resolve(self, name: str) -> Symbol:
        try:
            return self._by_name[name]
        except KeyError:
            raise UnknownSymbolError([name])

    def resolve_all(self, names: Iterable[str]) -> Dict[str, Symbol]:
        names = list(names)
        missing = sorted({n for n in names if n not in self._by_name})
        if missing:
            raise UnknownSymbolError(missing)
        return {n: self._by_name[n] for n in names}

    def currency_of(self, ticker: str) -> str:
        return self._currency_by_ticker[ticker]

    def tickers(self) -> List[str]:
        return sorted(self._currency_by_ticker)


def load(path: str) -> SymbolMap:
    with open(path, encoding="utf-8") as fin:
        entries = yaml.safe_load(fin) or []
    return SymbolMap(
        Symbol(name=e["name"], ticker=e["ticker"], currency=e["currency"])
        for e in entries
    )
```

- [ ] **Step 4: Generate the initial `symbols.yaml`**

Seed it from the mappings already accumulated in
`finance/providers/miraeasset.py`, assigning currency by ticker suffix. Run
this once from the repo root:

```python
import io
from finance.providers.miraeasset import name_code_mappings

def currency_for(ticker):
    if ticker.endswith((".KS", ".KQ")):
        return "KRW"
    if ticker.endswith(".T"):
        return "JPY"
    return "USD"

lines = ["# 종목명 -> ticker + currency.",
         "# Several names may map to one ticker: 미래에셋 truncates 종목명",
         "# inconsistently between export vintages.",
         "# Regenerate nothing by hand-editing blindly -- add entries as",
         "# `nav import` reports them."]
for name, ticker in sorted(name_code_mappings.items(), key=lambda kv: kv[1]):
    lines.append("- {name: %s, ticker: %s, currency: %s}" % (name, ticker, currency_for(ticker)))

with io.open("subprojects/nav/symbols.yaml", "w", encoding="utf-8") as fout:
    fout.write("\n".join(lines) + "\n")
```

Then reconcile against the 종목명 list from the Task 1 human checkpoint: add an
entry for every name that appeared in the real export and is not already
present. Delete the `Berkshire Hathaway I` entry unless the account holder
confirms it is BRK-B rather than BRK-A — the existing code flags that mapping
as a dangerous assumption, and this is the moment to resolve it.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_symbols.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add subprojects/nav/nav/symbols.py subprojects/nav/symbols.yaml \
        subprojects/nav/tests/test_symbols.py
git commit -m "$(cat <<'EOF'
feat(nav): Resolve 종목명 to ticker and currency

Seeded from the mappings in finance/providers/miraeasset.py. An unmapped
name raises with a paste-ready YAML stub rather than falling back to a
placeholder code.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Transaction taxonomy and handlers

**Files:**
- Create: `subprojects/nav/nav/model.py`
- Create: `subprojects/nav/nav/categories.py`
- Create: `subprojects/nav/categories.yaml`
- Test: `subprojects/nav/tests/test_categories.py`

**Interfaces:**
- Consumes: the 거래종류 list printed by `nav categories` in Task 1.
- Produces: `model.Transaction` (frozen dataclass: `date: datetime`, `seq: int`, `category: str`, `name: str`, `ticker: str`, `currency: str`, `amount: Decimal`, `unit_price: Decimal`, `quantity: Decimal`, `fees: Decimal`, `tax: Decimal`, `raw: str`); `model.Leg` (frozen dataclass: `ticker: str`, `quantity: Decimal`); `model.cash_ticker(currency) -> str`; `categories.load(path) -> CategoryMap`; `CategoryMap.legs_for(transaction) -> list[Leg]`; `CategoryMap.validate(categories)`; `categories.UnknownCategoryError` with `.categories` and `.stub`; `categories.HANDLERS` dict.

- [ ] **Step 1: Write the failing test**

Create `subprojects/nav/tests/test_categories.py`:

```python
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from nav import categories
from nav.model import Leg, Transaction

YAML = """
- {category: 현금매수, handler: buy}
- {category: 현금매도, handler: sell}
- {category: 입금, handler: cash_in}
- {category: 출금, handler: cash_out}
- {category: 배당금, handler: dividend}
- {category: 기타, handler: noop}
"""


@pytest.fixture
def category_map(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text(YAML, encoding="utf-8")
    return categories.load(str(path))


def make(category, **kwargs):
    defaults = dict(
        date=datetime(2026, 9, 1, tzinfo=timezone.utc),
        seq=1,
        category=category,
        name="애플",
        ticker="AAPL",
        currency="USD",
        amount=Decimal("1500.00"),
        unit_price=Decimal("150.00"),
        quantity=Decimal("10"),
        fees=Decimal("3.50"),
        tax=Decimal("0"),
        raw="[]",
    )
    defaults.update(kwargs)
    return Transaction(**defaults)


def test_buy_adds_shares_and_debits_cash(category_map):
    legs = category_map.legs_for(make("현금매수"))
    assert legs == [
        Leg("AAPL", Decimal("10")),
        Leg("_USD", Decimal("-1503.50")),
    ]


def test_sell_removes_shares_and_credits_cash_net_of_costs(category_map):
    legs = category_map.legs_for(
        make("현금매도", tax=Decimal("2.00"))
    )
    assert legs == [
        Leg("AAPL", Decimal("-10")),
        Leg("_USD", Decimal("1494.50")),
    ]


def test_dividend_credits_cash_net_of_tax(category_map):
    legs = category_map.legs_for(
        make("배당금", amount=Decimal("12.30"), tax=Decimal("1.84"),
             quantity=Decimal("0"), ticker="AAPL")
    )
    assert legs == [Leg("_USD", Decimal("10.46"))]


def test_cash_in_and_out_use_the_row_currency(category_map):
    assert category_map.legs_for(
        make("입금", currency="KRW", amount=Decimal("1000000"), ticker="", name="")
    ) == [Leg("_KRW", Decimal("1000000"))]
    assert category_map.legs_for(
        make("출금", currency="KRW", amount=Decimal("1000000"), ticker="", name="")
    ) == [Leg("_KRW", Decimal("-1000000"))]


def test_noop_produces_no_legs(category_map):
    assert category_map.legs_for(make("기타")) == []


def test_unknown_category_raises_with_stub(category_map):
    with pytest.raises(categories.UnknownCategoryError) as excinfo:
        category_map.legs_for(make("권리락"))
    assert excinfo.value.categories == ["권리락"]
    assert "- {category: 권리락, handler: ???}" in excinfo.value.stub


def test_validate_reports_every_unknown_category_at_once(category_map):
    with pytest.raises(categories.UnknownCategoryError) as excinfo:
        category_map.validate(["현금매수", "권리락", "액면분할"])
    assert excinfo.value.categories == ["권리락", "액면분할"]


def test_unknown_handler_name_is_rejected_at_load(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text("- {category: X, handler: teleport}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown handler"):
        categories.load(str(path))


def test_buy_without_a_ticker_is_rejected(category_map):
    with pytest.raises(ValueError, match="requires a ticker"):
        category_map.legs_for(make("현금매수", ticker=""))


def test_shipped_categories_file_loads():
    categories.load("subprojects/nav/categories.yaml")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_categories.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nav.model'`

- [ ] **Step 3: Implement `model.py`**

```python
"""Shared value types for nav."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

CASH_PREFIX = "_"


@dataclass(frozen=True)
class Transaction:
    """One normalized line of a 거래내역조회 (0650) export."""

    date: datetime
    seq: int
    category: str
    name: str
    ticker: str
    currency: str
    amount: Decimal
    unit_price: Decimal
    quantity: Decimal
    fees: Decimal
    tax: Decimal
    raw: str


@dataclass(frozen=True)
class Leg:
    """A signed change to one inventory entry."""

    ticker: str
    quantity: Decimal


def cash_ticker(currency: str) -> str:
    """Pseudo-ticker under which cash of a currency is held.

    Extends the `_USD` convention already used by finance.ext.models.
    """
    return CASH_PREFIX + currency
```

- [ ] **Step 4: Implement `categories.py`**

```python
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
```

- [ ] **Step 5: Write `categories.yaml` from the real vocabulary**

Create `subprojects/nav/categories.yaml` using the 거래종류 values reported by
the Task 1 human checkpoint. Start from these, which cover the sample fixture,
then add one line per additional 거래종류 the real export produced:

```yaml
# 거래종류 -> handler. Handlers are defined in nav/categories.py:
#   buy, sell, cash_in, cash_out, dividend, interest, fee, noop
#
# 환전 appears as a pair of rows, one per currency: map the paying row to
# cash_out and the receiving row to cash_in.
- {category: 현금매수, handler: buy}
- {category: 현금매도, handler: sell}
- {category: 입금, handler: cash_in}
- {category: 출금, handler: cash_out}
- {category: 배당금, handler: dividend}
```

Every 거래종류 in the real export must appear. Deciding that a category has no
effect on the inventory is a legitimate outcome — map it to `noop` — but it
must be a decision recorded in the file, not an omission.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_categories.py -v`
Expected: 11 passed

- [ ] **Step 7: Commit**

```bash
git add subprojects/nav/nav/model.py subprojects/nav/nav/categories.py \
        subprojects/nav/categories.yaml subprojects/nav/tests/test_categories.py
git commit -m "$(cat <<'EOF'
feat(nav): Map 거래종류 to inventory movements

categories.yaml maps each Korean string to a named handler; the handlers
hold the arithmetic and are unit tested. Unmapped 거래종류 and unknown
handler names both raise.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Ingest 0650 exports into `transaction.parquet`

**Files:**
- Create: `subprojects/nav/nav/ingest.py`
- Modify: `subprojects/nav/nav/cli.py`
- Test: `subprojects/nav/tests/test_ingest.py`

**Interfaces:**
- Consumes: `Miraeasset.read_records` (Task 2), `SymbolMap` (Task 3), `CategoryMap` and `model.Transaction` (Task 4).
- Produces: `ingest.normalize(records, symbol_map, category_map) -> list[Transaction]`; `ingest.to_frame(transactions) -> pd.DataFrame`; `ingest.from_frame(df) -> list[Transaction]`; `ingest.merge(existing, new) -> pd.DataFrame`; `ingest.load_frame(path) -> Optional[pd.DataFrame]`; `ingest.save_frame(df, path)`; `ingest.COLUMNS` list.

Numeric columns are stored as **strings** in parquet and converted back to
`Decimal` on load. Money is exact in this pipeline; a float round-trip would
quietly reintroduce the imprecision the `Decimal` fields exist to avoid, and at
a few thousand rows the storage cost is irrelevant.

- [ ] **Step 1: Write the failing test**

Create `subprojects/nav/tests/test_ingest.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nav.ingest'`

- [ ] **Step 3: Implement `ingest.py`**

```python
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
```

- [ ] **Step 4: Add the `nav import` command**

Append to `subprojects/nav/nav/cli.py`, and add these shared options at the top
of the module after the imports:

```python
import os

DEFAULT_ROOT = os.environ.get("NAV_ROOT", "subprojects/nav")


def _paths(root):
    return {
        "symbols": os.path.join(root, "symbols.yaml"),
        "categories": os.path.join(root, "categories.yaml"),
        "seed": os.path.join(root, "seed.yaml"),
        "transaction": os.path.join(root, "data", "transaction.parquet"),
        "nav_daily": os.path.join(root, "data", "nav_daily.parquet"),
    }
```

Then the command:

```python
@cli.command(name="import")
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--root", default=DEFAULT_ROOT, show_default=True)
def import_(paths, root: str):
    """Parse 0650 exports into data/transaction.parquet."""
    from finance.providers.miraeasset import Miraeasset
    from nav import categories, ingest, symbols

    p = _paths(root)
    symbol_map = symbols.load(p["symbols"])
    category_map = categories.load(p["categories"])
    provider = Miraeasset()

    transactions = []
    for path in paths:
        transactions += ingest.normalize(
            provider.read_records(path), symbol_map, category_map
        )

    existing = ingest.load_frame(p["transaction"])
    before = 0 if existing is None else len(existing)
    merged = ingest.merge(existing, ingest.to_frame(transactions))
    ingest.save_frame(merged, p["transaction"])
    click.echo(
        "{} rows read, {} new, {} total".format(
            len(transactions), len(merged) - before, len(merged)
        )
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_ingest.py -v`
Expected: 12 passed

- [ ] **Step 6: Verify the command against the real export**

```bash
nav import subprojects/nav/imports/*.csv
nav import subprojects/nav/imports/*.csv   # second run must add 0 new rows
```

If either run raises `UnknownSymbolError` or `UnknownCategoryError`, paste the
stub from the error into `symbols.yaml` or `categories.yaml` and rerun. That
loop is the intended workflow, not a failure.

- [ ] **Step 7: Commit**

```bash
git add subprojects/nav/nav/ingest.py subprojects/nav/nav/cli.py \
        subprojects/nav/tests/test_ingest.py
git commit -m "$(cat <<'EOF'
feat(nav): Ingest 0650 exports into transaction.parquet

Resolution and validation run over the whole batch before anything is
written, so an unmapped 종목명 or 거래종류 reports every offender at once.
Deduplication on (date, seq) makes re-imports and overlapping exports
no-ops. Money is stored as strings and read back as Decimal.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Multi-currency cash and a NAV series in `Portfolio`

Upstream work in the parent package. All changes are additive; every existing
test in `tests/ext/test_ext_models.py` must still pass.

No FX code is added to `Portfolio`. Because `net_asset_value` is
`Σ current_prices[t] × quantity[t]`, supplying prices already expressed in the
base currency makes the existing arithmetic correct for a mixed-currency
inventory. FX conversion belongs in the price table (Task 8).

**Files:**
- Modify: `finance/ext/models.py`
- Modify: `finance/ext/exceptions.py`
- Test: `tests/ext/test_ext_models.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `finance.ext.models.is_cash(ticker) -> bool`; `Portfolio(current_prices, target_weights, transactions, base_currency="USD")` with attribute `cash_ticker`; `Portfolio.eval_nav(evaluated_at, prices) -> float`; `Portfolio.eval_daily_nav_series(from_date, to_date, prices_by_date) -> list[tuple[datetime, float]]`; `finance.ext.exceptions.MissingPriceException`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/ext/test_ext_models.py`:

```python
from datetime import datetime, timezone

from finance.ext.exceptions import MissingPriceException
from finance.ext.models import is_cash


def utc(year, month, day):
    return datetime(year, month, day, tzinfo=timezone.utc)


def test_is_cash_recognizes_underscore_prefixed_tickers():
    assert is_cash("_USD")
    assert is_cash("_KRW")
    assert not is_cash("SPY")


def test_default_base_currency_is_usd():
    assert Portfolio({}, {}, []).cash_ticker == "_USD"


def test_base_currency_selects_the_cash_ticker():
    assert Portfolio({}, {}, [], base_currency="KRW").cash_ticker == "_KRW"


def test_rebalancing_plan_excludes_every_cash_ticker():
    prices = {"SPY": 100.0, "_USD": 1.0, "_KRW": 1.0}
    pf = Portfolio(prices, {"SPY": 1}, [], base_currency="KRW")
    pf.inventory = {"SPY": 10, "_USD": 500, "_KRW": 500}
    assert set(pf.make_rebalancing_plan()) == {"SPY"}


def test_eval_nav_sums_positions_and_cash():
    transactions = [
        Portfolio.Transaction(utc(2026, 1, 1), "SPY", 10),
        Portfolio.Transaction(utc(2026, 1, 1), "_KRW", 1000),
    ]
    pf = Portfolio({}, {}, transactions, base_currency="KRW")
    nav = pf.eval_nav(utc(2026, 1, 2), {"SPY": 500.0, "_KRW": 1.0})
    assert nav == 6000.0


def test_eval_nav_ignores_transactions_after_the_date():
    transactions = [
        Portfolio.Transaction(utc(2026, 1, 1), "SPY", 10),
        Portfolio.Transaction(utc(2026, 3, 1), "SPY", 10),
    ]
    pf = Portfolio({}, {}, transactions, base_currency="KRW")
    assert pf.eval_nav(utc(2026, 2, 1), {"SPY": 100.0}) == 1000.0


def test_eval_nav_skips_zero_quantity_holdings():
    transactions = [
        Portfolio.Transaction(utc(2026, 1, 1), "SPY", 10),
        Portfolio.Transaction(utc(2026, 1, 2), "SPY", -10),
    ]
    pf = Portfolio({}, {}, transactions, base_currency="KRW")
    assert pf.eval_nav(utc(2026, 1, 3), {}) == 0.0


def test_eval_nav_raises_on_a_missing_price():
    transactions = [Portfolio.Transaction(utc(2026, 1, 1), "SPY", 10)]
    pf = Portfolio({}, {}, transactions, base_currency="KRW")
    with pytest.raises(MissingPriceException, match="SPY"):
        pf.eval_nav(utc(2026, 1, 2), {"_KRW": 1.0})


def test_eval_daily_nav_series_walks_days():
    transactions = [Portfolio.Transaction(utc(2026, 1, 1), "SPY", 10)]
    pf = Portfolio({}, {}, transactions, base_currency="KRW")
    prices_by_date = {
        utc(2026, 1, 2): {"SPY": 100.0},
        utc(2026, 1, 3): {"SPY": 110.0},
    }
    series = pf.eval_daily_nav_series(utc(2026, 1, 2), utc(2026, 1, 4), prices_by_date)
    assert series == [(utc(2026, 1, 2), 1000.0), (utc(2026, 1, 3), 1100.0)]


def test_eval_inventory_default_date_is_evaluated_per_call():
    """The default used to be bound at import time, freezing 'now'."""
    transactions = [Portfolio.Transaction(utc(2020, 1, 1), "SPY", 10)]
    pf = Portfolio({}, {}, transactions)
    assert pf.eval_inventory() == {"SPY": 10}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=. pytest tests/ext/test_ext_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'MissingPriceException'`

- [ ] **Step 3: Add the exception**

Append to `finance/ext/exceptions.py`:

```python
class MissingPriceException(Exception):
    pass
```

- [ ] **Step 4: Generalize cash handling in `Portfolio`**

In `finance/ext/models.py`, add near the top after the imports:

```python
from finance.ext.exceptions import MissingPriceException

CASH_PREFIX = "_"


def is_cash(ticker: str) -> bool:
    """Cash is held in the inventory under an underscore-prefixed ticker."""
    return ticker.startswith(CASH_PREFIX)
```

Change `Portfolio.__init__` to accept a base currency, keeping the existing
three positional parameters so current callers are unaffected:

```python
    def __init__(
        self,
        current_prices: dict,
        target_weights: dict,
        transactions: List[Transaction],
        base_currency: str = "USD",
    ):
        self.inventory: dict[str, float] = {}  # ticker: quantity
        self.current_prices = current_prices  # ticker: price
        self.target_weights = self.normalize_weights(target_weights)  # ticker: weight
        self.transactions = transactions
        self.base_currency = base_currency
        self.cash_ticker = CASH_PREFIX + base_currency
```

In `make_rebalancing_plan`, replace the `_USD` literal:

```python
        return {t: plan(t, diff) for t in diff if not is_cash(t)}
```

In `apply_plan`, replace every `self.inventory["_USD"]` and the trailing
`| {"_USD": self.inventory["_USD"]}` with `self.cash_ticker`:

```python
        def apply(t, q):
            self.inventory.setdefault(t, 0)
            while self.inventory[self.cash_ticker] - self.current_prices[t] * q < 0:
                if q > 0:
                    q -= 1
                else:
                    q += 1
            self.inventory[self.cash_ticker] -= self.current_prices[t] * q
            if self.inventory[self.cash_ticker] < 0:
                raise ValueError(
                    f"{self.cash_ticker} balance cannot be negative: {t}, {q}"
                )
            return self.inventory[t] + q

        self.inventory = {t: apply(t, q) for t, q in plan.items()} | {
            self.cash_ticker: self.inventory[self.cash_ticker]
        }
        return self.inventory
```

- [ ] **Step 5: Fix the import-time default and implement the NAV methods**

Change the signature of `eval_inventory` so the default date is computed per
call rather than bound when the module is imported:

```python
    def eval_inventory(self, evaluated_at=None) -> dict:
        if evaluated_at is None:
            evaluated_at = datetime.now(timezone.utc)
        self.inventory = {}
        for record in self.transactions:
            if record.date <= evaluated_at:
                self.apply_transaction(record)
        return self.inventory
```

Replace the `eval_nav` stub, and add the series method next to it:

```python
    def eval_nav(self, evaluated_at: datetime, prices: dict) -> float:
        """Net asset value at a point in time.

        `prices` must already be expressed in one currency; this method
        performs no conversion. Holdings that have gone to zero are skipped so
        that a delisted position with no price does not block valuation.
        """
        inventory = self.eval_inventory(evaluated_at)
        total = 0.0
        for ticker, quantity in inventory.items():
            if quantity == 0:
                continue
            try:
                price = prices[ticker]
            except KeyError:
                raise MissingPriceException(
                    "No price for {} at {}".format(ticker, evaluated_at)
                )
            total += price * quantity
        return total

    def eval_daily_nav_series(
        self, from_date: datetime, to_date: datetime, prices_by_date: dict
    ) -> List[tuple]:
        """NAV for each day in [from_date, to_date).

        :param prices_by_date: {datetime: {ticker: price in the base currency}}
        """
        return [
            (date, self.eval_nav(date, prices_by_date[date]))
            for date in make_dates(from_date, to_date)
        ]
```

`make_dates` is already imported from `finance.utils` in this module, and the
existing `from datetime import datetime, timedelta, timezone` line already
provides `timezone`. No import changes are needed.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `PYTHONPATH=. pytest tests/ext/test_ext_models.py -v`
Expected: all previously passing tests still pass, plus 10 new ones.

- [ ] **Step 7: Check the whole suite and the type checker**

Run: `PYTHONPATH=. pytest tests -v`
Run: `mypy --ignore-missing-imports finance`
Expected: no new failures or type errors.

- [ ] **Step 8: Commit**

```bash
git add finance/ext/models.py finance/ext/exceptions.py tests/ext/test_ext_models.py
git commit -m "$(cat <<'EOF'
feat(ext): Multi-currency cash and a daily NAV series

Cash is now any underscore-prefixed ticker rather than the hardcoded
_USD, so _KRW works alongside it. eval_nav() was a stub returning zero;
it now values an inventory against a price table, and
eval_daily_nav_series() walks a date range.

No FX lives here. net_asset_value is a plain sum of price x quantity, so
prices expressed in one base currency make mixed-currency inventories
correct without conversion code in this class.

Also fixes eval_inventory's default date, which was bound at import time
and froze 'now' for the life of the process.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Seed and replay

**Files:**
- Create: `subprojects/nav/nav/seed.py`
- Create: `subprojects/nav/nav/replay.py`
- Create: `subprojects/nav/seed.example.yaml`
- Test: `subprojects/nav/tests/test_seed.py`
- Test: `subprojects/nav/tests/test_replay.py`

**Interfaces:**
- Consumes: `SymbolMap` (Task 3), `CategoryMap`/`model.Transaction` (Task 4), `Portfolio` (Task 6).
- Produces: `seed.Seed` (frozen dataclass: `seed_date: date`, `positions: dict[str, Decimal]`, `cash: dict[str, Decimal]`); `seed.load(path, symbol_map) -> Seed`; `replay.seed_legs(seed) -> list[Portfolio.Transaction]`; `replay.transaction_legs(transactions, category_map, after) -> list[Portfolio.Transaction]`; `replay.build_portfolio(seed, transactions, category_map, base_currency="KRW") -> Portfolio`.

Quantities become `float` at the `Portfolio.Transaction` boundary because
`Portfolio` computes in `float`. Exactness is preserved everywhere it can
accumulate error — parsing, storage and leg arithmetic are all `Decimal`.

- [ ] **Step 1: Write the failing seed test**

Create `subprojects/nav/tests/test_seed.py`:

```python
from datetime import date
from decimal import Decimal

import pytest

from nav import seed, symbols

SYMBOLS_YAML = """
- {name: 애플, ticker: AAPL, currency: USD}
- {name: 삼성전자보통주, ticker: 005930.KS, currency: KRW}
"""

SEED_YAML = """
seed_date: 2026-09-14
positions:
  - {ticker: AAPL, quantity: 10}
  - {ticker: 005930.KS, quantity: 100}
cash:
  KRW: 1234567
  USD: 890.12
"""


@pytest.fixture
def symbol_map(tmp_path):
    path = tmp_path / "symbols.yaml"
    path.write_text(SYMBOLS_YAML, encoding="utf-8")
    return symbols.load(str(path))


def write(tmp_path, text):
    path = tmp_path / "seed.yaml"
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_loads_positions_and_cash(tmp_path, symbol_map):
    s = seed.load(write(tmp_path, SEED_YAML), symbol_map)
    assert s.seed_date == date(2026, 9, 14)
    assert s.positions == {"AAPL": Decimal("10"), "005930.KS": Decimal("100")}
    assert s.cash == {"KRW": Decimal("1234567"), "USD": Decimal("890.12")}


def test_cash_amounts_are_exact(tmp_path, symbol_map):
    s = seed.load(write(tmp_path, SEED_YAML), symbol_map)
    assert s.cash["USD"] == Decimal("890.12")


def test_unknown_ticker_is_rejected(tmp_path, symbol_map):
    text = "seed_date: 2026-09-14\npositions:\n  - {ticker: NOPE, quantity: 1}\ncash: {KRW: 0}\n"
    with pytest.raises(ValueError, match="NOPE"):
        seed.load(write(tmp_path, text), symbol_map)


def test_missing_seed_date_is_rejected(tmp_path, symbol_map):
    text = "positions: []\ncash: {KRW: 0}\n"
    with pytest.raises(ValueError, match="seed_date"):
        seed.load(write(tmp_path, text), symbol_map)


def test_empty_positions_are_allowed(tmp_path, symbol_map):
    text = "seed_date: 2026-09-14\npositions: []\ncash: {KRW: 100}\n"
    assert seed.load(write(tmp_path, text), symbol_map).positions == {}


def test_example_file_loads(symbol_map):
    seed.load("subprojects/nav/seed.example.yaml", symbol_map)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_seed.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nav.seed'`

- [ ] **Step 3: Implement `seed.py` and the example file**

`subprojects/nav/nav/seed.py`:

```python
"""The opening 잔고 that replay starts from."""

from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal
from typing import Dict

import yaml

from nav.symbols import SymbolMap


@dataclass(frozen=True)
class Seed:
    seed_date: date_type
    positions: Dict[str, Decimal]
    cash: Dict[str, Decimal]


def load(path: str, symbol_map: SymbolMap) -> Seed:
    with open(path, encoding="utf-8") as fin:
        content = yaml.safe_load(fin) or {}

    if "seed_date" not in content:
        raise ValueError("seed_date is required in {}".format(path))
    seed_date = content["seed_date"]
    if not isinstance(seed_date, date_type):
        raise ValueError("seed_date must be a date, got {!r}".format(seed_date))

    positions: Dict[str, Decimal] = {}
    for entry in content.get("positions") or []:
        ticker = entry["ticker"]
        try:
            symbol_map.currency_of(ticker)
        except KeyError:
            raise ValueError(
                "{} in {} is not listed in symbols.yaml".format(ticker, path)
            )
        positions[ticker] = Decimal(str(entry["quantity"]))

    cash = {
        currency: Decimal(str(amount))
        for currency, amount in (content.get("cash") or {}).items()
    }
    return Seed(seed_date=seed_date, positions=positions, cash=cash)
```

`subprojects/nav/seed.example.yaml`:

```yaml
# Copy to seed.yaml and fill in from a 잔고 screen or export.
# seed.yaml is gitignored: it holds real balances.
#
# Quantities and amounts are as of the close of seed_date. Transactions
# dated after seed_date are replayed on top of this.
seed_date: 2026-09-14
positions:
  - {ticker: AAPL, quantity: 10}
  - {ticker: 005930.KS, quantity: 100}
cash:
  KRW: 1234567
  USD: 890.12
```

- [ ] **Step 4: Write the failing replay test**

Create `subprojects/nav/tests/test_replay.py`:

```python
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from nav import categories, replay
from nav.model import Transaction
from nav.seed import Seed

CATEGORIES_YAML = """
- {category: 현금매수, handler: buy}
- {category: 배당금, handler: dividend}
"""


@pytest.fixture
def category_map(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text(CATEGORIES_YAML, encoding="utf-8")
    return categories.load(str(path))


SEED = Seed(
    seed_date=date(2026, 9, 10),
    positions={"AAPL": Decimal("10")},
    cash={"KRW": Decimal("1000000"), "USD": Decimal("500")},
)


def txn(day, category="현금매수", **kwargs):
    defaults = dict(
        date=datetime(2026, 9, day, tzinfo=timezone.utc),
        seq=1,
        category=category,
        name="애플",
        ticker="AAPL",
        currency="USD",
        amount=Decimal("300"),
        unit_price=Decimal("150"),
        quantity=Decimal("2"),
        fees=Decimal("1"),
        tax=Decimal("0"),
        raw="[]",
    )
    defaults.update(kwargs)
    return Transaction(**defaults)


def test_seed_legs_cover_positions_and_every_currency():
    legs = replay.seed_legs(SEED)
    assert {(leg.ticker, leg.quantity) for leg in legs} == {
        ("AAPL", 10.0),
        ("_KRW", 1000000.0),
        ("_USD", 500.0),
    }


def test_seed_legs_are_dated_at_the_seed_date():
    assert all(
        leg.date == datetime(2026, 9, 10, tzinfo=timezone.utc)
        for leg in replay.seed_legs(SEED)
    )


def test_transactions_on_or_before_the_seed_date_are_dropped(category_map):
    legs = replay.transaction_legs([txn(9), txn(10)], category_map, after=SEED.seed_date)
    assert legs == []


def test_transactions_after_the_seed_date_are_kept(category_map):
    legs = replay.transaction_legs([txn(11)], category_map, after=SEED.seed_date)
    assert [(leg.ticker, leg.quantity) for leg in legs] == [
        ("AAPL", 2.0),
        ("_USD", -301.0),
    ]


def test_portfolio_replays_seed_plus_transactions(category_map):
    pf = replay.build_portfolio(SEED, [txn(11)], category_map)
    inventory = pf.eval_inventory(datetime(2026, 9, 12, tzinfo=timezone.utc))
    assert inventory["AAPL"] == 12.0
    assert inventory["_USD"] == pytest.approx(199.0)
    assert inventory["_KRW"] == 1000000.0


def test_portfolio_before_a_transaction_shows_only_the_seed(category_map):
    pf = replay.build_portfolio(SEED, [txn(11)], category_map)
    inventory = pf.eval_inventory(datetime(2026, 9, 10, tzinfo=timezone.utc))
    assert inventory["AAPL"] == 10.0
    assert inventory["_USD"] == 500.0


def test_dividend_credits_cash_without_touching_the_position(category_map):
    pf = replay.build_portfolio(
        SEED,
        [txn(11, category="배당금", amount=Decimal("12.30"), tax=Decimal("1.84"),
             quantity=Decimal("0"))],
        category_map,
    )
    inventory = pf.eval_inventory(datetime(2026, 9, 12, tzinfo=timezone.utc))
    assert inventory["AAPL"] == 10.0
    assert inventory["_USD"] == pytest.approx(510.46)


def test_base_currency_is_krw_by_default(category_map):
    assert replay.build_portfolio(SEED, [], category_map).cash_ticker == "_KRW"
```

- [ ] **Step 5: Run it to verify it fails**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_replay.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nav.replay'`

- [ ] **Step 6: Implement `replay.py`**

```python
"""Seed plus transactions into a replayable Portfolio."""

from datetime import date as date_type
from datetime import datetime, time, timezone
from typing import Iterable, List

from finance.ext.models import Portfolio

from nav.categories import CategoryMap
from nav.model import Transaction, cash_ticker
from nav.seed import Seed


def _at_utc(value: date_type) -> datetime:
    return datetime.combine(value, time(0, 0, 0)).replace(tzinfo=timezone.utc)


def seed_legs(seed: Seed) -> List[Portfolio.Transaction]:
    """Opening balances as transactions dated at the seed date."""
    when = _at_utc(seed.seed_date)
    legs = [
        Portfolio.Transaction(when, ticker, float(quantity))
        for ticker, quantity in seed.positions.items()
    ]
    legs += [
        Portfolio.Transaction(when, cash_ticker(currency), float(amount))
        for currency, amount in seed.cash.items()
    ]
    return legs


def transaction_legs(
    transactions: Iterable[Transaction], category_map: CategoryMap, after: date_type
) -> List[Portfolio.Transaction]:
    """Legs for transactions dated strictly after the seed date.

    The seed states the closing 잔고 of its date, so that day's transactions are
    already reflected in it.
    """
    legs = []
    for transaction in transactions:
        if transaction.date.date() <= after:
            continue
        for leg in category_map.legs_for(transaction):
            legs.append(
                Portfolio.Transaction(transaction.date, leg.ticker, float(leg.quantity))
            )
    return legs


def build_portfolio(
    seed: Seed,
    transactions: Iterable[Transaction],
    category_map: CategoryMap,
    base_currency: str = "KRW",
) -> Portfolio:
    legs = seed_legs(seed) + transaction_legs(
        transactions, category_map, after=seed.seed_date
    )
    legs.sort(key=lambda leg: leg.date)
    return Portfolio({}, {}, legs, base_currency=base_currency)
```

- [ ] **Step 7: Run both test files to verify they pass**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_seed.py subprojects/nav/tests/test_replay.py -v`
Expected: 14 passed

- [ ] **Step 8: Commit**

```bash
git add subprojects/nav/nav/seed.py subprojects/nav/nav/replay.py \
        subprojects/nav/seed.example.yaml \
        subprojects/nav/tests/test_seed.py subprojects/nav/tests/test_replay.py
git commit -m "$(cat <<'EOF'
feat(nav): Replay a seeded 잔고 forward through transactions

The seed states the closing balance of its date, so transactions on that
date are already reflected and only later ones are applied.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Prices and FX

**Files:**
- Create: `subprojects/nav/nav/prices.py`
- Test: `subprojects/nav/tests/test_prices.py`

**Interfaces:**
- Consumes: `SymbolMap` (Task 3), `finance.ext.warehouse` (existing).
- Produces: `prices.fx_symbol(currency, base) -> Optional[str]`; `prices.region_for(symbol) -> str`; `prices.required_symbols(tickers, symbol_map, base, extra_currencies=()) -> list[str]`; `prices.build_price_table(historical, tickers, symbol_map, dates, base, extra_currencies=()) -> tuple[dict, dict]` returning `(prices_by_date, stale_by_date)`; `prices.refresh(symbols, historical_path)`.

`extra_currencies` forces a currency's rate into the table even when nothing is
currently held in it. The report always quotes a USD figure, so `USD` is always
requested — otherwise an account holding only KR stocks would have no
`_USD` price and no way to render `nav_usd`.

FX is not a subsystem. A currency's rate is a symbol in the same warehouse
(`USDKRW=X`, `JPYKRW=X`), fetched by the same code as any equity. Cash
pseudo-tickers are priced at their currency's rate, and `_KRW` at exactly 1.

- [ ] **Step 1: Write the failing test**

Create `subprojects/nav/tests/test_prices.py`:

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_prices.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nav.prices'`

- [ ] **Step 3: Implement `prices.py`**

```python
"""Daily closes and FX, expressed in one base currency.

An exchange rate is just another symbol in the parquet warehouse, so FX needs
no separate fetching, caching or storage path.
"""

import os
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from nav.model import cash_ticker
from nav.symbols import SymbolMap


class NoPriceHistoryError(Exception):
    pass


def fx_symbol(currency: str, base: str) -> Optional[str]:
    """Warehouse symbol for a currency's rate against the base currency."""
    if currency == base:
        return None
    return "{}{}=X".format(currency, base)


def region_for(symbol: str) -> str:
    if symbol.endswith("=X"):
        return "FX"
    if symbol.endswith((".KS", ".KQ")):
        return "KR"
    return "US"


def required_symbols(
    tickers: Iterable[str],
    symbol_map: SymbolMap,
    base: str,
    extra_currencies: Iterable[str] = (),
) -> List[str]:
    """Every warehouse symbol needed to value these holdings."""
    needed = set()
    currencies = set(extra_currencies)
    for ticker in tickers:
        needed.add(ticker)
        currencies.add(symbol_map.currency_of(ticker))
    for currency in currencies:
        symbol = fx_symbol(currency, base)
        if symbol:
            needed.add(symbol)
    return sorted(needed)


def refresh(symbols_to_fetch: Iterable[str], historical_path: str) -> pd.DataFrame:
    """Fetches each symbol's history and merges it into the warehouse file."""
    from finance.ext.warehouse import concat_dataframes, fetch_historical_data

    existing = (
        pd.read_parquet(historical_path) if os.path.exists(historical_path) else None
    )
    for symbol in symbols_to_fetch:
        fetched = fetch_historical_data(symbol, region=region_for(symbol))
        existing = fetched if existing is None else concat_dataframes(existing, fetched)

    if existing is None:
        raise ValueError("No symbols to refresh")

    os.makedirs(os.path.dirname(os.path.abspath(historical_path)), exist_ok=True)
    existing.to_parquet(historical_path, index=False)
    return existing


def _naive(index):
    """Drops any timezone so warehouse dates and query dates compare.

    yfinance history is timezone-aware; a hand-built frame usually is not.
    """
    return index.dt.tz_localize(None) if index.dt.tz is not None else index


def _close_series(historical: pd.DataFrame, symbol: str) -> pd.Series:
    rows = historical[historical["symbol"] == symbol]
    if rows.empty:
        raise NoPriceHistoryError("No history for {}".format(symbol))
    dates = _naive(pd.to_datetime(rows["date"])).dt.normalize()
    return pd.Series(rows["close"].values, index=dates).sort_index()


def _as_of(series: pd.Series, when: datetime, symbol: str) -> Tuple[float, bool]:
    """Latest close at or before `when`, and whether it was carried forward."""
    stamp = pd.Timestamp(when)
    if stamp.tzinfo is not None:
        stamp = stamp.tz_localize(None)
    naive = stamp.normalize()
    eligible = series[series.index <= naive]
    if eligible.empty:
        raise NoPriceHistoryError(
            "No close for {} at or before {}".format(symbol, naive.date())
        )
    return float(eligible.iloc[-1]), eligible.index[-1] < naive


def build_price_table(
    historical: pd.DataFrame,
    tickers: Iterable[str],
    symbol_map: SymbolMap,
    dates: Iterable[datetime],
    base: str,
    extra_currencies: Iterable[str] = (),
) -> Tuple[Dict[datetime, Dict[str, float]], Dict[datetime, List[str]]]:
    """Prices in the base currency for every ticker on every date.

    A missing close carries the last known one forward and records the symbol
    in the stale map. KR and US calendars differ, so on most days one side is
    stale by construction.
    """
    tickers = list(tickers)
    currencies = {symbol_map.currency_of(t) for t in tickers}
    currencies |= set(extra_currencies)
    currencies.add(base)

    close_by_symbol = {t: _close_series(historical, t) for t in tickers}
    fx_by_currency = {}
    for currency in currencies:
        symbol = fx_symbol(currency, base)
        fx_by_currency[currency] = (
            None if symbol is None else _close_series(historical, symbol)
        )

    prices_by_date: Dict[datetime, Dict[str, float]] = {}
    stale_by_date: Dict[datetime, List[str]] = {}

    for when in dates:
        row: Dict[str, float] = {}
        stale: List[str] = []

        rates: Dict[str, float] = {}
        for currency, series in fx_by_currency.items():
            if series is None:
                rates[currency] = 1.0
            else:
                rate, was_stale = _as_of(series, when, fx_symbol(currency, base))
                rates[currency] = rate
                if was_stale:
                    stale.append(fx_symbol(currency, base))

        for ticker in tickers:
            close, was_stale = _as_of(close_by_symbol[ticker], when, ticker)
            row[ticker] = close * rates[symbol_map.currency_of(ticker)]
            if was_stale:
                stale.append(ticker)

        for currency, rate in rates.items():
            row[cash_ticker(currency)] = rate

        prices_by_date[when] = row
        stale_by_date[when] = sorted(set(stale))

    return prices_by_date, stale_by_date
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_prices.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add subprojects/nav/nav/prices.py subprojects/nav/tests/test_prices.py
git commit -m "$(cat <<'EOF'
feat(nav): Base-currency price table with FX and carry-forward

An exchange rate is a warehouse symbol like any other (USDKRW=X), so FX
needs no separate fetch or storage path. Missing closes carry forward and
are reported as stale rather than silently substituted.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Daily NAV series, `nav sync`, `nav rebuild`

**Files:**
- Create: `subprojects/nav/nav/valuation.py`
- Modify: `subprojects/nav/nav/cli.py`
- Test: `subprojects/nav/tests/test_valuation.py`

**Interfaces:**
- Consumes: `Portfolio` (Task 6), `replay` (Task 7), `prices` (Task 8).
- Produces: `valuation.COLUMNS`; `valuation.daily_dates(start, end) -> list[datetime]`; `valuation.build(portfolio, dates, prices_by_date, stale_by_date, base="KRW", report_currency="USD") -> pd.DataFrame`; `valuation.holdings_at(portfolio, when, prices) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

Create `subprojects/nav/tests/test_valuation.py`:

```python
from datetime import date, datetime, timezone

import pytest

from finance.ext.models import Portfolio
from nav import valuation


def utc(day):
    return datetime(2026, 9, day, tzinfo=timezone.utc)


def portfolio():
    legs = [
        Portfolio.Transaction(utc(1), "AAPL", 10.0),
        Portfolio.Transaction(utc(1), "_USD", 500.0),
        Portfolio.Transaction(utc(1), "_KRW", 1000000.0),
    ]
    return Portfolio({}, {}, legs, base_currency="KRW")


PRICES = {
    utc(2): {"AAPL": 150.0 * 1300.0, "_USD": 1300.0, "_KRW": 1.0},
    utc(3): {"AAPL": 150.0 * 1400.0, "_USD": 1400.0, "_KRW": 1.0},
}
STALE = {utc(2): [], utc(3): ["AAPL"]}


def test_daily_dates_is_inclusive_of_start_and_end():
    dates = valuation.daily_dates(date(2026, 9, 1), date(2026, 9, 3))
    assert dates == [utc(1), utc(2), utc(3)]


def test_nav_krw_sums_holdings_and_cash():
    frame = valuation.build(portfolio(), [utc(2)], PRICES, STALE)
    row = frame.iloc[0]
    assert row["holdings_krw"] == pytest.approx(10 * 150.0 * 1300.0)
    assert row["cash_krw"] == pytest.approx(1000000.0)
    assert row["cash_usd"] == pytest.approx(500.0)
    assert row["nav_krw"] == pytest.approx(1950000.0 + 1000000.0 + 650000.0)


def test_nav_usd_is_nav_krw_over_the_rate():
    frame = valuation.build(portfolio(), [utc(2)], PRICES, STALE)
    row = frame.iloc[0]
    assert row["nav_usd"] == pytest.approx(row["nav_krw"] / 1300.0)


def test_fx_only_move_changes_nav_without_changing_positions():
    frame = valuation.build(portfolio(), [utc(2), utc(3)], PRICES, STALE)
    assert frame.iloc[1]["nav_krw"] > frame.iloc[0]["nav_krw"]
    assert frame.iloc[1]["holdings_krw"] == pytest.approx(10 * 150.0 * 1400.0)


def test_stale_symbols_are_recorded():
    frame = valuation.build(portfolio(), [utc(2), utc(3)], PRICES, STALE)
    assert frame.iloc[0]["stale"] == ""
    assert frame.iloc[1]["stale"] == "AAPL"


def test_columns_are_exactly_as_declared():
    frame = valuation.build(portfolio(), [utc(2)], PRICES, STALE)
    assert list(frame.columns) == valuation.COLUMNS


def test_holdings_at_reports_weights():
    holdings = valuation.holdings_at(portfolio(), utc(2), PRICES[utc(2)])
    by_ticker = {h["ticker"]: h for h in holdings}
    assert by_ticker["AAPL"]["quantity"] == pytest.approx(10.0)
    assert by_ticker["AAPL"]["value_krw"] == pytest.approx(1950000.0)
    assert sum(h["weight"] for h in holdings) == pytest.approx(1.0)


def test_holdings_at_omits_closed_positions():
    legs = [
        Portfolio.Transaction(utc(1), "AAPL", 10.0),
        Portfolio.Transaction(utc(1), "AAPL", -10.0),
        Portfolio.Transaction(utc(1), "_KRW", 100.0),
    ]
    pf = Portfolio({}, {}, legs, base_currency="KRW")
    tickers = {h["ticker"] for h in valuation.holdings_at(pf, utc(2), {"_KRW": 1.0})}
    assert tickers == {"_KRW"}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_valuation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nav.valuation'`

- [ ] **Step 3: Implement `valuation.py`**

```python
"""The daily NAV series."""

from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone
from typing import Dict, Iterable, List

import pandas as pd

from finance.ext.models import Portfolio, is_cash

from nav.model import cash_ticker

COLUMNS = [
    "date",
    "nav_krw",
    "nav_usd",
    "holdings_krw",
    "cash_krw",
    "cash_usd",
    "fx_usdkrw",
    "stale",
]


def daily_dates(start: date_type, end: date_type) -> List[datetime]:
    """Every day from start to end inclusive, as UTC midnights."""
    days = (end - start).days
    return [
        datetime.combine(start + timedelta(days=i), time(0, 0, 0)).replace(
            tzinfo=timezone.utc
        )
        for i in range(days + 1)
    ]


def holdings_at(portfolio: Portfolio, when: datetime, prices: Dict[str, float]) -> List[dict]:
    """Open positions and cash at a point in time, with base-currency weights."""
    inventory = portfolio.eval_inventory(when)
    rows = []
    for ticker, quantity in inventory.items():
        if quantity == 0:
            continue
        value = prices[ticker] * quantity
        rows.append(
            {
                "ticker": ticker,
                "quantity": float(quantity),
                "price_krw": float(prices[ticker]),
                "value_krw": float(value),
                "is_cash": is_cash(ticker),
            }
        )
    total = sum(row["value_krw"] for row in rows)
    for row in rows:
        row["weight"] = row["value_krw"] / total if total else 0.0
    return sorted(rows, key=lambda r: -r["value_krw"])


def build(
    portfolio: Portfolio,
    dates: Iterable[datetime],
    prices_by_date: Dict[datetime, Dict[str, float]],
    stale_by_date: Dict[datetime, List[str]],
    base: str = "KRW",
    report_currency: str = "USD",
) -> pd.DataFrame:
    """NAV per day, in the base currency and in the reporting currency."""
    base_cash = cash_ticker(base)
    report_cash = cash_ticker(report_currency)

    rows = []
    for when in dates:
        prices = prices_by_date[when]
        inventory = portfolio.eval_inventory(when)
        rate = prices[report_cash]

        holdings = 0.0
        for ticker, quantity in inventory.items():
            if quantity == 0 or is_cash(ticker):
                continue
            holdings += prices[ticker] * quantity

        nav = portfolio.eval_nav(when, prices)
        rows.append(
            {
                "date": when,
                "nav_krw": nav,
                "nav_usd": nav / rate,
                "holdings_krw": holdings,
                "cash_krw": float(inventory.get(base_cash, 0.0)),
                "cash_usd": float(inventory.get(report_cash, 0.0)),
                "fx_usdkrw": float(rate),
                "stale": ",".join(stale_by_date.get(when, [])),
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)
```

- [ ] **Step 4: Add `nav sync` and `nav rebuild`**

Append to `subprojects/nav/nav/cli.py`:

```python
DEFAULT_HISTORICAL = "historical.parquet"


def _load_state(root: str):
    """Everything needed to value the account: maps, seed, transactions."""
    from nav import categories, ingest, replay, seed as seed_module, symbols

    p = _paths(root)
    symbol_map = symbols.load(p["symbols"])
    category_map = categories.load(p["categories"])
    account_seed = seed_module.load(p["seed"], symbol_map)

    frame = ingest.load_frame(p["transaction"])
    transactions = [] if frame is None else ingest.from_frame(frame)
    portfolio = replay.build_portfolio(account_seed, transactions, category_map)
    return p, symbol_map, account_seed, transactions, portfolio


def _held_tickers(account_seed, transactions):
    tickers = set(account_seed.positions)
    tickers |= {t.ticker for t in transactions if t.ticker}
    return sorted(tickers)


@cli.command()
@click.option("--root", default=DEFAULT_ROOT, show_default=True)
@click.option("--historical", default=DEFAULT_HISTORICAL, show_default=True)
@click.option("--fetch/--no-fetch", default=True, help="Fetch missing prices from Yahoo.")
def sync(root: str, historical: str, fetch: bool):
    """Refresh prices and recompute the daily NAV series."""
    import datetime as dt

    import pandas as pd

    from nav import ingest
    from nav import prices as prices_module
    from nav import valuation

    p, symbol_map, account_seed, transactions, portfolio = _load_state(root)
    tickers = _held_tickers(account_seed, transactions)
    if not tickers:
        raise click.ClickException("No holdings found; check seed.yaml and imports.")

    needed = prices_module.required_symbols(
        tickers, symbol_map, "KRW", extra_currencies=["USD"]
    )
    if fetch:
        click.echo("Fetching {} symbols...".format(len(needed)))
        prices_module.refresh(needed, historical)

    history = pd.read_parquet(historical)
    dates = valuation.daily_dates(account_seed.seed_date, dt.date.today())
    price_table, stale = prices_module.build_price_table(
        history, tickers, symbol_map, dates, "KRW", extra_currencies=["USD"]
    )
    frame = valuation.build(portfolio, dates, price_table, stale)
    ingest.save_frame(frame, p["nav_daily"])
    latest = frame.iloc[-1]
    click.echo(
        "{} days. NAV {:,.0f} KRW / {:,.2f} USD".format(
            len(frame), latest["nav_krw"], latest["nav_usd"]
        )
    )


@cli.command()
@click.option("--root", default=DEFAULT_ROOT, show_default=True)
@click.confirmation_option(prompt="Delete data/ and rebuild from imports/?")
def rebuild(root: str):
    """Delete derived data and rebuild it from imports/ and the YAML files."""
    import glob
    import shutil

    data_dir = os.path.join(root, "data")
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)

    exports = sorted(glob.glob(os.path.join(root, "imports", "*.csv")))
    if not exports:
        raise click.ClickException("No exports found under {}/imports".format(root))

    ctx = click.get_current_context()
    ctx.invoke(import_, paths=tuple(exports), root=root)
    ctx.invoke(sync, root=root, historical=DEFAULT_HISTORICAL, fetch=True)
```

`rebuild` composes the other commands through `ctx.invoke` rather than shelling
out to itself, so a failure in either step propagates normally.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_valuation.py -v`
Expected: 8 passed

- [ ] **Step 6: Run the whole nav suite**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests tests -v`
Expected: all pass.

- [ ] **Step 7: Verify against real data**

```bash
nav sync
```

Expected: a day count and today's NAV in both currencies. Sanity-check the
number against the 잔고 screen — it should agree to within the day's price
movement. If it does not, that is the reconciliation problem Task 12 exists to
diagnose; note the discrepancy and continue.

- [ ] **Step 8: Commit**

```bash
git add subprojects/nav/nav/valuation.py subprojects/nav/nav/cli.py \
        subprojects/nav/tests/test_valuation.py
git commit -m "$(cat <<'EOF'
feat(nav): Daily NAV series with `nav sync` and `nav rebuild`

NAV is reported in KRW and USD, with holdings, cash per currency, the
rate used, and the symbols whose prices were carried forward.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: `nav show`

**Files:**
- Modify: `subprojects/nav/nav/cli.py`
- Create: `subprojects/nav/nav/display.py`
- Test: `subprojects/nav/tests/test_display.py`

**Interfaces:**
- Consumes: `valuation` output frame (Task 9).
- Produces: `display.summarize(frame, when=None) -> dict` with keys `date`, `nav_krw`, `nav_usd`, `change_krw`, `change_pct`, `fx_usdkrw`, `stale`; `display.render(summary, holdings) -> rich.console.RenderableType`.

- [ ] **Step 1: Write the failing test**

Create `subprojects/nav/tests/test_display.py`:

```python
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


def test_render_returns_something_printable():
    from rich.console import Console

    holdings = [
        {"ticker": "AAPL", "quantity": 10.0, "price_krw": 100.0,
         "value_krw": 1000.0, "is_cash": False, "weight": 0.9},
        {"ticker": "_KRW", "quantity": 100.0, "price_krw": 1.0,
         "value_krw": 100.0, "is_cash": True, "weight": 0.1},
    ]
    console = Console(record=True, width=100)
    console.print(display.render(display.summarize(FRAME), holdings))
    text = console.export_text()
    assert "AAPL" in text
    assert "1,100" in text
```

- [ ] **Step 2: Run it to verify it fails**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_display.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nav.display'`

- [ ] **Step 3: Implement `display.py`**

```python
"""Terminal rendering of the NAV series."""

from datetime import datetime
from typing import List, Optional

import pandas as pd
from rich.console import Group
from rich.table import Table


def summarize(frame: pd.DataFrame, when: Optional[datetime] = None) -> dict:
    """One day's figures, with the change against the preceding row."""
    if when is None:
        index = len(frame) - 1
    else:
        matches = frame.index[frame["date"] == when].tolist()
        if not matches:
            raise KeyError("No NAV row for {}".format(when))
        index = matches[0]

    row = frame.iloc[index]
    previous = frame.iloc[index - 1] if index > 0 else None
    change = 0.0 if previous is None else float(row["nav_krw"] - previous["nav_krw"])
    change_pct = (
        0.0
        if previous is None or previous["nav_krw"] == 0
        else change / float(previous["nav_krw"])
    )
    stale = [s for s in str(row["stale"]).split(",") if s]

    return {
        "date": row["date"],
        "nav_krw": float(row["nav_krw"]),
        "nav_usd": float(row["nav_usd"]),
        "change_krw": change,
        "change_pct": change_pct,
        "fx_usdkrw": float(row["fx_usdkrw"]),
        "stale": stale,
    }


def render(summary: dict, holdings: List[dict]) -> Group:
    arrow = "▲" if summary["change_krw"] > 0 else ("▼" if summary["change_krw"] < 0 else "=")
    colour = "green" if summary["change_krw"] > 0 else ("red" if summary["change_krw"] < 0 else "white")

    header = Table.grid(padding=(0, 2))
    header.add_column(justify="right")
    header.add_column()
    header.add_row("date", str(pd.Timestamp(summary["date"]).date()))
    header.add_row("NAV", "{:,.0f} KRW".format(summary["nav_krw"]))
    header.add_row("", "{:,.2f} USD".format(summary["nav_usd"]))
    header.add_row(
        "change",
        "[{}]{} {:,.0f} KRW ({:+.2%})[/{}]".format(
            colour, arrow, abs(summary["change_krw"]), summary["change_pct"], colour
        ),
    )
    header.add_row("USDKRW", "{:,.2f}".format(summary["fx_usdkrw"]))
    if summary["stale"]:
        header.add_row("[yellow]stale[/yellow]", ", ".join(summary["stale"]))

    table = Table(title="Holdings")
    table.add_column("ticker")
    table.add_column("quantity", justify="right")
    table.add_column("price (KRW)", justify="right")
    table.add_column("value (KRW)", justify="right")
    table.add_column("weight", justify="right")
    for holding in holdings:
        table.add_row(
            holding["ticker"],
            "{:,.4f}".format(holding["quantity"]).rstrip("0").rstrip("."),
            "{:,.2f}".format(holding["price_krw"]),
            "{:,.0f}".format(holding["value_krw"]),
            "{:.1%}".format(holding["weight"]),
        )

    return Group(header, "", table)
```

- [ ] **Step 4: Add the `nav show` command**

Append to `subprojects/nav/nav/cli.py`:

```python
@cli.command()
@click.option("--root", default=DEFAULT_ROOT, show_default=True)
@click.option("--historical", default=DEFAULT_HISTORICAL, show_default=True)
@click.option("--date", "as_of", default=None, help="YYYY-MM-DD (defaults to the latest).")
def show(root: str, historical: str, as_of):
    """Print today's NAV, the change since yesterday, and the holdings."""
    from datetime import datetime, timezone

    import pandas as pd
    from rich.console import Console

    from nav import display, ingest, prices as prices_module, valuation

    p, symbol_map, account_seed, transactions, portfolio = _load_state(root)
    frame = ingest.load_frame(p["nav_daily"])
    if frame is None:
        raise click.ClickException("No NAV data. Run `nav sync` first.")

    when = (
        pd.Timestamp(frame.iloc[-1]["date"]).to_pydatetime()
        if as_of is None
        else datetime.strptime(as_of, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    )
    summary = display.summarize(frame, when=when)

    history = pd.read_parquet(historical)
    tickers = _held_tickers(account_seed, transactions)
    price_table, _ = prices_module.build_price_table(
        history, tickers, symbol_map, [when], "KRW", extra_currencies=["USD"]
    )
    holdings = valuation.holdings_at(portfolio, when, price_table[when])

    Console().print(display.render(summary, holdings))
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_display.py -v`
Expected: 6 passed

- [ ] **Step 6: Verify against real data**

```bash
nav show
nav show --date 2026-09-01
```

- [ ] **Step 7: Commit**

```bash
git add subprojects/nav/nav/display.py subprojects/nav/nav/cli.py \
        subprojects/nav/tests/test_display.py
git commit -m "$(cat <<'EOF'
feat(nav): Add `nav show`

NAV in both currencies, the change since the preceding day, the rate
used, any carried-forward prices, and the holdings with weights.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: `nav report`

**Files:**
- Create: `subprojects/nav/nav/report.py`
- Modify: `subprojects/nav/nav/cli.py`
- Test: `subprojects/nav/tests/test_report.py`

**Interfaces:**
- Consumes: the NAV frame (Task 9), `holdings_at` (Task 9), `summarize` (Task 10).
- Produces: `report.build_payload(frame, holdings, summary) -> dict`; `report.render_html(payload) -> str`.

The data is inlined in a `<script type="application/json">` block rather than
fetched from a sibling file, because a page opened over `file://` cannot fetch
local resources. The result is one double-clickable file with no server and no
build step.

- [ ] **Step 1: Write the failing test**

Create `subprojects/nav/tests/test_report.py`:

```python
import json
from datetime import datetime, timezone

import pandas as pd

from nav import display, report, valuation


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

HOLDINGS = [
    {"ticker": "AAPL", "quantity": 10.0, "price_krw": 100.0, "value_krw": 1000.0,
     "is_cash": False, "weight": 0.909},
    {"ticker": "_KRW", "quantity": 100.0, "price_krw": 1.0, "value_krw": 100.0,
     "is_cash": True, "weight": 0.091},
]


def payload():
    return report.build_payload(FRAME, HOLDINGS, display.summarize(FRAME))


def test_payload_series_is_json_serializable():
    json.dumps(payload())


def test_payload_dates_are_iso_strings():
    assert payload()["series"][0]["date"] == "2026-09-01"


def test_payload_carries_both_currencies():
    latest = payload()["summary"]
    assert latest["nav_krw"] == 1100.0
    assert latest["nav_usd"] == 1.1


def test_payload_carries_holdings_and_stale():
    p = payload()
    assert p["holdings"][0]["ticker"] == "AAPL"
    assert p["summary"]["stale"] == ["AAPL"]


def test_html_inlines_the_payload():
    html = report.render_html(payload())
    assert '<script type="application/json" id="nav-data">' in html
    assert '"nav_krw": 1100.0' in html or '"nav_krw":1100.0' in html


def test_html_has_no_unsubstituted_placeholder():
    html = report.render_html(payload())
    assert "{{" not in html


def test_html_pins_an_exact_chart_library_version():
    html = report.render_html(payload())
    assert "cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js" in html


def test_html_does_not_fetch_a_sibling_data_file():
    assert "fetch(" not in report.render_html(payload())
```

- [ ] **Step 2: Run it to verify it fails**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nav.report'`

- [ ] **Step 3: Implement `report.py`**

```python
"""A self-contained HTML report."""

import json
from typing import List

import pandas as pd

CHART_JS = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NAV</title>
<style>
  :root { color-scheme: light dark; --fg: #1a1a1a; --muted: #6b6b6b; --bg: #fafafa; --line: #e0e0e0; }
  @media (prefers-color-scheme: dark) {
    :root { --fg: #e8e8e8; --muted: #9a9a9a; --bg: #16181d; --line: #2c2f36; }
  }
  body { margin: 0; padding: 24px; background: var(--bg); color: var(--fg);
         font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif; }
  .wrap { max-width: 900px; margin: 0 auto; }
  h1 { font-size: 15px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase;
       color: var(--muted); margin: 0 0 4px; }
  .nav { font-size: 34px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .sub { color: var(--muted); font-variant-numeric: tabular-nums; }
  .up { color: #1a7f37; } .down { color: #c0392b; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px;
           background: #f5c26b33; color: #8a6100; }
  @media (prefers-color-scheme: dark) { .badge { color: #f0c674; } }
  .toggle { margin: 20px 0 8px; }
  button { font: inherit; padding: 5px 14px; border: 1px solid var(--line);
           background: transparent; color: var(--fg); cursor: pointer; }
  button[aria-pressed="true"] { background: var(--fg); color: var(--bg); }
  button:first-of-type { border-radius: 6px 0 0 6px; }
  button:last-of-type { border-radius: 0 6px 6px 0; border-left: 0; }
  table { border-collapse: collapse; width: 100%; margin-top: 28px; }
  th, td { padding: 7px 10px; border-bottom: 1px solid var(--line); text-align: right;
           font-variant-numeric: tabular-nums; }
  th:first-child, td:first-child { text-align: left; font-variant-numeric: normal; }
  th { color: var(--muted); font-weight: 500; font-size: 12px; text-transform: uppercase;
       letter-spacing: .04em; }
  .cash td:first-child { color: var(--muted); }
  canvas { margin-top: 8px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Net asset value</h1>
  <div class="nav" id="nav"></div>
  <div class="sub" id="sub"></div>
  <div class="sub" id="stale"></div>

  <div class="toggle">
    <button id="btn-krw" aria-pressed="true">KRW</button
    ><button id="btn-usd" aria-pressed="false">USD</button>
  </div>
  <canvas id="chart" height="110"></canvas>

  <table>
    <thead><tr><th>Ticker</th><th>Quantity</th><th>Price (KRW)</th>
    <th>Value (KRW)</th><th>Weight</th></tr></thead>
    <tbody id="holdings"></tbody>
  </table>
</div>

<script type="application/json" id="nav-data">__PAYLOAD__</script>
<script src="__CHARTJS__"></script>
<script>
const data = JSON.parse(document.getElementById("nav-data").textContent);
const fmt = (v, d) => v.toLocaleString(undefined, {minimumFractionDigits: d, maximumFractionDigits: d});
const s = data.summary;

document.getElementById("nav").textContent = fmt(s.nav_krw, 0) + " KRW";
const dir = s.change_krw > 0 ? "up" : (s.change_krw < 0 ? "down" : "");
const arrow = s.change_krw > 0 ? "\\u25b2" : (s.change_krw < 0 ? "\\u25bc" : "=");
document.getElementById("sub").innerHTML =
  fmt(s.nav_usd, 2) + " USD &middot; <span class='" + dir + "'>" + arrow + " " +
  fmt(Math.abs(s.change_krw), 0) + " KRW (" + (s.change_pct * 100).toFixed(2) + "%)</span>" +
  " &middot; " + s.date + " &middot; USDKRW " + fmt(s.fx_usdkrw, 2);
if (s.stale.length) {
  document.getElementById("stale").innerHTML =
    "<span class='badge'>carried forward: " + s.stale.join(", ") + "</span>";
}

const body = document.getElementById("holdings");
data.holdings.forEach(h => {
  const tr = document.createElement("tr");
  if (h.is_cash) tr.className = "cash";
  [h.ticker, fmt(h.quantity, 4).replace(/\\.?0+$/, ""), fmt(h.price_krw, 2),
   fmt(h.value_krw, 0), (h.weight * 100).toFixed(1) + "%"].forEach(v => {
    const td = document.createElement("td");
    td.textContent = v;
    tr.appendChild(td);
  });
  body.appendChild(tr);
});

const labels = data.series.map(r => r.date);
const chart = new Chart(document.getElementById("chart"), {
  type: "line",
  data: {labels, datasets: [{
    data: data.series.map(r => r.nav_krw),
    borderColor: "#4c78a8", borderWidth: 2, pointRadius: 0, tension: 0.15, fill: false
  }]},
  options: {
    responsive: true, maintainAspectRatio: true,
    plugins: {legend: {display: false}},
    scales: {x: {ticks: {maxTicksLimit: 8}}, y: {ticks: {callback: v => fmt(v, 0)}}}
  }
});

function setCurrency(currency) {
  const krw = currency === "krw";
  chart.data.datasets[0].data = data.series.map(r => krw ? r.nav_krw : r.nav_usd);
  chart.update();
  document.getElementById("btn-krw").setAttribute("aria-pressed", krw);
  document.getElementById("btn-usd").setAttribute("aria-pressed", !krw);
}
document.getElementById("btn-krw").onclick = () => setCurrency("krw");
document.getElementById("btn-usd").onclick = () => setCurrency("usd");
</script>
</body>
</html>
"""


def build_payload(frame: pd.DataFrame, holdings: List[dict], summary: dict) -> dict:
    series = [
        {
            "date": str(pd.Timestamp(row["date"]).date()),
            "nav_krw": float(row["nav_krw"]),
            "nav_usd": float(row["nav_usd"]),
        }
        for row in frame.to_dict("records")
    ]
    return {
        "series": series,
        "holdings": holdings,
        "summary": {
            "date": str(pd.Timestamp(summary["date"]).date()),
            "nav_krw": summary["nav_krw"],
            "nav_usd": summary["nav_usd"],
            "change_krw": summary["change_krw"],
            "change_pct": summary["change_pct"],
            "fx_usdkrw": summary["fx_usdkrw"],
            "stale": summary["stale"],
        },
    }


def render_html(payload: dict) -> str:
    return TEMPLATE.replace(
        "__PAYLOAD__", json.dumps(payload, ensure_ascii=False)
    ).replace("__CHARTJS__", CHART_JS)
```

- [ ] **Step 4: Add the `nav report` command**

Append to `subprojects/nav/nav/cli.py`:

```python
@cli.command()
@click.option("--root", default=DEFAULT_ROOT, show_default=True)
@click.option("--historical", default=DEFAULT_HISTORICAL, show_default=True)
@click.option("--output", "-o", default=None, help="Defaults to <root>/nav.html")
def report(root: str, historical: str, output):
    """Write a self-contained HTML dashboard."""
    import pandas as pd

    from nav import display, ingest, prices as prices_module
    from nav import report as report_module
    from nav import valuation

    p, symbol_map, account_seed, transactions, portfolio = _load_state(root)
    frame = ingest.load_frame(p["nav_daily"])
    if frame is None:
        raise click.ClickException("No NAV data. Run `nav sync` first.")

    when = pd.Timestamp(frame.iloc[-1]["date"]).to_pydatetime()
    history = pd.read_parquet(historical)
    price_table, _ = prices_module.build_price_table(
        history, _held_tickers(account_seed, transactions), symbol_map, [when],
        "KRW", extra_currencies=["USD"],
    )
    holdings = valuation.holdings_at(portfolio, when, price_table[when])

    payload = report_module.build_payload(frame, holdings, display.summarize(frame))
    destination = output or os.path.join(root, "nav.html")
    with open(destination, "w", encoding="utf-8") as fout:
        fout.write(report_module.render_html(payload))
    click.echo("Wrote {}".format(destination))
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_report.py -v`
Expected: 8 passed

- [ ] **Step 6: Open the real report**

```bash
nav report && open subprojects/nav/nav.html
```

Expected: the curve renders, the KRW/USD toggle switches the axis, and the
holdings table matches `nav show`.

- [ ] **Step 7: Commit**

```bash
git add subprojects/nav/nav/report.py subprojects/nav/nav/cli.py \
        subprojects/nav/tests/test_report.py
git commit -m "$(cat <<'EOF'
feat(nav): Add `nav report`

One self-contained HTML file with the data inlined, since a file:// page
cannot fetch a sibling JSON. Opens by double-click, no server.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: `nav check` — reconciliation and corporate-action detection

The 잔고 export format is undocumented, so `nav check` reads a statement in the
same YAML shape as `seed.yaml` rather than a broker CSV. Transcribing a handful
of positions is a minute's work, it is done rarely, and it keeps the command
independent of a format that has not been observed. A CSV parser can be added
later without changing the comparison logic.

**Files:**
- Create: `subprojects/nav/nav/check.py`
- Modify: `subprojects/nav/nav/cli.py`
- Modify: `subprojects/nav/README.md`
- Test: `subprojects/nav/tests/test_check.py`

**Interfaces:**
- Consumes: `Seed`/`seed.load` (Task 7), `Portfolio` (Task 6).
- Produces: `check.Difference` (frozen dataclass: `ticker: str`, `computed: float`, `actual: float`, `delta: float`); `check.compare(portfolio, statement, when) -> list[Difference]`; `check.suspicious_moves(historical, tickers, threshold=0.4) -> list[dict]`.

- [ ] **Step 1: Write the failing test**

Create `subprojects/nav/tests/test_check.py`:

```python
from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd

from finance.ext.models import Portfolio
from nav import check
from nav.seed import Seed


def utc(day):
    return datetime(2026, 9, day, tzinfo=timezone.utc)


def portfolio():
    legs = [
        Portfolio.Transaction(utc(1), "AAPL", 10.0),
        Portfolio.Transaction(utc(1), "_KRW", 1000.0),
    ]
    return Portfolio({}, {}, legs, base_currency="KRW")


def statement(**kwargs):
    defaults = dict(
        seed_date=date(2026, 9, 2),
        positions={"AAPL": Decimal("10")},
        cash={"KRW": Decimal("1000")},
    )
    defaults.update(kwargs)
    return Seed(**defaults)


def test_no_differences_when_everything_agrees():
    assert check.compare(portfolio(), statement(), utc(2)) == []


def test_reports_a_quantity_mismatch():
    diffs = check.compare(portfolio(), statement(positions={"AAPL": Decimal("20")}), utc(2))
    assert len(diffs) == 1
    assert diffs[0].ticker == "AAPL"
    assert diffs[0].computed == 10.0
    assert diffs[0].actual == 20.0
    assert diffs[0].delta == 10.0


def test_reports_a_cash_mismatch():
    diffs = check.compare(portfolio(), statement(cash={"KRW": Decimal("900")}), utc(2))
    assert [d.ticker for d in diffs] == ["_KRW"]
    assert diffs[0].delta == -100.0


def test_reports_a_position_missing_from_the_statement():
    diffs = check.compare(portfolio(), statement(positions={}), utc(2))
    assert diffs[0].ticker == "AAPL"
    assert diffs[0].actual == 0.0


def test_reports_a_position_missing_from_the_replay():
    diffs = check.compare(
        portfolio(), statement(positions={"AAPL": Decimal("10"), "TSLA": Decimal("5")}), utc(2)
    )
    assert [d.ticker for d in diffs] == ["TSLA"]
    assert diffs[0].computed == 0.0


def test_tiny_rounding_differences_are_ignored():
    diffs = check.compare(
        portfolio(), statement(cash={"KRW": Decimal("1000.0000001")}), utc(2)
    )
    assert diffs == []


HISTORICAL = pd.DataFrame(
    [
        {"symbol": "AAPL", "date": pd.Timestamp("2026-09-01"), "close": 100.0},
        {"symbol": "AAPL", "date": pd.Timestamp("2026-09-02"), "close": 25.0},
        {"symbol": "TSLA", "date": pd.Timestamp("2026-09-01"), "close": 100.0},
        {"symbol": "TSLA", "date": pd.Timestamp("2026-09-02"), "close": 103.0},
    ]
)


def test_suspicious_moves_flags_a_probable_split():
    moves = check.suspicious_moves(HISTORICAL, ["AAPL", "TSLA"])
    assert [m["symbol"] for m in moves] == ["AAPL"]
    assert moves[0]["ratio"] < -0.7


def test_suspicious_moves_ignores_ordinary_days():
    assert check.suspicious_moves(HISTORICAL, ["TSLA"]) == []
```

- [ ] **Step 2: Run it to verify it fails**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_check.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nav.check'`

- [ ] **Step 3: Implement `check.py`**

```python
"""Reconciliation of the replayed inventory against a real statement."""

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List

import pandas as pd

from finance.ext.models import Portfolio

from nav.model import cash_ticker
from nav.seed import Seed

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
```

- [ ] **Step 4: Add the `nav check` command**

Append to `subprojects/nav/nav/cli.py`:

```python
@cli.command()
@click.argument("statement", type=click.Path(exists=True, dir_okay=False))
@click.option("--root", default=DEFAULT_ROOT, show_default=True)
@click.option("--historical", default=DEFAULT_HISTORICAL, show_default=True)
def check(statement: str, root: str, historical: str):
    """Reconcile the replayed inventory against a real 잔고 statement.

    STATEMENT is a YAML file in the same shape as seed.yaml.
    """
    from datetime import datetime, time, timezone

    import pandas as pd

    from nav import check as check_module
    from nav import seed as seed_module

    p, symbol_map, account_seed, transactions, portfolio = _load_state(root)
    actual = seed_module.load(statement, symbol_map)
    when = datetime.combine(actual.seed_date, time(0, 0, 0)).replace(tzinfo=timezone.utc)

    differences = check_module.compare(portfolio, actual, when)
    if differences:
        click.echo("Differences as of {}:".format(actual.seed_date))
        for difference in differences:
            click.echo(
                "  {:<12} computed {:>14,.4f}  actual {:>14,.4f}  delta {:>+14,.4f}".format(
                    difference.ticker, difference.computed, difference.actual, difference.delta
                )
            )
    else:
        click.echo("Reconciled: no differences as of {}.".format(actual.seed_date))

    if os.path.exists(historical):
        moves = check_module.suspicious_moves(
            pd.read_parquet(historical), _held_tickers(account_seed, transactions)
        )
        if moves:
            click.echo("\nPossible corporate actions (single-day moves over 40%):")
            for move in moves:
                click.echo(
                    "  {:<12} {}  {:+.1%}".format(move["symbol"], move["date"], move["ratio"])
                )

    if differences:
        raise SystemExit(1)
```

- [ ] **Step 5: Update the README for the YAML statement**

In `subprojects/nav/README.md`, change the `nav check` row of the CLI table to:

```
| `nav check <statement.yaml>` | Reconcile computed positions against a real 잔고, given as a YAML file in the same shape as `seed.yaml`; report per-symbol differences. |
```

and replace the paragraph beneath the table with:

```
The 잔고 export format is undocumented, so the statement is supplied as YAML in
the same shape as `seed.yaml` rather than as a broker CSV. Transcribing a few
positions is a minute's work, it is done rarely, and it keeps reconciliation
independent of a format that has never been observed.
```

In the same file, under **Pipeline → 3. Transaction taxonomy**, replace the
`fx_exchange` handler mention: the handler set is `buy`, `sell`, `cash_in`,
`cash_out`, `dividend`, `interest`, `fee`, `noop`, and 환전 maps to `cash_out`
on the paying row and `cash_in` on the receiving row.

Under **Upstream changes**, note that `finance/providers/record.py` and
`finance/providers/miraeasset.py` were also modified (Task 2) to accept
comma-separated numbers and fractional share quantities.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests/test_check.py -v`
Expected: 8 passed

- [ ] **Step 7: Run the entire suite**

Run: `PYTHONPATH=.:subprojects/nav pytest subprojects/nav/tests tests -v`
Run: `mypy --ignore-missing-imports finance`
Expected: all pass, no new type errors.

- [ ] **Step 8: Commit**

```bash
git add subprojects/nav/nav/check.py subprojects/nav/nav/cli.py \
        subprojects/nav/README.md subprojects/nav/tests/test_check.py
git commit -m "$(cat <<'EOF'
feat(nav): Add `nav check`

Reconciles the replayed inventory against a real 잔고 and flags
single-day price moves over 40% as probable corporate actions. Splits
are not corrected -- Yahoo closes are split-adjusted while replayed
quantities are not -- but they no longer pass unnoticed.

The statement is YAML in the seed.yaml shape rather than a broker CSV,
since that export format has never been observed.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```
