import os
import pytz
import pytest

from finance.ext.models import Portfolio


def assert_equals_dict_of_float(d1: dict, d2: dict):
    assert d1.keys() == d2.keys()
    for k in d1.keys():
        assert abs(d1[k] - d2[k]) < 1e-6


@pytest.mark.skipif(
    not os.path.exists("notebooks/historical/US.parquet"),
    reason="Data file does not exist",
)
def test_portfolio():
    pf = Portfolio.load_from_file("tests/samples/portfolio1.yml", {})
    pf.eval_inventory()
    assert pf.inventory == {"QQQ": 6, "SCHD": 70, "SCHH": 10, "TLT": 15}

    import pandas as pd
    from finance.utils import parse_date

    historical = pd.read_parquet("notebooks/historical/US.parquet")
    from_date = parse_date("2023-10-01").replace(tzinfo=pytz.utc)
    to_date = parse_date("2023-10-30").replace(tzinfo=pytz.utc)
    pf.eval_daily_nav(from_date, to_date, historical)


# TODO: Diversify test scenarios
inventory = {
    "SPY": 50,
    "TLT": 45,
    "ARKW": 500,
    "REMX": 100,
    "_USD": 10000,
}
current_prices = {
    "SPY": 436.04,
    "TLT": 86.2,
    "ARKW": 52.64,
    "REMX": 63.25,
    "GDX": 28.95,
    "_USD": 1,
}
target = {
    "SPY": 4,
    "TLT": 3,
    "GDX": 2,
    "ARKW": 1,
    "_USD": 1,
}
p1 = Portfolio(current_prices, target, [])
p1.inventory = inventory


def test_portfolio_asset_values():
    assert_equals_dict_of_float(
        p1.asset_values,
        {
            "SPY": 21802.0,
            "TLT": 3879.0,
            "ARKW": 26320.0,
            "REMX": 6325.0,
            "_USD": 10000,
        },
    )


def test_portfolio_net_asset_value():
    assert p1.net_asset_value == 68326


def test_portfolio_current_weights():
    assert_equals_dict_of_float(
        p1.current_weights,
        {
            "ARKW": 0.3852120715393847,
            "REMX": 0.09257091004888329,
            "SPY": 0.3190879021163247,
            "TLT": 0.056771946257647164,
            "_USD": 0.14635717003776014,
        },
    )


def test_portfolio_calc_diff():
    assert_equals_dict_of_float(
        p1.calc_diff(),
        {
            "SPY": -0.04454846152003894,
            "ARKW": 0.2943029806302938,
            "TLT": -0.21595532646962554,
            "GDX": -0.18181818181818182,
            "REMX": 0.09257091004888329,
            "_USD": 0.055448079128669225,
        },
    )


@pytest.mark.skip
def test_portfolio_make_rebalancing_plan():
    assert_equals_dict_of_float(
        p1.make_rebalancing_plan(),
        {
            "SPY": 6,
            "ARKW": -382,
            "TLT": 171,
            "GDX": 429,
            "REMX": -100,
        },
    )


@pytest.mark.skip
def test_portfolio_apply_plan():
    plan = p1.make_rebalancing_plan()
    p1.apply_plan(plan, parse_dt("2023-01-03"), parse_dt("2023-01-05"), {})
    assert_equals_dict_of_float(
        p1.inventory,
        {
            "SPY": 56,
            "TLT": 216,
            "ARKW": 118,
            "REMX": 0,
            "GDX": 429,
            "_USD": 6657.49,
        },
    )
    expected_usd = (target["_USD"] / sum(target.values())) * p1.net_asset_value
    assert 0.9 < p1.inventory["_USD"] / expected_usd < 1.1
