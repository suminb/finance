from finance.ext.dart import FinancialStatementItem, FinancialStatementRequest, search_corporations


def test_search_corporations():
    results = search_corporations("씨젠")
    assert len(results) == 1

    corp = results[0]
    assert "씨젠" == corp.name
    assert "00788773" == corp.dart_code
    assert "096530" == corp.stock_code


def test_financial_statement():
    fs = FinancialStatementRequest()
    results = fs.fetch("00788773", 2020, "11012", "OFS")

    for item in results:
        assert FinancialStatementItem == type(item)
        assert "00788773" == item.corporation_code

    assert {"재무상태표", "포괄손익계산서", "현금흐름표", "자본변동표"} == set(item.account_name for item in results)
