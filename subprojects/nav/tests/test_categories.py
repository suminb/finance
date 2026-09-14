from datetime import datetime, timezone
from decimal import Decimal

import pytest
import yaml

from nav import categories
from nav.model import Leg, Transaction

YAML = """
- {category: 현금매수, handler: buy}
- {category: 현금매도, handler: sell}
- {category: 입금, handler: cash_in}
- {category: 출금, handler: cash_out}
- {category: 배당금, handler: dividend}
- {category: 기타, handler: noop}
"""


@pytest.fixture
def category_map(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text(YAML, encoding="utf-8")
    return categories.load(str(path))


def make(category, **kwargs):
    defaults = dict(
        date=datetime(2026, 9, 1, tzinfo=timezone.utc),
        seq=1,
        category=category,
        name="애플",
        ticker="AAPL",
        currency="USD",
        amount=Decimal("1500.00"),
        unit_price=Decimal("150.00"),
        quantity=Decimal("10"),
        fees=Decimal("3.50"),
        tax=Decimal("0"),
        raw="[]",
    )
    defaults.update(kwargs)
    return Transaction(**defaults)


def test_buy_adds_shares_and_debits_cash(category_map):
    legs = category_map.legs_for(make("현금매수"))
    assert legs == [
        Leg("AAPL", Decimal("10")),
        Leg("_USD", Decimal("-1503.50")),
    ]


def test_sell_removes_shares_and_credits_cash_net_of_costs(category_map):
    legs = category_map.legs_for(
        make("현금매도", tax=Decimal("2.00"))
    )
    assert legs == [
        Leg("AAPL", Decimal("-10")),
        Leg("_USD", Decimal("1494.50")),
    ]


def test_dividend_credits_cash_net_of_tax(category_map):
    legs = category_map.legs_for(
        make("배당금", amount=Decimal("12.30"), tax=Decimal("1.84"),
             quantity=Decimal("0"), ticker="AAPL")
    )
    assert legs == [Leg("_USD", Decimal("10.46"))]


def test_cash_in_and_out_use_the_row_currency(category_map):
    assert category_map.legs_for(
        make("입금", currency="KRW", amount=Decimal("1000000"), ticker="", name="")
    ) == [Leg("_KRW", Decimal("1000000"))]
    assert category_map.legs_for(
        make("출금", currency="KRW", amount=Decimal("1000000"), ticker="", name="")
    ) == [Leg("_KRW", Decimal("-1000000"))]


def test_noop_produces_no_legs(category_map):
    assert category_map.legs_for(make("기타")) == []


def test_unknown_category_raises_with_stub(category_map):
    with pytest.raises(categories.UnknownCategoryError) as excinfo:
        category_map.legs_for(make("권리락"))
    assert excinfo.value.categories == ["권리락"]
    # Stub now has quotes around handler due to yaml.safe_dump
    assert "handler: '???'" in excinfo.value.stub
    # And the category should be present
    assert "권리락" in excinfo.value.stub


def test_validate_reports_every_unknown_category_at_once(category_map):
    with pytest.raises(categories.UnknownCategoryError) as excinfo:
        category_map.validate(["현금매수", "권리락", "액면분할"])
    assert excinfo.value.categories == ["권리락", "액면분할"]


def test_unknown_handler_name_is_rejected_at_load(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text("- {category: X, handler: teleport}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown handler"):
        categories.load(str(path))


def test_buy_without_a_ticker_is_rejected(category_map):
    with pytest.raises(ValueError, match="requires a ticker"):
        category_map.legs_for(make("현금매수", ticker=""))


def test_shipped_categories_file_loads():
    categories.load("subprojects/nav/categories.yaml")


@pytest.fixture
def category_map_with_all_handlers(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text("""
- {category: 현금매수, handler: buy}
- {category: 현금매도, handler: sell}
- {category: 입금, handler: cash_in}
- {category: 출금, handler: cash_out}
- {category: 배당금, handler: dividend}
- {category: 이자, handler: interest}
- {category: 수수료, handler: fee}
- {category: 기타, handler: noop}
""", encoding="utf-8")
    return categories.load(str(path))


def test_interest_credits_cash_net_of_tax(category_map_with_all_handlers):
    legs = category_map_with_all_handlers.legs_for(
        make("이자", amount=Decimal("25.00"), tax=Decimal("3.75"),
             quantity=Decimal("0"), ticker="")
    )
    assert legs == [Leg("_USD", Decimal("21.25"))]


def test_fee_debits_cash_with_amount_and_costs(category_map_with_all_handlers):
    legs = category_map_with_all_handlers.legs_for(
        make("수수료", amount=Decimal("10.00"), fees=Decimal("0.50"), tax=Decimal("0"),
             quantity=Decimal("0"), ticker="")
    )
    assert legs == [Leg("_USD", Decimal("-10.50"))]


def test_unknown_category_stub_is_valid_yaml(category_map):
    # pytest.raises, not a bare try/except: with the assertions inside an
    # except block, a legs_for() that stopped raising would make this test
    # pass having executed nothing at all. Its two siblings below already do
    # it this way.
    with pytest.raises(categories.UnknownCategoryError) as excinfo:
        category_map.legs_for(make("권리락"))
    parsed = yaml.safe_load(excinfo.value.stub)
    assert len(parsed) == 1
    assert parsed[0]["category"] == "권리락"
    assert parsed[0]["handler"] == "???"


def test_unknown_category_stub_with_special_characters_is_valid_yaml(category_map):
    # Test that the stub properly escapes category names with special characters
    with pytest.raises(categories.UnknownCategoryError) as excinfo:
        category_map.legs_for(make("category:with:colons"))

    # Parse the stub back to verify it's valid YAML
    parsed = yaml.safe_load(excinfo.value.stub)
    assert len(parsed) == 1
    assert parsed[0]["category"] == "category:with:colons"
    assert parsed[0]["handler"] == "???"


def test_unknown_category_stub_with_comma_is_valid_yaml(category_map):
    # Test that the stub properly escapes category names with commas
    with pytest.raises(categories.UnknownCategoryError) as excinfo:
        category_map.legs_for(make("category,with,comma"))

    # Parse the stub back to verify it's valid YAML
    parsed = yaml.safe_load(excinfo.value.stub)
    assert len(parsed) == 1
    assert parsed[0]["category"] == "category,with,comma"
    assert parsed[0]["handler"] == "???"


def test_duplicate_category_with_different_handler_is_rejected(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text("""
- {category: 현금매수, handler: buy}
- {category: 현금매수, handler: sell}
""", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate category"):
        categories.load(str(path))


def test_duplicate_category_with_same_handler_is_allowed(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text("""
- {category: 현금매수, handler: buy}
- {category: 현금매수, handler: buy}
""", encoding="utf-8")
    # Should not raise
    map_obj = categories.load(str(path))
    assert "현금매수" in map_obj._mapping
