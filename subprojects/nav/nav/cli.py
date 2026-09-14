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
