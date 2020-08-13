# This is a temporary module.
#
# I want to make this module clean and neat but I honestly don't know where to
# start...

import json
import os

# TODO: We need a separate layer for making RESTful requests...
import requests


dart_access_key = os.environ.get("SBF_DART_KEY")

# TODO: Company vs. corporation?


def load_corporation_list(file_path="data/dart_corporation_codes.json"):
    with open(file_path) as fin:
        for r in json.loads(fin.read())["result"]["list"]:
            yield CorporationInfo(r["corp_code"], r["stock_code"], r["corp_name"], r["modify_date"])


def search_corporations(query):
    """FIXME: This is a very inefficient linear search."""
    return [c for c in load_corporation_list() if query in c.name]


class CorporationInfo:
    def __init__(self, dart_code, stock_code, name, updated_at):
        self.dart_code = dart_code
        self.stock_code = stock_code
        self.name = name
        self.updated_at = updated_at

    def __repr__(self):
        return f"{self.name} ({self.stock_code})"


class OfficialFiling:
    def __init__(
        self,
        corporation_class,
        corporation_name,
        corporation_code,
        stock_code,
        title,
        receipt_number,
        receipt_datetime,
        filer_name,
        remark,
    ):
        self.corporation_class = corporation_class
        self.corporation_name = corporation_name
        self.corporation_code = corporation_code
        self.stock_code = stock_code
        self.title = title
        self.receipt_number = receipt_number
        self.receipt_datetime = receipt_datetime
        self.filer_name = filer_name
        self.remark = remark

    def __repr__(self):
        return f"{self.corporation_name}({self.corporation_class}), {self.title}"


class OfficialFilingRequest:
    url = "https://opendart.fss.or.kr/api/list.json"

    def fetch(self, corporation_code: str, start_datetime: str, end_datetime: str):
        resp = requests.get(
            self.url,
            params={
                "crtfc_key": dart_access_key,
                "corp_code": corporation_code,
                "bgn_de": start_datetime,
                "end_de": end_datetime,
                "page_count": 100,
            },
        )
        data = json.loads(resp.text)

        # FIXME: Replace with a proper error handling logic
        assert data["status"] == "000"

        # TODO: Handle pagination
        return [
            OfficialFiling(
                d["corp_cls"],
                d["corp_name"],
                d["corp_code"],
                d["stock_code"],
                d["report_nm"],
                d["rcept_no"],
                d["rcept_dt"],
                d["flr_nm"],
                d["rm"],
            )
            for d in data["list"]
        ]

        # {"status":"000","message":"정상","page_no":1,"page_count":10,"total_count":223,"total_page":23,"list":[{"corp_code":"00120182","corp_name":"NH투자증권","stock_code":"005940","corp_cls":"Y","report_nm":"[첨부추가]일괄신고추가서류(파생결합증권-주가연계증권)","rcept_no":"20200117000559","flr_nm":"NH투자증권","rcept_dt":"20200117","rm":""},{"corp_code":"00120182","corp_name":"NH투자증권","stock_code":"005940","corp_cls":"Y","report_nm":"[첨부추가]일괄신고추가서류(파생결합증권-주가연계증권)","rcept_no":"20200117000486","flr_nm":"NH투자증권","rcept_dt":"20200117","rm":""},{"corp_code":"00120182","corp_name":"NH투자증권","stock_code":"005940","corp_cls":"Y","report_nm":"[첨부추가]일괄신고추가서류(파생결합증권-주가연계증권)","rcept_no":"20200117000375","flr_nm":"NH투자증권","rcept_dt":"20200117","rm":""},{"corp_code":"00120182","corp_name":"NH투자증권","stock_code":"005940","corp_cls":"Y","report_nm":"[첨부추가]일괄신고추가서류(파생결합증권-주가연계증권)","rcept_no":"20200117000341","flr_nm":"NH투자증권","rcept_dt":"20200117","rm":""},{"corp_code":"00120182","corp_name":"NH투자증권","stock_code":"005940","corp_cls":"Y","report_nm":"[첨부추


class FinancialStatementItem:
    def __init__(
        self,
        corporation_code: str,
        business_year: int,
        fs_type: str,
        fs_name: str,
        account_id: str,
        account_name: str,
        account_detail: str,
        term: str,
        amount: int,
        order: int,
    ):
        """
        :param fs_type: 재무제표구분 (BS : 재무상태표, IS: 손익계산서, CIS: 포괄손익계산서, CF: 현금흐름표, SCE: 자본변동표)
        """
        self.corporation_code = corporation_code
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
        return f"{self.corporation_code}, {self.business_year}, {self.fs_name}, {self.account_name}: {self.amount}"


class FinancialStatementRequest:
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"

    def fetch(self, corporation_code: str, business_year: int, report_code: str, fs: str):
        """
        :param report_code: 1분기보고서: 11013, 반기보고서 : 11012, 3분기보고서: 11014, 사업보고서: 11011
        :param fs: CFS:연결재무제표, OFS:재무제표
        """
        resp = requests.get(
            self.url,
            params={
                "crtfc_key": dart_access_key,
                "corp_code": corporation_code,
                "bsns_year": business_year,
                "reprt_code": report_code,
                "fs_div": fs,
            },
        )
        data = json.loads(resp.text)

        # FIXME: Replace with a proper error handling logic
        assert data["status"] == "000"

        return [
            FinancialStatementItem(
                corporation_code,
                business_year,
                item_dict["sj_div"],
                item_dict["sj_nm"],
                item_dict["account_id"],
                item_dict["account_nm"],
                item_dict["account_detail"],
                item_dict["thstrm_nm"],
                item_dict["thstrm_amount"],
                int(item_dict["ord"]),
            )
            for item_dict in data["list"]
        ]
