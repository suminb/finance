"""CLI commands for finance data processing (no database dependency)."""

import os
from typing import List

import click
from logbook import Logger

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
log = Logger("finance")


@click.group()
def cli():
    """Finance data processing CLI."""
    pass


@cli.group()
def refresh_tickers():
    """Refreshes tickers and historical data."""
    pass


def _refresh_tickers_common(
    region: str,
    tickers_input: str,
    historical_output: str,
    staging_dir: str,
    symbols_list: List[str],
):
    """Common logic for all refresh-tickers subcommands."""
    import pandas as pd
    from finance.ext.warehouse import refresh_tickers_and_historical_data

    tickers = pd.read_parquet(tickers_input)
    tickers = tickers[(tickers.status != "delisted") & (tickers.status != "invalid")]

    # Use tickers_input as output if not specified otherwise
    tickers_output = tickers_input

    refresh_tickers_and_historical_data(
        region,
        tickers,
        staging_dir,
        tickers_output,
        historical_output,
        symbols_list,
    )


@refresh_tickers.command()
@click.argument("symbols", nargs=-1, required=True)
@click.option(
    "--output", "-o", required=True, help="Output parquet file for historical data"
)
@click.option(
    "--tickers", default="tickers.parquet", help="Input/output tickers parquet file"
)
@click.option(
    "--staging-dir", default=".", help="Staging directory for intermediate files"
)
@click.option("--region", "-r", default="US", help="Region code (e.g., US, KR)")
def static(symbols: tuple, output: str, tickers: str, staging_dir: str, region: str):
    """Refresh specific ticker symbols.

    Example:
        finance refresh-tickers static SPY IVI QQQ --output US.parquet
    """
    symbols_list = list(symbols)
    _refresh_tickers_common(region, tickers, output, staging_dir, symbols_list)


@refresh_tickers.command()
@click.option("--count", "-n", default=25, help="Number of random tickers to sample")
@click.option(
    "--output", "-o", required=True, help="Output parquet file for historical data"
)
@click.option(
    "--tickers", default="tickers.parquet", help="Input/output tickers parquet file"
)
@click.option(
    "--staging-dir", default=".", help="Staging directory for intermediate files"
)
@click.option("--region", "-r", default="US", help="Region code (e.g., US, KR)")
def random(count: int, output: str, tickers: str, staging_dir: str, region: str):
    """Refresh a random sample of tickers.

    Example:
        finance refresh-tickers random --count 50 --output US.parquet
    """
    import random as random_module
    import pandas as pd

    tickers_df = pd.read_parquet(tickers)
    tickers_df = tickers_df[
        (tickers_df.status != "delisted") & (tickers_df.status != "invalid")
    ]
    symbols_list = tickers_df["symbol"].to_list()
    symbols_list = random_module.sample(symbols_list, count)

    _refresh_tickers_common(region, tickers, output, staging_dir, symbols_list)


@refresh_tickers.command()
@click.option("--count", "-n", default=25, help="Number of oldest tickers to refresh")
@click.option(
    "--output", "-o", required=True, help="Output parquet file for historical data"
)
@click.option(
    "--tickers", default="tickers.parquet", help="Input/output tickers parquet file"
)
@click.option(
    "--staging-dir", default=".", help="Staging directory for intermediate files"
)
@click.option("--region", "-r", default="US", help="Region code (e.g., US, KR)")
def oldest(count: int, output: str, tickers: str, staging_dir: str, region: str):
    """Refresh the oldest (most stale) tickers based on updated_at timestamp.

    Example:
        finance refresh-tickers oldest --count 30 --output US.parquet
    """
    import pandas as pd

    tickers_df = pd.read_parquet(tickers)
    tickers_df = tickers_df[
        (tickers_df.status != "delisted") & (tickers_df.status != "invalid")
    ]
    symbols_list = tickers_df.sort_values("updated_at")["symbol"].to_list()
    symbols_list = symbols_list[:count]

    _refresh_tickers_common(region, tickers, output, staging_dir, symbols_list)


@refresh_tickers.command()
@click.option(
    "--output", "-o", required=True, help="Output parquet file for historical data"
)
@click.option(
    "--tickers", default="tickers.parquet", help="Input/output tickers parquet file"
)
@click.option(
    "--staging-dir", default=".", help="Staging directory for intermediate files"
)
@click.option("--region", "-r", default="US", help="Region code (e.g., US, KR)")
def all(output: str, tickers: str, staging_dir: str, region: str):
    """Refresh all tickers in the database.

    Example:
        finance refresh-tickers all --output US.parquet
    """
    import pandas as pd

    tickers_df = pd.read_parquet(tickers)
    tickers_df = tickers_df[
        (tickers_df.status != "delisted") & (tickers_df.status != "invalid")
    ]
    symbols_list = tickers_df["symbol"].to_list()

    _refresh_tickers_common(region, tickers, output, staging_dir, symbols_list)


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
    """Pre-screen stocks based on some pre-defined criteria"""
    from functools import partial
    import pandas as pd
    import polars as pl
    from finance.ext.warehouse import (
        make_combination_indices,
        calc_pairwise_correlations,
        calc_overall_correlation,
        filter_tickers,
        map_sector_indices,
    )

    tickers = pl.read_parquet(tickers_source)
    filtered_tickers = filter_tickers(tickers, region)

    sectors = list(set(filtered_tickers["sector"]))
    sector_index_map = dict(zip(sectors, range(len(sectors))))

    # TODO: Support 'static_symbols' option
    static_symbols: List[str] = []

    symbols = list(filtered_tickers["symbol"]) + static_symbols
    symbol_indices = tickers.filter(pl.col("symbol").is_in(symbols))[
        "__index_level_0__"
    ]
    assert len(symbols) == len(symbol_indices)

    symbol_index_map = dict(zip(symbols, symbol_indices))

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

    historical["symbol_index"] = historical["symbol"].apply(symbol_index_map.get)

    historical_by_symbols = historical.pivot(columns="symbol_index", values="close")
    log.info(f"historical_by_symbols.shape = {historical_by_symbols.shape}")

    static_indices = [symbols.index(s) for s in static_symbols]

    os.makedirs(prescreening_target, exist_ok=True)
    combination_indices_with_partition = make_combination_indices(
        list(symbol_indices), static_indices, r, partitions
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
                "combination_indices": pl.Array(pl.UInt32, r),
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

        log.info("Mapping sector indicies...")
        prescreening = prescreening.with_columns(
            pl.col("combination_indices")
            .map_elements(partial(map_sector_indices, tickers, sector_index_map))  # type: ignore[attr-defined]
            .alias("sector_indices")
        )

        log.info("Determining if duplicated sectors exist...")
        prescreening = prescreening.with_columns(
            pl.col("sector_indices")
            .map_elements(lambda x: len(set(x)) != len(x))  # type: ignore[attr-defined]
            .alias("has_duplicated_sectors")
        )

        log.info(f"Saving prescreening results to '{prescreening_target}'")
        prescreening.write_parquet(
            prescreening_target,
            use_pyarrow=True,
            pyarrow_options={"partition_cols": ["__partition__"]},
        )


if __name__ == "__main__":
    cli()
