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
