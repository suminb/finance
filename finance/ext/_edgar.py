import csv
from datetime import datetime
from glob import glob
import sys
from typing import List
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
        nodew = XmlNodeWrapper(xml_node)
        ns = EDGAR_XML_NAMESPACE
        self.name = nodew.text("d:name")

        # NOTE: Not sure what these are...
        self.lei = nodew.text("d:lei")
        self.cusip = nodew.text("d:cusip")

        isin_tag = xml_node.find("d:identifiers/d:isin", ns)
        if isin_tag is not None:
            self.isin = isin_tag.attrib["value"]
        else:
            self.isin = None
        # NOTE: Sometimes <identifiers> contains <ticker>

        self.units = float(nodew.text("d:valUSD", ns))
        self.value_usd = float(nodew.text("d:valUSD", ns))
        self.percentage = float(nodew.text("d:pctVal", ns))

        currency = xml_node.find("d:curCd", ns)
        if currency is not None:
            self.currency = currency.text
        else:
            currency = xml_node.find("d:currencyConditional", ns)
            self.currency = currency.attrib["curCd"]

        self.payoff_profile = nodew.text("d:payoffProfile")
        self.asset_category = nodew.text("d:assetCat")
        self.issuer_category = nodew.text("d:issuerCat")
        self.invested_country = nodew.text("d:invCountry")
        self.is_restricted_security = nodew.text("d:isRestrictedSec")

        # NOTE: Not sure what these are...
        self.fair_value_level = nodew.text("d:fairValLevel")
        self.is_cash_collateral = nodew.text("d:securityLending/d:isCashCollateral")
        self.is_non_cash_collateral = nodew.text(
            "d:securityLending/d:isNonCashCollateral"
        )
        self.is_loan_by_fund = nodew.text("d:securityLending/d:isLoanByFund")

    def __repr__(self):
        return f"{self.name}, {self.isin}, {self.value_usd}, {self.percentage}"


class XmlNodeWrapper:
    def __init__(self, xml_node: Element):
        self.xml_node = xml_node

    def text(self, node_name: str, ns=EDGAR_XML_NAMESPACE):
        node = self.xml_node.find(node_name, ns)
        if node is None:
            return None
        else:
            return node.text


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


def export_as_csv(rows: List[EdgarIndexRow], fout):
    writer = csv.writer(fout)
    for row in rows:
        text_report = fetch_report(row.txt_path)
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


if __name__ == "__main__":
    rows = search(lambda row: row.type == "NPORT-P" and "BLACKROCK" in row.title)
    export_as_csv(rows, sys.stdout)
