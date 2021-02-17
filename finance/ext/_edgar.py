import csv
from datetime import datetime
from glob import glob
import sys
from xml.etree.ElementTree import Element, ElementTree, fromstring

import edgar
import requests


EDGAR_URL_PREFIX = "https://www.sec.gov/Archives/"
EDGAR_XML_NAMESPACE = {"d": "http://www.sec.gov/edgar/nport"}


class EdgarIndexRow:
    def __init__(self, raw_columns):
        (
            self.cik,
            self.title,
            self.type,
            date,
            self.txt_path,
            self.html_path,
        ) = raw_columns
        self.date = datetime.strptime(date, "%Y-%m-%d")

    def __repr__(self):
        return f"{self.cik}, {self.title}, {self.type}, {self.date}, {self.txt_path}, {self.html_path}"


class Investment:
    def __init__(self, xml_node: Element):
        ns = EDGAR_XML_NAMESPACE
        self.name = xml_node.find("d:name", ns).text

        # NOTE: Not sure what these are...
        self.lei = xml_node.find("d:lei").text
        self.cusip = xml_node.find("d:cusip").text

        isin_tag = xml_node.find("d:identifiers/d:isin", ns)
        if isin_tag is not None:
            self.isin = isin_tag.attrib["value"]
        else:
            self.isin = None
        # NOTE: Sometimes <identifiers> contains <ticker>

        self.units = float(xml_node.find("d:valUSD", ns).text)
        self.value_usd = float(xml_node.find("d:valUSD", ns).text)
        self.percentage = float(xml_node.find("d:pctVal", ns).text)

        currency = xml_node.find("d:curCd", ns)
        if currency is not None:
            self.currency = currency.text
        else:
            currency = xml_node.find("d:currencyConditional", ns)
            self.currency = currency.attrib["curCd"]

        self.payoff_profile = xml_node.find("d:payoffProfile").text
        self.asset_category = xml_node.find("d:assetCat").text
        self.issuer_category = xml_node.find("d:issuerCat").text
        self.invested_country = xml_node.find("d:invCountry").text
        self.is_restricted_security = xml_node.find("d:isRestrictedSec").text

        # NOTE: Not sure what these are...
        self.fair_value_level = xml_node.find("d:fairValLevel").text
        self.is_cash_collateral = xml_node.find("d:securityLending/d:isCashCollateral").text
        self.is_non_cash_collateral = xml_node.find("d:securityLending/d:isNonCashCollateral").text
        self.is_loan_by_fund = xml_node.find("d:securityLending/d:isLoanByFund").text

    def __repr__(self):
        return f"{self.name}, {self.isin}, {self.value_usd}, {self.percentage}"


def fetch_indexes():
    edgar.download_index("/tmp/edgar", 2020, skip_all_present_except_last=False)


def fetch_report(txt_path: str):
    url = EDGAR_URL_PREFIX + txt_path
    resp = requests.get(url)

    return resp.text


def extract_investments(text_report: str):
    """
    :param text_report: Report in text format
    """
    xml = extract_xml(text_report)
    tree = ElementTree(fromstring(xml))

    ns = EDGAR_XML_NAMESPACE
    for element in tree.findall(".//d:invstOrSec", ns):
        yield Investment(element)


def extract_xml(text: str):
    start = text.index("<XML>")
    end = text.index("</XML>")
    return text[start + 5 : end].strip()


def search(predicate: callable):
    for filename in glob("/tmp/edgar/*.tsv"):
        with open(filename) as fin:
            rows = csv.reader(fin, delimiter="|")
            for row in rows:
                row = EdgarIndexRow(row)
                if predicate(row):
                    yield row


if __name__ == "__main__":
    writer = csv.writer(sys.stdout)
    for row in search(lambda row: row.type == "NPORT-P" and "BLACKROCK" in row.title):
        # print(row)
        text_report = fetch_report(row.txt_path)
        # text_report = fetch_report("edgar/data/1005942/0000869392-20-002228.txt")
        for investment in extract_investments(text_report):
            if investment.currency == "USD":
                writer.writerow(
                    [
                        investment.name,
                        investment.isin,
                        investment.value_usd,
                        investment.percentage,
                    ]
                )
