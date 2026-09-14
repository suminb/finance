"""Terminal rendering of the NAV series."""

from datetime import datetime
from typing import List, Optional

import pandas as pd
from rich.console import Group
from rich.table import Table


def summarize(frame: pd.DataFrame, when: Optional[datetime] = None) -> dict:
    """One day's figures, with the change against the preceding row."""
    if when is None:
        index = len(frame) - 1
    else:
        matches = frame.index[frame["date"] == when].tolist()
        if not matches:
            raise KeyError("No NAV row for {}".format(when))
        index = matches[0]

    row = frame.iloc[index]
    previous = frame.iloc[index - 1] if index > 0 else None
    change = 0.0 if previous is None else float(row["nav_krw"] - previous["nav_krw"])
    change_pct = (
        0.0
        if previous is None or previous["nav_krw"] == 0
        else change / float(previous["nav_krw"])
    )
    stale = [s for s in str(row["stale"]).split(",") if s]

    return {
        "date": row["date"],
        "nav_krw": float(row["nav_krw"]),
        "nav_usd": float(row["nav_usd"]),
        "change_krw": change,
        "change_pct": change_pct,
        "fx_usdkrw": float(row["fx_usdkrw"]),
        "stale": stale,
    }


def render(summary: dict, holdings: List[dict]) -> Group:
    arrow = "▲" if summary["change_krw"] > 0 else ("▼" if summary["change_krw"] < 0 else "=")
    colour = "green" if summary["change_krw"] > 0 else ("red" if summary["change_krw"] < 0 else "white")

    header = Table.grid(padding=(0, 2))
    header.add_column(justify="right")
    header.add_column()
    header.add_row("date", str(pd.Timestamp(summary["date"]).date()))
    header.add_row("NAV", "{:,.0f} KRW".format(summary["nav_krw"]))
    header.add_row("", "{:,.2f} USD".format(summary["nav_usd"]))
    header.add_row(
        "change",
        "[{}]{} {:,.0f} KRW ({:+.2%})[/{}]".format(
            colour, arrow, abs(summary["change_krw"]), summary["change_pct"], colour
        ),
    )
    header.add_row("USDKRW", "{:,.2f}".format(summary["fx_usdkrw"]))
    if summary["stale"]:
        header.add_row("[yellow]stale[/yellow]", ", ".join(summary["stale"]))

    table = Table(title="Holdings")
    table.add_column("ticker")
    table.add_column("quantity", justify="right")
    table.add_column("price (KRW)", justify="right")
    table.add_column("value (KRW)", justify="right")
    table.add_column("weight", justify="right")
    for holding in holdings:
        table.add_row(
            holding["ticker"],
            "{:,.4f}".format(holding["quantity"]).rstrip("0").rstrip("."),
            "{:,.2f}".format(holding["price_krw"]),
            "{:,.0f}".format(holding["value_krw"]),
            "{:.1%}".format(holding["weight"]),
        )

    return Group(header, "", table)
