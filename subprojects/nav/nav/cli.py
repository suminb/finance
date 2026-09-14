"""Command line interface for nav.

Command definitions only. The state-assembly helpers they share live in
`nav.state`.
"""

import os

import click

from nav.state import DEFAULT_HISTORICAL, DEFAULT_ROOT


@click.group()
def cli():
    """Daily net asset value tracking."""


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--encoding", default="euc-kr", show_default=True)
def categories(path: str, encoding: str):
    """Print the 거래종류 vocabulary and numeric formats of a 0650 export."""
    from nav import probe

    try:
        headers, rows = probe.read_rows(path, encoding=encoding)
        click.echo(probe.format_report(headers, rows))
    except probe.MalformedExportError as error:
        raise click.ClickException(str(error)) from None


@cli.command(name="import")
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("--root", default=DEFAULT_ROOT, show_default=True)
def import_(paths, root: str):
    """Parse 0650 exports into data/transaction.parquet."""
    from finance.providers.miraeasset import Miraeasset

    from nav import categories, ingest, symbols
    from nav import state

    p = state.paths(root)
    state.require_file(
        p["symbols"], "symbols.yaml", "It maps each 종목명 to a ticker and a currency."
    )
    state.require_file(
        p["categories"],
        "categories.yaml",
        "It maps each 거래종류 to a handler; `nav categories <export>` prints the "
        "vocabulary to fill it from.",
    )
    symbol_map = symbols.load(p["symbols"])
    category_map = categories.load(p["categories"])
    provider = Miraeasset()

    transactions = []
    for path in paths:
        # An unmapped 종목명 is the interaction this design advertises -- it
        # happens the first time any new holding is bought -- and its whole
        # value is the paste-ready YAML stub the exception carries. Raw, that
        # stub arrives as the tail of a twenty-line traceback.
        try:
            transactions += ingest.normalize(
                provider.read_records(path), symbol_map, category_map, source=path
            )
        except (
            symbols.UnknownSymbolError,
            categories.UnknownCategoryError,
            ingest.DuplicateKeyError,
        ) as error:
            raise click.ClickException(str(error)) from None
        except UnicodeDecodeError as error:
            raise click.ClickException(
                "{} is not euc-kr ({}). 미래에셋 exports 0650 as euc-kr; a "
                "round-trip through Excel usually re-saves it as UTF-8. "
                "Re-export it, or convert it back with `iconv -f utf-8 -t "
                "euc-kr`.".format(path, error.reason)
            ) from None
        except AssertionError as error:
            # finance.providers.miraeasset asserts a 25-column header. That
            # assertion is the parent package's, and is left alone; it is
            # wrapped here, at the nav boundary, where the user is.
            raise click.ClickException(
                "{} does not look like a 거래내역조회 (0650) export ({}). "
                "0650 has 25 columns; `nav categories {}` prints what was "
                "actually found.".format(path, error, path)
            ) from None

    existing = ingest.load_frame(p["transaction"])
    before = 0 if existing is None else len(existing)
    merged = ingest.merge(existing, ingest.to_frame(transactions))
    ingest.save_frame(merged, p["transaction"])
    click.echo(
        "{} rows read, {} new, {} total".format(
            len(transactions), len(merged) - before, len(merged)
        )
    )


@cli.command()
@click.option("--root", default=DEFAULT_ROOT, show_default=True)
@click.option("--historical", default=DEFAULT_HISTORICAL, show_default=True)
@click.option("--fetch/--no-fetch", default=True, help="Fetch missing prices from Yahoo.")
def sync(root: str, historical: str, fetch: bool):
    """Refresh prices and recompute the daily NAV series."""
    import datetime as dt

    from nav import ingest
    from nav import prices as prices_module
    from nav import state, valuation

    p, symbol_map, account_seed, transactions, portfolio = state.load_state(root)
    tickers = state.held_tickers(account_seed, transactions)
    if not tickers:
        raise click.ClickException("No holdings found; check seed.yaml and imports.")

    currencies = state.account_currencies(account_seed, transactions, symbol_map)
    needed = prices_module.required_symbols(
        tickers, symbol_map, state.BASE_CURRENCY, extra_currencies=currencies
    )
    if fetch:
        click.echo("Fetching {} symbols...".format(len(needed)))
        prices_module.refresh(needed, historical)

    history = state.read_historical(historical)
    today = dt.date.today()
    try:
        dates = valuation.daily_dates(account_seed.seed_date, today)
    except ValueError:
        raise click.ClickException(
            "seed_date {} is in the future (today is {}), so there is no day "
            "to value. Correct seed_date in {}.".format(
                account_seed.seed_date, today, p["seed"]
            )
        ) from None
    price_table, stale = prices_module.build_price_table(
        history, tickers, symbol_map, dates, state.BASE_CURRENCY,
        extra_currencies=currencies,
    )
    try:
        frame = valuation.build(
            portfolio, dates, price_table, stale,
            base=state.BASE_CURRENCY, report_currency=state.REPORT_CURRENCY,
        )
    except valuation.UnrepresentableCurrencyError as error:
        raise click.ClickException(str(error)) from None
    if frame.empty:
        # Belt and braces behind daily_dates' own check: persisting an empty
        # series is what wedged the account, so never write one.
        raise click.ClickException(
            "The NAV series came out empty; nothing was written. Check "
            "seed_date in {}.".format(p["seed"])
        )
    ingest.save_frame(frame, p["nav_daily"])
    latest = frame.iloc[-1]
    click.echo(
        "{} days. NAV {:,.0f} KRW / {:,.2f} USD".format(
            len(frame), latest["nav_krw"], latest["nav_usd"]
        )
    )


@cli.command()
@click.option("--root", default=DEFAULT_ROOT, show_default=True)
@click.option("--historical", default=DEFAULT_HISTORICAL, show_default=True)
@click.option("--fetch/--no-fetch", default=True, help="Fetch missing prices from Yahoo.")
@click.confirmation_option(prompt="Delete data/ and rebuild from imports/?")
def rebuild(root: str, historical: str, fetch: bool):
    """Delete derived data and rebuild it from imports/ and the YAML files."""
    import glob
    import shutil

    exports = sorted(glob.glob(os.path.join(root, "imports", "*.csv")))
    if not exports:
        raise click.ClickException("No exports found under {}/imports".format(root))

    data_dir = os.path.join(root, "data")
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)

    ctx = click.get_current_context()
    ctx.invoke(import_, paths=tuple(exports), root=root)
    ctx.invoke(sync, root=root, historical=historical, fetch=fetch)


@cli.command()
@click.option("--root", default=DEFAULT_ROOT, show_default=True)
@click.option("--historical", default=DEFAULT_HISTORICAL, show_default=True)
@click.option("--date", "as_of", default=None, help="YYYY-MM-DD (defaults to the latest).")
def show(root: str, historical: str, as_of):
    """Print today's NAV, the change since yesterday, and the holdings."""
    from datetime import datetime, timezone

    import pandas as pd
    from rich.console import Console

    from nav import display, ingest
    from nav import prices as prices_module
    from nav import state, valuation

    p, symbol_map, account_seed, transactions, portfolio = state.load_state(root)
    frame = ingest.load_frame(p["nav_daily"])
    if frame is None or frame.empty:
        # `.empty` as well as None: an empty nav_daily.parquet on disk is
        # not "data", and testing only for None let the file's mere
        # existence route past this message into an IndexError.
        raise click.ClickException("No NAV data. Run `nav sync` first.")

    if as_of is None:
        when = pd.Timestamp(frame.iloc[-1]["date"]).to_pydatetime()
    else:
        # A well-formed date with no row is handled below; this is the other
        # half -- a date that strptime cannot parse at all, which used to be a
        # raw ValueError.
        try:
            when = datetime.strptime(as_of, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise click.ClickException(
                "--date must be YYYY-MM-DD, got {!r}.".format(as_of)
            ) from None
    try:
        summary = display.summarize(frame, when=when)
    except KeyError:
        earliest = pd.Timestamp(frame.iloc[0]["date"]).date()
        latest = pd.Timestamp(frame.iloc[-1]["date"]).date()
        raise click.ClickException(
            "No NAV row for {}. Available dates: {} to {}.".format(
                when.date(), earliest, latest
            )
        )

    history = state.read_historical(historical)
    tickers = state.held_tickers(account_seed, transactions)
    price_table, _ = prices_module.build_price_table(
        history, tickers, symbol_map, [when], state.BASE_CURRENCY,
        extra_currencies=state.account_currencies(
            account_seed, transactions, symbol_map
        ),
    )
    holdings = valuation.holdings_at(portfolio, when, price_table[when])

    Console().print(display.render(summary, holdings))


@cli.command()
@click.option("--root", default=DEFAULT_ROOT, show_default=True)
@click.option("--historical", default=DEFAULT_HISTORICAL, show_default=True)
@click.option("--output", "-o", default=None, help="Defaults to <root>/nav.html")
def report(root: str, historical: str, output):
    """Write a self-contained HTML dashboard."""
    import pandas as pd

    from nav import display, ingest
    from nav import prices as prices_module
    from nav import report as report_module
    from nav import state, valuation

    p, symbol_map, account_seed, transactions, portfolio = state.load_state(root)
    frame = ingest.load_frame(p["nav_daily"])
    if frame is None or frame.empty:
        # `.empty` as well as None: an empty nav_daily.parquet on disk is
        # not "data", and testing only for None let the file's mere
        # existence route past this message into an IndexError.
        raise click.ClickException("No NAV data. Run `nav sync` first.")

    when = pd.Timestamp(frame.iloc[-1]["date"]).to_pydatetime()
    history = state.read_historical(historical)
    price_table, _ = prices_module.build_price_table(
        history, state.held_tickers(account_seed, transactions), symbol_map, [when],
        state.BASE_CURRENCY,
        extra_currencies=state.account_currencies(
            account_seed, transactions, symbol_map
        ),
    )
    holdings = valuation.holdings_at(portfolio, when, price_table[when])

    payload = report_module.build_payload(frame, holdings, display.summarize(frame))
    destination = output or os.path.join(root, "nav.html")
    with open(destination, "w", encoding="utf-8") as fout:
        fout.write(report_module.render_html(payload))
    click.echo("Wrote {}".format(destination))


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
    from nav import state

    p, symbol_map, account_seed, transactions, portfolio = state.load_state(root)
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
            pd.read_parquet(historical),
            state.held_tickers(account_seed, transactions),
        )
        if moves:
            click.echo("\nPossible corporate actions (single-day moves over 40%):")
            for move in moves:
                click.echo(
                    "  {:<12} {}  {:+.1%}".format(move["symbol"], move["date"], move["ratio"])
                )

    if differences:
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
