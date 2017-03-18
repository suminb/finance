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


class AbstractField(object):

    def __init__(self):
        self._values = {}

    def __get__(self, instance, instance_type, default=None):
        if instance is None:
            return self
        else:
            return self._values.get(instance, default)

    def __set__(self, instance, value):
        self._values[instance] = value


class DateTime(AbstractField):

    def __init__(self, date_format='%Y-%m-%d'):
        self.date_format = date_format
        super(self.__class__, self).__init__()

    def __set__(self, instance, value):
        self._values[instance] = parse_date(value, self.date_format)


class Integer(AbstractField):

    def __set__(self, instance, value):
        self._values[instance] = int(value)


class String(AbstractField):

    def __set__(self, instance, value):
        self._values[instance] = value.strip()


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

    id = Integer()
    registered_at = DateTime(date_format='%Y.%m.%d')
    title = String()
    entity = String()
    reporter = String()

    def __init__(self, **kwargs):
        self.id = kwargs['rcp_no']
        self.registered_at = kwargs['rcp_dm']
        self.title = kwargs['rptNm']
        self.entity = kwargs['ifm_nm']
        self.reporter = kwargs['ifm_nm2']

    def __repr__(self):
        return '{} ({}, {}, {})'.format(
            self.title, self.id,
            self.registered_at.strftime('%Y-%m-%d'), self.entity)

    def __iter__(self):
        attrs = ['id', 'registered_at', 'title', 'entity', 'reporter']
        for attr in attrs:
            yield attr, getattr(self, attr)
