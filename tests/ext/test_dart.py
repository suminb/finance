import json

import pytest

from finance.ext.dart import (
    FinancialStatementItem,
    FinancialStatementParser,
    FinancialStatementRequest,
    OfficialFiling,
    OfficialFilingParser,
    OfficialFilingRequest,
    search_corporations,
)


def test_search_corporations():
    results = search_corporations("씨젠")
    assert len(results) == 1

    corp = results[0]
    assert "씨젠" == corp.name
    assert "00788773" == corp.dart_code
    assert "096530" == corp.stock_code


@pytest.mark.skip
def test_financial_statement_request():
    req = FinancialStatementRequest()
    results = req.fetch("00788773", 2020, "11012", "OFS")

    for item in results:
        assert FinancialStatementItem == type(item)
        assert "00788773" == item.corporation_code
        assert 2020 == item.business_year

    assert {"재무상태표", "포괄손익계산서", "현금흐름표", "자본변동표"} == set(
        item.fs_name for item in results
    )


def test_financial_statement_parser():
    with open("tests/samples/dart_financial_statements.json") as fin:
        json_object = json.loads(fin.read())
    parser = FinancialStatementParser(json_object, "00266961", 2020)

    assert dict == type(parser.statements)
    assert {"BS", "CIS", "CF", "SCE"} == set(parser.statements.keys())

    bs = parser.statements["BS"]
    cis = parser.statements["CIS"]
    cf = parser.statements["CF"]
    sce = parser.statements["SCE"]

    for _, item in bs.items():
        assert FinancialStatementItem == type(item)
        assert "00266961" == item.corporation_code
        assert 2020 == item.business_year
        assert "재무상태표" == item.fs_name
    for _, item in cis.items():
        assert FinancialStatementItem == type(item)
        assert "00266961" == item.corporation_code
        assert 2020 == item.business_year
        assert "포괄손익계산서" == item.fs_name
    for _, item in cf.items():
        assert FinancialStatementItem == type(item)
        assert "00266961" == item.corporation_code
        assert 2020 == item.business_year
        assert "현금흐름표" == item.fs_name
    for _, item in sce.items():
        assert FinancialStatementItem == type(item)
        assert "00266961" == item.corporation_code
        assert 2020 == item.business_year
        assert "자본변동표" == item.fs_name


@pytest.mark.skip
def test_official_filing_request():
    req = OfficialFilingRequest()
    filings = req.fetch("00266961", "20200101", "20200814")

    for filing in filings:
        assert OfficialFiling == type(filing)
        assert "00266961" == filing.corporation_code
        assert "NAVER" == filing.corporation_name


def test_official_filing_parser():
    with open("tests/samples/dart_official_filings.json") as fin:
        json_object = json.loads(fin.read())
    parser = OfficialFilingParser(json_object)

    for filing in parser.filings:
        assert OfficialFiling == type(filing)
        assert "00266961" == filing.corporation_code
        assert "NAVER" == filing.corporation_name
