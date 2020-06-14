import csv
from functools import partial

import pytest

from finance.importers import import_stock_values
from finance.models import (
    engine as _engine,
    session as _session,
)
from finance.models import (
    Account,
    AccountType,
    Asset,
    AssetType,
    Base,
    CurrencyAsset,
    FundAsset,
    P2PBondAsset,
    Portfolio,
    StockAsset,
)


@pytest.fixture(scope="module", autouse=True)
def session(request):
    """A database session. Shall not be confused with test sessions."""
    def teardown():
        _session.close()
        Base.metadata.drop_all(_engine)

    request.addfinalizer(teardown)

    Base.metadata.create_all(_engine)
    return _session


@pytest.fixture(scope="module")
def base_class():
    return Base


@pytest.fixture(scope="module")
def engine():
    return _engine


@pytest.fixture(scope="module")
def stock_assets():
    with open("tests/samples/stocks.csv") as fin:
        reader = csv.reader(fin, delimiter=",")
        for row in reader:
            isin, code, name = row
            if isin.startswith("#"):
                continue
            Asset.create(type=AssetType.stock, isin=isin, code=code, name=name)


@pytest.fixture(scope="function")
def account_checking(request):
    account = Account.create(type="checking", name="신한은행 입출금")
    request.addfinalizer(partial(teardown, record=account))
    return account


@pytest.fixture(scope="function")
def account_savings(request):
    account = Account.create(type="savings", name="신한은행 적금")
    request.addfinalizer(partial(teardown, record=account))
    return account


@pytest.fixture(scope="function")
def account_8p(request):
    account = Account.create(type="virtual", name="8퍼센트")
    request.addfinalizer(partial(teardown, record=account))
    return account


@pytest.fixture(scope="function")
def account_hf(request):
    account = Account.create(type="virtual", name="어니스트펀드")
    request.addfinalizer(partial(teardown, record=account))
    return account


@pytest.fixture(scope="function")
def account_sp500(request):
    account = Account.create(type="investment", name="S&P500 Fund")
    request.addfinalizer(partial(teardown, record=account))
    return account


@pytest.fixture(scope="function")
def account_stock(request):
    account = Account.create(
        type=AccountType.investment,
        institution="Miraeasset",
        number="ACCOUNT1",
        name="미래에셋대우 1",
    )
    request.addfinalizer(partial(teardown, record=account))
    return account


@pytest.fixture(scope="function")
def asset_hf1(request):
    asset = P2PBondAsset.create(name="포트폴리오 투자상품 1호")
    request.addfinalizer(partial(teardown, record=asset))
    assert asset.type == "p2p_bond"
    return asset


@pytest.fixture(scope="function")
def asset_krw(request):
    asset = CurrencyAsset.create(code="KRW", description="Korean Won")
    request.addfinalizer(partial(teardown, record=asset))
    return asset


@pytest.fixture(scope="function")
def asset_sp500(request):
    asset = FundAsset.create(
        name="KB Star S&P500", description="", data={"code": "KR5223941018"}
    )
    request.addfinalizer(partial(teardown, record=asset))
    return asset


@pytest.fixture(scope="function")
def asset_usd(request):
    asset = CurrencyAsset.create(code="USD", description="United States Dollar")
    request.addfinalizer(partial(teardown, record=asset))
    return asset


@pytest.fixture(scope="function")
def stock_asset_ncsoft(request):
    asset = StockAsset.create(
        name="NCsoft Corporation",
        code="036570.KS",
        description="NCsoft Corporation",
        data={"bps": 88772, "eps": 12416},
    )
    request.addfinalizer(partial(teardown, record=asset))
    return asset


@pytest.fixture(scope="function")
def stock_asset_spy(request, asset_usd):
    asset = StockAsset.create(
        name="SPY",
        code="SPY",
        isin="US78462F1030",
        description="SPDR S&P 500 ETF Trust Fund",
    )
    request.addfinalizer(partial(teardown, record=asset))

    with open("tests/samples/SPY.csv") as fin:
        for av in import_stock_values(fin, "SPY", base_asset=asset_usd):
            request.addfinalizer(partial(teardown, record=av))

    return asset


@pytest.fixture(scope="function")
def stock_asset_amd(request, asset_usd):
    asset = StockAsset.create(
        name="AMD",
        code="AMD",
        isin="US0079031078",
        description="Advanced Micro Devices, Inc",
    )
    request.addfinalizer(partial(teardown, record=asset))

    with open("tests/samples/AMD.csv") as fin:
        for av in import_stock_values(fin, "AMD", base_asset=asset_usd):
            request.addfinalizer(partial(teardown, record=av))

    return asset


@pytest.fixture(scope="function")
def stock_asset_nvda(request, asset_usd):
    asset = StockAsset.create(
        name="NVDA", code="NVDA", isin="US67066G1040", description="NVIDIA Corporation"
    )
    request.addfinalizer(partial(teardown, record=asset))

    with open("tests/samples/NVDA.csv") as fin:
        for av in import_stock_values(fin, "NVDA", base_asset=asset_usd):
            request.addfinalizer(partial(teardown, record=av))

    return asset


@pytest.fixture(scope="function")
def stock_asset_amzn(request, asset_usd):
    asset = StockAsset.create(
        name="AMZN", code="AMZN", isin="US0231351067", description="Amazon"
    )
    request.addfinalizer(partial(teardown, record=asset))

    with open("tests/samples/AMZN.csv") as fin:
        for av in import_stock_values(fin, "AMZN", base_asset=asset_usd):
            request.addfinalizer(partial(teardown, record=av))

    return asset


@pytest.fixture(scope="function")
def stock_asset_sbux(request, asset_usd):
    asset = StockAsset.create(
        name="SBUX", code="SBUX", isin="US8552441094", description="Starbucks"
    )
    request.addfinalizer(partial(teardown, record=asset))

    with open("tests/samples/SBUX.csv") as fin:
        for av in import_stock_values(fin, "SBUX", base_asset=asset_usd):
            request.addfinalizer(partial(teardown, record=av))

    return asset


@pytest.fixture(scope="function")
def portfolio(request, asset_krw, account_checking, account_sp500):
    p = Portfolio.create(base_asset=asset_krw)
    p.add_accounts(account_checking, account_sp500)

    def teardown():
        # NOTE: The following statement is necessary because the scope of
        # `asset_krw` is a module, whereas the scope of `p` is a function.
        p.base_asset = None
        _session.delete(p)
        _session.commit()

    request.addfinalizer(teardown)
    return p


def teardown(record):
    _session.delete(record)
    _session.commit()
