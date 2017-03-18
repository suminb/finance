import json
try:
    # Python 3
    from urllib.parse import quote_plus
except:
    # Python 2
    from urllib import quote_plus

import requests

from finance.utils import parse_date
from finance.providers.provider import Provider

DART_HOST = 'm.dart.fss.or.kr'

"""
curl 'http://m.dart.fss.or.kr/md3002/search.st?currentPage=2&maxResultCnt=15&corporationType=&textCrpNm=%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90&textCrpCik=00126380&startDate=20160912&endDate=20170312&publicType=&publicOrgType=&reportName=&textPresenterNm=&finalReport=&lastRcpNo=20170310800637&totalPage=&textTerm=&_=1489313031578'
"""


class Dart(Provider):

    def fetch_data(self, entity_name):
        """
        :param entity_name: Financial entity name (e.g., 삼성전자)
        """
        url = 'http://{}/md3002/search.st'.format(DART_HOST)
        params = {
            'maxResultCnt': 15,
            'corporationType': None,
            'textCrpNm': quote_plus(entity_name),
            'textCrpCik': '00126380',  # NOTE: What is this?
            'startDate': '20160912',
            'endDate': '20170312',
            'publicType': None,
            'publicOrgType': None,
            'reportName': None,
            'textPresenterNm': None,
            # and more...
        }
        resp = requests.get(url, params=params)
        data = json.loads(resp.text)
        return self.process_data(data)

    def process_data(self, json_data):
        # page_count = json_data['totalPage']
        # record_count = json_data['totCount']
        records = json_data['rlist']

        for record in records:
            yield Record(**record)


class Record(object):

    def __init__(self, **kwargs):
        # TODO: Refactor the following part - use descriptors
        self.id = kwargs['rcp_no'].strip()
        self.registered_at = parse_date(kwargs['rcp_dm'], '%Y.%m.%d')
        self.title = kwargs['rptNm'].strip()
        self.entity = kwargs['ifm_nm'].strip()
        self.reporter = kwargs['ifm_nm2'].strip()

    def __repr__(self):
        return '{} ({}, {}, {})'.format(
            self.title, self.id,
            self.registered_at.strftime('%Y-%m-%d'), self.entity)
