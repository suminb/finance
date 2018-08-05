from datetime import datetime

from logbook import Logger
import requests
import xmltodict

from finance.providers.provider import AssetValueProvider


DATE_FORMAT = '%Y%m%d'

log = Logger(__name__)


class Kofia(AssetValueProvider):
    """Korea Financial Investment Association (금융투자협회)"""

    def __init__(self):
        pass

    @property
    def request_url(self):
        return 'http://dis.kofia.or.kr/proframeWeb/XMLSERVICES/'

    @property
    def request_headers(self):
        return {
            'Origin': 'http://dis.kofia.or.kr',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.8,ko;q=0.6',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/48.0.2564.109 Safari/537.36',
            'Content-Type': 'text/xml',
            'Accept': 'text/xml',
            'Referer':
                'http://dis.kofia.or.kr/websquare/popup.html?w2xPath='
                '/wq/com/popup/DISComFundSmryInfo.xml&companyCd=20090602&'
                'standardCd=KR5223941018&standardDt=20160219&grntGb=S&'
                'search=&check=1&isMain=undefined&companyGb=A&uFundNm='
                '/v8ASwBCwqTQwLv4rW0AUwAmAFAANQAwADDHeLNxwqTJna2Mx5DSLMeQwu'
                'DQwQBbyPzC3QAt0wzA%0A3dYVAF0AQwAtAEU%3D&popupID=undefined&'
                'w2xHome=/wq/fundann/&w2xDocumentRoot=',
        }

    def get_request_body(self, code, from_date, to_date):
        """
        :type from_date: datetime.datetime
        :type to_date: datetime.datetime
        """
        return """<?xml version="1.0" encoding="utf-8"?>
            <message>
                <proframeHeader>
                    <pfmAppName>FS-COM</pfmAppName>
                    <pfmSvcName>COMFundPriceModSO</pfmSvcName>
                    <pfmFnName>priceModSrch</pfmFnName>
                </proframeHeader>
                <systemHeader></systemHeader>
                <COMFundUnityInfoInputDTO>
                    <standardCd>{code}</standardCd>
                    <companyCd>A01031</companyCd>
                    <vSrchTrmFrom>{from_date}</vSrchTrmFrom>
                    <vSrchTrmTo>{to_date}</vSrchTrmTo>
                    <vSrchStd>1</vSrchStd>
                </COMFundUnityInfoInputDTO>
            </message>
        """.format(code=code,
                   from_date=from_date.strftime(DATE_FORMAT),
                   to_date=to_date.strftime(DATE_FORMAT))

    def fetch_data(self, code, from_date, to_date):
        """Fetch data from the provider.

        :param code: Fund code (e.g., KR5223941018)
        :param from_date:
        :param to_date:

        :type from_date: datetime.datetime
        :type to_date: datetime.datetime
        """
        request_body = self.get_request_body(code, from_date, to_date)
        resp = requests.post(self.request_url, headers=self.request_headers,
                             data=request_body)

        # TODO: Handle cases where the XML could not be parsed
        parsed_data = xmltodict.parse(resp.text)

        message = parsed_data['root']['message']
        price_records = message['COMFundPriceModListDTO']['priceModList']
        for pr in price_records:
            date_str = pr['standardDt']
            date = datetime.strptime(date_str, '%Y%m%d')
            unit_price = float(pr['standardCot'])
            original_quantity = float(pr['uOriginalAmt'])

            yield date, unit_price, original_quantity * 1000000
