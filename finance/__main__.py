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


@cli.command()
@click.argument("tickers_source")
@click.argument("historical_source")
@click.argument("tickers_target")
@click.argument("historical_target")
@click.option("-r", "--region", default="US", help="Region")
@click.option(
    "-s", "--strategy", default="oldest", help="all | oldest | random | static"
)
@click.option("-k", "--sample-count", default=25)
@click.option("--symbols", type=str)
def refresh_tickers(
    tickers_source: str,
    historical_source: str,
    tickers_target: str,
    historical_target: str,
    region,
    strategy: str,
    sample_count: int,
    symbols: str,
):
    """Refreshes tickers and historical data.

    :param source: Source file name
    :param symbols: Comma separated strings (without spaces in between)
    """
    import random
    import pandas as pd
    from finance.ext.warehouse import refresh_tickers_and_historical_data

    tickers = pd.read_parquet(tickers_source)
    tickers = tickers[(tickers.status != "delisted") & (tickers.status != "invalid")]
    if strategy == "all":
        symbols_ = tickers["symbol"].to_list()
    elif strategy == "oldest":
        symbols_ = tickers.sort_values("updated_at")["symbol"].to_list()
        symbols_ = symbols_[:sample_count]
    elif strategy == "random":
        symbols_ = tickers["symbol"].to_list()
        symbols_ = random.sample(symbols_, sample_count)
    elif strategy == "static":
        symbols_ = symbols.split(",")
    else:
        raise NotImplementedError(f"Strategy: {strategy}")

    refresh_tickers_and_historical_data(
        region,
        tickers,
        historical_source,
        tickers_target,
        historical_target,
        symbols_,
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
