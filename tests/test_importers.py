from finance.importers import import_miraeasset_foreign_records


def test_import_miraeasset_foreign_records(
    asset_usd, asset_krw, account_stock, stock_assets, stock_asset_spy,
    stock_asset_amzn, stock_asset_nvda, stock_asset_amd, stock_asset_sbux
):
    with open('tests/samples/miraeasset_foreign.csv') as fin:
        import_miraeasset_foreign_records(fin, account_stock)
