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


if __name__ == "__main__":
    cli()
