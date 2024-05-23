from finance.ext.models import Portfolio


def test_portfolio():
    pf = Portfolio.load_from_file("tests/samples/portfolio1.yml", {})
    pf.evaluate_inventory()
    assert pf.inventory == {"QQQ": 6, "SCHD": 70, "SCHH": 10, "TLT": 15}
