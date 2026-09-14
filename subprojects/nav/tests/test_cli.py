import json
from datetime import datetime, timezone

import pandas as pd
import yaml
from click.testing import CliRunner

from nav import ingest, prices as prices_module, replay, seed as seed_module, valuation
from nav.categories import CategoryMap
from nav.cli import cli
from nav.symbols import Symbol, SymbolMap


def utc(day):
    return datetime(2026, 9, day, tzinfo=timezone.utc)


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

    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "2026-09-01" in result.output
    assert "2026-09-02" in result.output


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
