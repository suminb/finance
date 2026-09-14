import json
from datetime import datetime, timezone

import pandas as pd
import yaml
from click.testing import CliRunner

from nav import ingest, prices as prices_module, replay, seed as seed_module, valuation
from nav.categories import CategoryMap
from nav.cli import cli
from nav.symbols import Symbol, SymbolMap


SAMPLE = "subprojects/nav/tests/samples/miraeasset_0650_sample.csv"


def utc(day):
    return datetime(2026, 9, day, tzinfo=timezone.utc)


def assert_clean_error(result, *fragments):
    """The failure reached the user as a message, not as an escaped exception.

    `"Traceback" not in result.output` cannot fail: CliRunner captures an
    uncaught exception in `result.exception` and never writes it to
    `result.output`. What actually distinguishes the two cases is the
    exception object -- click turns a ClickException into SystemExit(1) after
    printing "Error: ...", while anything else arrives intact.
    """
    assert result.exit_code != 0, result.output
    assert isinstance(result.exception, SystemExit), (
        "expected a ClickException, but {!r} escaped".format(result.exception)
    )
    assert "Error: " in result.output, result.output
    for fragment in fragments:
        assert fragment in result.output, result.output


def _build_show_root(tmp_path):
    """A synthetic root + historical file for exercising `nav show` end to end.

    AAPL has a close on both days, so it is never stale. USDKRW=X only has a
    close for 2026-09-01, so on 2026-09-02 the rate is carried forward and
    recorded as stale -- deliberately a symbol that is not also a holding,
    so its appearance in rendered output can only come from the stale line.
    """
    root = tmp_path / "root"
    (root / "data").mkdir(parents=True)

    (root / "symbols.yaml").write_text(
        yaml.safe_dump([{"name": "APPLE", "ticker": "AAPL", "currency": "USD"}]),
        encoding="utf-8",
    )
    (root / "categories.yaml").write_text(yaml.safe_dump([]), encoding="utf-8")
    (root / "seed.yaml").write_text(
        yaml.safe_dump(
            {
                "seed_date": utc(1).date(),
                "positions": [{"ticker": "AAPL", "quantity": 10}],
                "cash": {"KRW": 100000, "USD": 0},
            }
        ),
        encoding="utf-8",
    )

    historical_path = tmp_path / "historical.parquet"
    pd.DataFrame(
        [
            {"symbol": "AAPL", "date": pd.Timestamp("2026-09-01"), "close": 150.0},
            {"symbol": "AAPL", "date": pd.Timestamp("2026-09-02"), "close": 155.0},
            {"symbol": "USDKRW=X", "date": pd.Timestamp("2026-09-01"), "close": 1300.0},
        ]
    ).to_parquet(historical_path, index=False)

    symbol_map = SymbolMap([Symbol(name="APPLE", ticker="AAPL", currency="USD")])
    account_seed = seed_module.load(str(root / "seed.yaml"), symbol_map)
    portfolio = replay.build_portfolio(account_seed, [], CategoryMap([]))

    dates = [utc(1), utc(2)]
    historical = pd.read_parquet(historical_path)
    price_table, stale = prices_module.build_price_table(
        historical, ["AAPL"], symbol_map, dates, "KRW", extra_currencies=["USD"]
    )
    frame = valuation.build(portfolio, dates, price_table, stale)
    ingest.save_frame(frame, str(root / "data" / "nav_daily.parquet"))

    return root, historical_path


def test_show_prints_the_latest_row_by_default(tmp_path):
    """Default `nav show`: the `to_pydatetime()` branch of `when`.

    Exercises both currencies and the stale annotation together, and pins
    the exact figures so a regression in either the NAV-USD line or the
    stale line (or a datetime-key mismatch that silently picked the wrong
    row) would show up as a failing assertion, not just a nonzero exit code.
    """
    root, historical_path = _build_show_root(tmp_path)

    result = CliRunner().invoke(
        cli, ["show", "--root", str(root), "--historical", str(historical_path)]
    )

    assert result.exit_code == 0, result.output
    assert "2026-09-02" in result.output
    assert "2,115,000 KRW" in result.output
    assert "1,626.92 USD" in result.output
    assert "65,000 KRW" in result.output
    assert "USDKRW=X" in result.output  # stale annotation, not a holding
    assert "AAPL" in result.output


def test_show_with_date_option_prints_that_row(tmp_path):
    """`--date`: the `strptime(...).replace(tzinfo=timezone.utc)` branch of `when`.

    2026-09-01 is the seed date, so nothing is stale and the change against
    the (nonexistent) prior row must be reported as zero.
    """
    root, historical_path = _build_show_root(tmp_path)

    result = CliRunner().invoke(
        cli,
        [
            "show",
            "--root", str(root),
            "--historical", str(historical_path),
            "--date", "2026-09-01",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "2026-09-01" in result.output
    assert "2,050,000 KRW" in result.output
    assert "1,576.92 USD" in result.output
    assert "0 KRW (+0.00%)" in result.output
    assert "USDKRW=X" not in result.output  # nothing carried forward on the seed date


def test_show_with_an_unknown_date_is_a_clean_error(tmp_path):
    """A `--date` with no matching row must not dump a raw KeyError traceback."""
    root, historical_path = _build_show_root(tmp_path)

    result = CliRunner().invoke(
        cli,
        [
            "show",
            "--root", str(root),
            "--historical", str(historical_path),
            "--date", "2026-09-03",
        ],
    )

    assert_clean_error(result, "2026-09-01", "2026-09-02")


def test_report_writes_a_self_contained_html_file_from_real_data(tmp_path):
    """`nav report` end to end, through the real `holdings_at` -> `build_payload`

    -> `json.dumps` path, not the hand-built dicts of native floats in
    test_report.py's fixtures. `holdings_at` and `summarize` are supposed to
    cast every numeric field with float(...), but nothing here previously
    caught a regression of that cast: a dropped float() would let a
    numpy.float64 reach json.dumps and raise TypeError only once someone ran
    `nav report` for real. This exercises that whole pipeline and confirms
    the emitted file's inlined JSON block parses.
    """
    root, historical_path = _build_show_root(tmp_path)
    output_path = tmp_path / "nav.html"

    result = CliRunner().invoke(
        cli,
        [
            "report",
            "--root", str(root),
            "--historical", str(historical_path),
            "--output", str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert output_path.exists()

    html = output_path.read_text(encoding="utf-8")
    start = html.index('id="nav-data">') + len('id="nav-data">')
    end = html.index("</script>", start)
    payload = json.loads(html[start:end])  # raises if a numpy scalar leaked through

    assert payload["summary"]["nav_krw"] == 2115000.0
    assert payload["holdings"][0]["ticker"] == "AAPL"


def _build_check_root(tmp_path):
    """A synthetic root + historical file for exercising `nav check` end to end.

    No transactions are imported, so the replayed inventory at any date on or
    after the seed date is exactly the seed's positions and cash -- the
    statement is what varies between tests. `historical.parquet` has a single
    close per symbol (deliberately not two), so `suspicious_moves` always
    skips it and the "Possible corporate actions" section never fires here;
    that keeps these tests focused on `compare`'s wiring through the CLI.
    """
    root = tmp_path / "root"
    (root / "data").mkdir(parents=True)

    (root / "symbols.yaml").write_text(
        yaml.safe_dump([{"name": "APPLE", "ticker": "AAPL", "currency": "USD"}]),
        encoding="utf-8",
    )
    (root / "categories.yaml").write_text(yaml.safe_dump([]), encoding="utf-8")
    (root / "seed.yaml").write_text(
        yaml.safe_dump(
            {
                "seed_date": utc(1).date(),
                "positions": [{"ticker": "AAPL", "quantity": 10}],
                "cash": {"KRW": 100000, "USD": 0},
            }
        ),
        encoding="utf-8",
    )

    historical_path = tmp_path / "historical.parquet"
    pd.DataFrame(
        [{"symbol": "AAPL", "date": pd.Timestamp("2026-09-01"), "close": 150.0}]
    ).to_parquet(historical_path, index=False)

    return root, historical_path


def _write_statement(path, **kwargs):
    defaults = dict(
        seed_date=utc(1).date(),
        positions=[{"ticker": "AAPL", "quantity": 10}],
        cash={"KRW": 100000, "USD": 0},
    )
    defaults.update(kwargs)
    path.write_text(yaml.safe_dump(defaults), encoding="utf-8")


def test_check_reports_no_differences_and_exits_zero(tmp_path):
    """A statement that agrees with the replay: clean exit, no diff table."""
    root, historical_path = _build_check_root(tmp_path)
    statement_path = tmp_path / "statement.yaml"
    _write_statement(statement_path)

    result = CliRunner().invoke(
        cli,
        [
            "check", str(statement_path),
            "--root", str(root),
            "--historical", str(historical_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Reconciled: no differences as of 2026-09-01." in result.output
    assert "Differences as of" not in result.output
    assert "Possible corporate actions" not in result.output


def test_check_reports_a_mismatch_and_exits_nonzero(tmp_path):
    """A statement that disagrees with the replay: diff table printed, exit 1."""
    root, historical_path = _build_check_root(tmp_path)
    statement_path = tmp_path / "statement.yaml"
    _write_statement(statement_path, positions=[{"ticker": "AAPL", "quantity": 20}])

    result = CliRunner().invoke(
        cli,
        [
            "check", str(statement_path),
            "--root", str(root),
            "--historical", str(historical_path),
        ],
    )

    assert result.exit_code == 1, result.output
    assert "Differences as of 2026-09-01:" in result.output
    assert "Reconciled" not in result.output
    assert "AAPL" in result.output
    assert "10.0000" in result.output  # computed
    assert "20.0000" in result.output  # actual
    assert "+10.0000" in result.output  # delta
    assert "_KRW" not in result.output  # cash agrees; only AAPL should differ


def test_rebuild_checks_for_exports_before_deleting_data(tmp_path):
    """A rebuild that cannot proceed must not have already destroyed data/.

    Both data/ and imports/ are gitignored, so once data/ is gone the only
    way back is the user's original broker exports. If imports/ turns out
    to be empty (wrong --root, nothing there yet, a misnamed file), the
    precondition failure must be reported before any deletion happens.
    """
    root = tmp_path
    data_dir = root / "data"
    data_dir.mkdir()
    marker = data_dir / "transaction.parquet"
    marker.write_bytes(b"not really a parquet file, just a marker")
    (root / "imports").mkdir()  # present but empty: no *.csv to rebuild from

    runner = CliRunner()
    result = runner.invoke(cli, ["rebuild", "--root", str(root), "--yes"])

    assert result.exit_code != 0
    assert data_dir.exists()
    assert marker.exists()


# --------------------------------------------------------------------------
# `nav import`: the designed workflow, and the ways a first run goes wrong.
# --------------------------------------------------------------------------


def _import_root(tmp_path, symbols_yaml=None, categories_yaml=None):
    """A root holding just the two YAML maps `nav import` needs."""
    root = tmp_path / "root"
    root.mkdir(exist_ok=True)
    if symbols_yaml is not None:
        (root / "symbols.yaml").write_text(symbols_yaml, encoding="utf-8")
    if categories_yaml is not None:
        (root / "categories.yaml").write_text(categories_yaml, encoding="utf-8")
    return root


FULL_SYMBOLS = (
    "- {name: 애플, ticker: AAPL, currency: USD}\n"
    "- {name: 삼성전자보통주, ticker: 005930.KS, currency: KRW}\n"
)
FULL_CATEGORIES = (
    "- {category: 현금매수, handler: buy}\n"
    "- {category: 배당금, handler: dividend}\n"
    "- {category: 출금, handler: cash_out}\n"
)


def test_import_writes_the_transaction_table_and_is_idempotent(tmp_path):
    """`nav import` end to end against the committed 0650 fixture.

    Re-running it must report the same total with nothing new, which is the
    idempotency the (date, seq) key exists to provide.
    """
    root = _import_root(tmp_path, FULL_SYMBOLS, FULL_CATEGORIES)
    runner = CliRunner()

    first = runner.invoke(cli, ["import", SAMPLE, "--root", str(root)])
    assert first.exit_code == 0, first.output
    assert "4 rows read, 4 new, 4 total" in first.output
    assert (root / "data" / "transaction.parquet").exists()

    second = runner.invoke(cli, ["import", SAMPLE, "--root", str(root)])
    assert second.exit_code == 0, second.output
    assert "4 rows read, 0 new, 4 total" in second.output


def test_import_with_an_unmapped_symbol_shows_the_stub_not_a_traceback(tmp_path):
    """The interaction the README advertises, and the one a user hits most.

    Buying a new holding always produces a 종목명 that symbols.yaml has never
    seen. The whole value of that failure is the paste-ready YAML stub, which
    used to arrive as the last line of a raw Python traceback with nothing on
    stdout at all.
    """
    root = _import_root(
        tmp_path, "- {name: 애플, ticker: AAPL, currency: USD}\n", FULL_CATEGORIES
    )

    result = CliRunner().invoke(cli, ["import", SAMPLE, "--root", str(root)])

    assert_clean_error(
        result,
        "Unmapped 종목명",
        "symbols.yaml",
        "- {name: 삼성전자보통주, ticker: '???', currency: '???'}",
    )
    assert not (root / "data").exists()  # nothing written


def test_import_with_an_unmapped_category_shows_the_stub(tmp_path):
    root = _import_root(
        tmp_path, FULL_SYMBOLS, "- {category: 현금매수, handler: buy}\n"
    )

    result = CliRunner().invoke(cli, ["import", SAMPLE, "--root", str(root)])

    assert_clean_error(
        result, "Unmapped 거래종류", "categories.yaml", "handler: '???'", "배당금"
    )


def test_import_of_a_colliding_key_is_a_clean_error(tmp_path):
    """The Critical data-loss case reaches the user as a message, not a raise."""
    root = _import_root(
        tmp_path,
        "[]\n",
        "- {category: 출금, handler: cash_out}\n- {category: 입금, handler: cash_in}\n",
    )
    header = open(SAMPLE, encoding="euc-kr").readline().rstrip("\n")
    export = tmp_path / "fx.csv"
    export.write_text(
        "\n".join(
            [
                header,
                '2026/09/05,7,출금,환전출금,KRW,"1,300,000","1,300,000",0,,,'
                "0,0,0,0,0,0,,110000,HTS,,,,,,",
                '2026/09/05,7,입금,환전입금,USD,"1,000.00","1,000.00",0,,,'
                "0,0,0,0,0,0,,110000,HTS,,,,,,",
            ]
        )
        + "\n",
        encoding="euc-kr",
    )

    result = CliRunner().invoke(cli, ["import", str(export), "--root", str(root)])

    assert_clean_error(result, "거래번호", "seq=7")
    assert not (root / "data").exists()


def test_import_of_a_utf8_export_names_the_encoding(tmp_path):
    """The likeliest shape of a broken export: an Excel round-trip to UTF-8."""
    root = _import_root(tmp_path, FULL_SYMBOLS, FULL_CATEGORIES)
    export = tmp_path / "utf8.csv"
    export.write_bytes(
        open(SAMPLE, "rb").read().decode("euc-kr").encode("utf-8")
    )

    result = CliRunner().invoke(cli, ["import", str(export), "--root", str(root)])

    assert_clean_error(result, "not euc-kr", "iconv")


def test_import_of_a_non_0650_file_names_the_column_count(tmp_path):
    """finance.providers.miraeasset's 25-column assert, wrapped at the boundary."""
    root = _import_root(tmp_path, FULL_SYMBOLS, FULL_CATEGORIES)
    export = tmp_path / "wrong.csv"
    export.write_text("a,b,c\n1,2,3\n", encoding="euc-kr")

    result = CliRunner().invoke(cli, ["import", str(export), "--root", str(root)])

    assert_clean_error(result, "0650", "25 columns")


def test_import_without_symbols_yaml_names_the_file(tmp_path):
    root = _import_root(tmp_path, None, FULL_CATEGORIES)

    result = CliRunner().invoke(cli, ["import", SAMPLE, "--root", str(root)])

    assert_clean_error(result, "symbols.yaml not found", "종목명")


def test_import_without_categories_yaml_names_the_file(tmp_path):
    root = _import_root(tmp_path, FULL_SYMBOLS, None)

    result = CliRunner().invoke(cli, ["import", SAMPLE, "--root", str(root)])

    assert_clean_error(result, "categories.yaml not found", "nav categories")


# --------------------------------------------------------------------------
# Missing inputs on the valuation commands.
# --------------------------------------------------------------------------


def test_show_without_a_seed_points_at_the_example(tmp_path):
    root = _import_root(tmp_path, FULL_SYMBOLS, FULL_CATEGORIES)

    result = CliRunner().invoke(cli, ["show", "--root", str(root)])

    assert_clean_error(result, "seed.yaml not found", "seed.example.yaml")


def test_show_without_symbols_yaml_names_the_file(tmp_path):
    root = _import_root(tmp_path, None, FULL_CATEGORIES)

    result = CliRunner().invoke(cli, ["show", "--root", str(root)])

    assert_clean_error(result, "symbols.yaml not found")


def test_show_without_a_historical_warehouse_says_what_creates_it(tmp_path):
    root, _ = _build_show_root(tmp_path)

    result = CliRunner().invoke(
        cli,
        ["show", "--root", str(root), "--historical", str(tmp_path / "absent.parquet")],
    )

    assert_clean_error(result, "No price history", "nav sync")


def test_report_without_a_historical_warehouse_says_what_creates_it(tmp_path):
    root, _ = _build_show_root(tmp_path)

    result = CliRunner().invoke(
        cli,
        [
            "report",
            "--root", str(root),
            "--historical", str(tmp_path / "absent.parquet"),
            "--output", str(tmp_path / "nav.html"),
        ],
    )

    assert_clean_error(result, "No price history", "nav sync")


def test_show_with_a_malformed_date_is_a_clean_error(tmp_path):
    """Distinct from a well-formed date with no row: strptime itself fails."""
    root, historical_path = _build_show_root(tmp_path)

    result = CliRunner().invoke(
        cli,
        [
            "show",
            "--root", str(root),
            "--historical", str(historical_path),
            "--date", "2026-13-45",
        ],
    )

    assert_clean_error(result, "YYYY-MM-DD", "2026-13-45")


def test_categories_on_a_utf8_export_names_the_encoding(tmp_path):
    export = tmp_path / "utf8.csv"
    export.write_bytes(open(SAMPLE, "rb").read().decode("euc-kr").encode("utf-8"))

    result = CliRunner().invoke(cli, ["categories", str(export)])

    assert_clean_error(result, "not euc-kr-encoded", "--encoding utf-8")


def test_categories_on_an_empty_file_says_so(tmp_path):
    export = tmp_path / "empty.csv"
    export.write_text("", encoding="euc-kr")

    result = CliRunner().invoke(cli, ["categories", str(export)])

    assert_clean_error(result, "is empty")


def test_categories_without_a_category_column_says_so(tmp_path):
    export = tmp_path / "other.csv"
    export.write_text("a,b,c\n1,2,3\n", encoding="euc-kr")

    result = CliRunner().invoke(cli, ["categories", str(export)])

    assert_clean_error(result, "No 거래종류 column", "0650")
