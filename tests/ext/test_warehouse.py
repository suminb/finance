from finance.ext.warehouse import Portfolio


# TODO: Diversify test scenarios
inventory = {
    "SPY": 50,
    "TLT": 45,
    "ARKW": 500,
    "REMX": 100,
}
current_prices = {
    "SPY": 436.04,
    "TLT": 86.2,
    "ARKW": 52.64,
    "REMX": 63.25,
    "GDX": 28.95,
}
target = {
    "SPY": 4,
    "TLT": 3,
    "GDX": 2,
    "ARKW": 1,
}
p1 = Portfolio(inventory, current_prices, target, 0)


def test_portfolio_asset_values():
    assert p1.asset_values == {
        "SPY": 21802.0,
        "TLT": 3879.0,
        "ARKW": 26320.0,
        "REMX": 6325.0,
    }


def test_portfolio_net_asset_value():
    assert p1.net_asset_value == 58326


def test_portfolio_current_weights():
    assert p1.current_weights == {
        "ARKW": 0.45125672941741246,
        "REMX": 0.10844220416280904,
        "SPY": 0.3737955628707609,
        "TLT": 0.06650550354901759,
    }


def test_portfolio_calc_diff():
    assert p1.calc_diff() == {
        "SPY": -0.026204437129239144,
        "ARKW": 0.3512567294174125,
        "TLT": -0.23349449645098241,
        "GDX": -0.2,
        "REMX": 0.10844220416280904,
    }


def test_portfolio_make_rebalancing_plan():
    assert p1.make_rebalancing_plan() == {
        "SPY": 3,
        "ARKW": -389,
        "TLT": 157,
        "GDX": 402,
        "REMX": -100,
    }


def test_portfolio_apply_plan():
    plan = p1.make_rebalancing_plan()
    p1.apply_plan(plan)
    assert p1.inventory == {
        "SPY": 53,
        "TLT": 202,
        "ARKW": 111,
        "REMX": 0,
        "GDX": 402,
    }
    assert p1.cash_balance >= 0