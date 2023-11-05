import json
import os

import click
from click.testing import CliRunner
from logbook import Logger
from sqlalchemy.exc import IntegrityError

from finance.importers import (
    import_stock_values as import_stock_values_,
)  # Avoid name clashes
from finance.models import (
    Account,
    AccountType,
    Asset,
    AssetType,
    AssetValue,
    Base,
    DartReport,
    engine,
    get_asset_by_fund_code,
    Granularity,
    Portfolio,
    session,
    Transaction,
    User,
)
from finance.providers import Dart, Kofia, Yahoo
from finance.utils import (
    date_to_datetime,
    extract_numbers,
    insert_stock_record,
    parse_date,
    parse_stock_records,
    serialize_datetime,
)

from typing import List

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
log = Logger("finance")


def insert_stock_assets():
    """NOTE: This is a temporary workaround. All stock informaion shall be
    fetched automatically on the fly.
    """
    rows = [
        ("036570.KS", "NCsoft Corporation"),
        ("145210.KS", "SAEHWA IMC"),
        ("069080.KQ", "Webzen"),
        ("053800.KQ", "Ahnlab Inc."),
        ("017670.KS", "SK Telecom Co. Ltd."),
        ("005380.KS", "Hyundai Motor Company"),
        ("056080.KQ", "Yujin Robot Co., Ltd."),
        ("069500.KS", "KODEX 200"),
        ("009830.KS", "한화케미칼"),
    ]

    for code, description in rows:
        log.info("Inserting {} ({})...", code, description)
        yield Asset.create(
            type="stock", code=code, description=description, ignore_if_exists=True
        )


@click.group()
def cli():
    pass


@cli.command()
def create_all():
    """Creates necessary database tables."""
    Base.metadata.create_all(engine)


@cli.command()
def drop_all():
    """Drops all database tables."""
    Base.metadata.drop_all(engine)


def create_account(type_: AccountType, institution: str, number: str, user):
    return Account.create(
        type=type_,
        name="Test account",
        institution=institution,
        number=number,
        user=user,
        ignore_if_exists=True,
    )


def create_asset(type_: AssetType, code: str, description: str):
    return Asset.create(
        type=type_, code=code, description=description, ignore_if_exists=True
    )


@cli.command()
def insert_test_data():
    """Inserts some sample data for testing."""
    user = User.create(
        family_name="Byeon",
        given_name="Sumin",
        email="suminb@gmail.com",
        ignore_if_exists=True,
    )

    account_checking = create_account(AccountType.checking, "Shinhan", "checking", user)
    account_stock = create_account(AccountType.investment, "Mirae Asset", "stock", user)

    asset_krw = create_asset(AssetType.currency, "KRW", "Korean Won")
    create_asset(AssetType.currency, "USD", "United States Dollar")

    for _ in insert_stock_assets():
        pass

    create_asset(AssetType.security, "KR5223941018", "KB S&P500")
    create_asset(AssetType.security, "KR5229221225", "이스트스프링차이나")

    portfolio = Portfolio()
    portfolio.base_asset = asset_krw
    portfolio.add_accounts(account_checking, account_stock)


@cli.command()
def import_sp500_asset_values():
    runner = CliRunner()
    runner.invoke(
        import_fund, ["KR5223941018", "2015-01-01", "2016-06-01"], catch_exceptions=True
    )


@cli.command()
def import_sp500_records():
    """Import S&P500 fund sample data. Expects a tab seprated value document."""
    account_checking = Account.get(id=1001)
    account_sp500 = Account.get(id=7001)
    asset_krw = Asset.query.filter_by(name="KRW").first()
    asset_sp500 = Asset.query.filter_by(name="KB S&P500").first()

    # Expected number of columns
    expected_col_count = 6

    with open("sample-data/sp500.csv") as fin:
        # Skip the first row (headers)
        headers = next(fin)
        col_count = len(headers.split())
        if col_count != expected_col_count:
            raise Exception(
                "Expected number of columns = {}, "
                "actual number of columns = {}".format(expected_col_count, col_count)
            )

        for line in fin:
            cols = line.split("\t")
            if len(cols) != expected_col_count:
                continue
            date = parse_date(cols[0], "%Y.%m.%d")
            _type = cols[1]
            quantity_krw, quantity_sp500 = [int(extract_numbers(v)) for v in cols[3:5]]

            log.info(", ".join([c.strip() for c in cols]))

            if not (_type == "일반입금" or _type == "일반신규"):
                log.info("Record type '{}' will be ignored", _type)
                continue

            with Transaction.create() as t:
                # NOTE: The actual deposit date and the buying date generally
                # differ by a few days. Need to figure out how to parse this
                # properly from the raw data.
                try:
                    deposit(account_checking, asset_krw, -quantity_krw, date, t)
                except IntegrityError:
                    log.warn("Identical record exists")
                    session.rollback()

                try:
                    deposit(account_sp500, asset_sp500, quantity_sp500, date, t)
                except IntegrityError:
                    log.warn("Identical record exists")
                    session.rollback()


@cli.command()
@click.argument("stock_code")  # e.g., NVDA, 027410.KS
@click.option("-s", "--start", "start_date", help="Start date (e.g., 2017-01-01)")
@click.option("-e", "--end", "end_date", help="End date (e.g., 2017-12-31)")
def fetch_stock_values(stock_code, start_date, end_date):
    """Fetches daily stock values from Yahoo Finance."""

    start_date = date_to_datetime(
        parse_date(start_date if start_date is not None else -30 * 3600 * 24)
    )
    end_date = date_to_datetime(parse_date(end_date if end_date is not None else 0))

    if start_date > end_date:
        raise ValueError("start_date must be equal to or less than end_date")

    provider = Yahoo()
    rows = provider.asset_values(stock_code, start_date, end_date, Granularity.day)

    for row in rows:
        # TODO: Write a function to handle this for generic cases
        # TODO: Convert the timestamp to an ISO format
        # NOTE: The last column is data source. Not sure if this is an elegant
        # way to handle this.

        # FIXME: Think of a better way to handle this
        dt = row[0].isoformat()

        print(", ".join([dt] + [str(c) for c in row[1:]] + ["yahoo"]))


# NOTE: This will probably be called by AWS Lambda
# TODO: Load data from stdin
@cli.command()
@click.argument("code")
@click.argument("from-date")
@click.argument("to-date")
def import_fund(code, from_date, to_date):
    """Imports fund data from KOFIA.

    :param code: e.g., KR5223941018
    :param from_date: e.g., 2016-01-01
    :param to_date: e.g., 2016-02-28
    """
    provider = Kofia()
    asset = get_asset_by_fund_code(code)

    # FIXME: Target asset should also be determined by asset.data.code
    base_asset = Asset.query.filter_by(name="KRW").first()

    data = provider.fetch_data(code, parse_date(from_date), parse_date(to_date))
    for date, unit_price, quantity in data:
        log.info("Import data on {}", date)
        unit_price /= 1000.0
        try:
            AssetValue.create(
                asset=asset,
                base_asset=base_asset,
                evaluated_at=date,
                close=unit_price,
                granularity=Granularity.day,
                source="kofia",
            )
        except IntegrityError:
            log.warn("Identical record has been found for {}. Skipping.", date)
            session.rollback()


@cli.command()
@click.argument("code")
def import_stock_values(code):
    """Import stock price information."""
    # NOTE: We assume all Asset records are already in the database, but
    # this is a temporary workaround. We should implement some mechanism to
    # automatically insert an Asset record when it is not found.

    stdin = click.get_text_stream("stdin")
    for _ in import_stock_values_(stdin, code):
        pass


# TODO: Load data from stdin
@cli.command()
@click.argument("filename")
def import_stock_records(filename):
    """Parses exported data from the Shinhan HTS."""
    account_bank = Account.query.filter(Account.name == "신한 입출금").first()
    account_stock = Account.query.filter(Account.name == "신한 주식").first()
    with open(filename) as fin:
        for parsed in parse_stock_records(fin):
            insert_stock_record(parsed, account_stock, account_bank)


@cli.command()
@click.argument("tickers_source")
@click.argument("historical_source")
@click.argument("tickers_target")
@click.argument("historical_target")
@click.option("-r", "--region", default="US", help="Region")
def refresh_tickers(
    tickers_source, historical_source, tickers_target, historical_target, region
):
    """Refreshes tickers.

    :param source: Source file name
    """
    from finance.ext.warehouse import refresh_tickers_and_historical_data

    refresh_tickers_and_historical_data(
        region, tickers_source, historical_source, tickers_target, historical_target
    )


@cli.command()
@click.argument("tickers_source")
@click.argument("historical_source")
@click.argument("prescreening_target")
@click.argument("r", type=int)
@click.option("-r", "--region", default="US", help="Region")
@click.option("-p", "--partitions", default=32, help="Number of partitions")
def prescreen(
    tickers_source: str,
    historical_source: str,
    prescreening_target: str,
    r: int,
    region: str,
    partitions: int,
):
    from functools import partial
    import pandas as pd
    import polars as pl
    from finance.ext.warehouse import (
        make_combination_indices,
        calc_pairwise_correlations,
        calc_overall_correlation,
    )

    tickers = pl.read_parquet(tickers_source)

    # US ETFs only
    tickers = tickers.filter((tickers["quote_type"] == "ETF") & (tickers["region"] == region))

    # Filter by market cap
    tickers = tickers.filter(tickers["market_cap"] >= 5e9)

    # Exclude leveraged ETFs
    tickers = tickers.filter(
        ~tickers["name"].str.contains("2X") & ~tickers["name"].str.contains("3X")
    )

    # TODO: Support 'static_symbols' option
    static_symbols: List[str] = []
    symbols = list(tickers["symbol"]) + static_symbols

    historical = pd.read_parquet(historical_source)

    # TODO: Take date range as parameters
    # Takes recent data only
    historical.drop(historical[historical.date < "2018-01-01"].index, inplace=True)

    historical.drop(historical[~historical.symbol.isin(symbols)].index, inplace=True)

    historical["date"] = pd.to_datetime(historical.date).dt.tz_localize(None)
    historical.set_index("date", inplace=True)

    # Drop unneccessary columns
    historical.drop(["open", "high", "low", "updated_at"], axis=1, inplace=True)
    if "__index_level_0__" in historical.columns:
        historical.drop(["__index_level_0__"], axis=1, inplace=True)

    historical["symbol_index"] = historical["symbol"].apply(symbols.index)

    historical_by_symbols = historical.pivot(columns="symbol_index", values="close")
    log.info(f"historical_by_symbols.shape = {historical_by_symbols.shape}")

    static_indices = [symbols.index(s) for s in static_symbols]

    os.makedirs(prescreening_target, exist_ok=True)
    combination_indices_with_partition = make_combination_indices(
        list(range(len(symbols))), static_indices, r, partitions
    )
    for p in range(partitions):
        try:
            combination_indices = next(combination_indices_with_partition)
        except StopIteration:
            break

        log.debug(
            f"Making a dataframe with {len(combination_indices)} combination indices..."
        )
        prescreening = pl.DataFrame(
            {
                "combination_indices": combination_indices,
                "__partition__": [p for _ in combination_indices],
            },
            schema={
                "combination_indices": pl.Array(r, pl.UInt32),
                "__partition__": pl.UInt16,
            },
        )

        log.info("Calculating pairwise correlations...")
        prescreening = prescreening.with_columns(
            pl.col("combination_indices")
            .map_batches(partial(calc_pairwise_correlations, historical_by_symbols))
            .alias("pairwise_correlations")
        )

        log.info("Calculating overall correlations...")
        prescreening = prescreening.with_columns(
            pl.col("pairwise_correlations")
            .map_batches(calc_overall_correlation)
            .alias("overall_correlation")
        )

        log.info(f"Saving prescreening results to '{prescreening_target}'")
        prescreening.write_parquet(
            prescreening_target,
            use_pyarrow=True,
            pyarrow_options={"partition_cols": ["__partition__"]},
        )


if __name__ == "__main__":
    cli()
