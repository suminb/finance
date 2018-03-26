from decimal import Decimal

from finance.importers import import_miraeasset_foreign_records
from finance.models import Asset


def test_import_miraeasset_foreign_records(
    asset_usd, asset_krw, account_stock, stock_assets, stock_asset_spy,
    stock_asset_amzn, stock_asset_nvda, stock_asset_amd, stock_asset_sbux
):
    with open('tests/samples/miraeasset_foreign.csv') as fin:
        import_miraeasset_foreign_records(fin, account_stock)

    balance = account_stock.balance()
    balance_sheet = [
        ('USD', -483.39),
        ('AMD', 22),
        ('SPY', 5),
        ('SBUX', 2),
        ('AMZN', 3),
        ('NVDA', 13),
    ]
    for symbol, amount in balance_sheet:
        asset = Asset.get_by_symbol(symbol)
        assert balance[asset] == Decimal(str(amount))
