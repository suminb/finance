from datetime import datetime
import pytz

import pytest

from finance.ext.warehouse import Portfolio, make_combination_indices


def assert_equals_dict_of_float(d1: dict, d2: dict):
    assert d1.keys() == d2.keys()
    for k in d1.keys():
        assert abs(d1[k] - d2[k]) < 1e-6


@pytest.mark.parametrize(
    ["indices", "r", "static_indices", "expected"],
    [
        ([1, 2, 3, 4], 1, [], [[1], [2], [3], [4]]),
        ([1, 2, 3], 2, [], [[1, 2], [1, 3], [2, 3]]),
        ([5, 4, 3], 3, [], [[5, 4, 3]]),
        (
            "abcd",
            2,
            [],
            [["a", "b"], ["a", "c"], ["a", "d"], ["b", "c"], ["b", "d"], ["c", "d"]],
        ),
        ([1, 2, 3, 4], 2, [1], [[1, 2], [1, 3], [1, 4]]),
        ([1, 2, 3, 4], 3, [2, 3], [[2, 3, 1], [2, 3, 4]]),
    ],
)
def test_make_combination_indices(indices, r, static_indices, expected):
    assert make_combination_indices(indices, r, static_indices) == expected


def parse_dt(str_dt, tz=pytz.timezone("America/New_York")):
    return datetime.strptime(str_dt + " 00:00:00", "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=tz
    )


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
p1 = Portfolio(inventory, current_prices, target)


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
