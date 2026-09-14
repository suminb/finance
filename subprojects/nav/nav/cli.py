"""Command line interface for nav."""

import os

import click

DEFAULT_ROOT = os.environ.get("NAV_ROOT", "subprojects/nav")


def _paths(root):
    return {
        "symbols": os.path.join(root, "symbols.yaml"),
        "categories": os.path.join(root, "categories.yaml"),
        "seed": os.path.join(root, "seed.yaml"),
        "transaction": os.path.join(root, "data", "transaction.parquet"),
        "nav_daily": os.path.join(root, "data", "nav_daily.parquet"),
    }


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

    history = pd.read_parquet(historical)
    tickers = _held_tickers(account_seed, transactions)
    price_table, _ = prices_module.build_price_table(
        history, tickers, symbol_map, [when], "KRW", extra_currencies=["USD"]
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


if __name__ == "__main__":
    cli()
