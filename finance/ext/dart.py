# This is a temporary module.
#
# I want to make this module clean and neat but I honestly don't know where to
# start...

import json
import os

# TODO: We need a separate layer for making RESTful requests...
import requests


dart_access_key = os.environ.get("SBF_DART_KEY")


class FinancialStatementItem:
    def __init__(
        self,
        company_code: str,
        business_year: int,
        fs_type: str,
        fs_name: str,
        account_id: str,
        account_name: str,
        account_detail: str,
        term: str,
        amount: int,
        order: int):
        """
        :param fs_type: 재무제표구분 (BS : 재무상태표, IS: 손익계산서, CIS: 포괄손익계산서, CF: 현금흐름표, SCE: 자본변동표)
        """
        self.company_code = company_code
        self.business_year = business_year
        self.fs_type = fs_type
        self.fs_name = fs_name
        self.account_id = account_id
        self.account_name = account_name
        self.account_detail = account_detail
        self.term = term
        self.amount = amount
        self.order = order

    def __repr__(self):
        return f"{self.company_code}, {self.business_year}, {self.fs_name}, {self.account_name}: {self.amount}"


class FinancialStatement:
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"

    def fetch(self, company_code: str, business_year: int, report_code: str, fs: str):
        """
        :param report_code: 1분기보고서: 11013, 반기보고서 : 11012, 3분기보고서: 11014, 사업보고서: 11011
        :param fs: CFS:연결재무제표, OFS:재무제표
        """
        resp = requests.get(self.url, params={"crtfc_key": dart_access_key, "corp_code": company_code, "bsns_year": business_year, "reprt_code": report_code, "fs_div": fs})
        data = json.loads(resp.text)

        # FIXME: Replace with a proper error handling logic
        assert data["status"] == "000"

        return [
            FinancialStatementItem(
                company_code, business_year, item_dict["sj_div"],
                item_dict["sj_nm"], item_dict["account_id"],
                item_dict["account_nm"], item_dict["account_detail"],
                item_dict["thstrm_nm"], item_dict["thstrm_amount"],
                int(item_dict["ord"])
            ) for item_dict in data["list"]]