from datetime import datetime, timedelta
import json
from urllib.parse import quote_plus

import requests

from finance.providers.provider import Provider
from finance.providers.record import DateTime, Integer, String

DART_HOST = 'm.dart.fss.or.kr'

"""
curl 'http://m.dart.fss.or.kr/md3002/search.st?currentPage=2&maxResultCnt=15
&corporationType=&textCrpNm=%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90
&textCrpCik=00126380&startDate=20160912&endDate=20170312&publicType=
&publicOrgType=&reportName=&textPresenterNm=&finalReport=
&lastRcpNo=20170310800637&totalPage=&textTerm=&_=1489313031578'
"""


class Dart(Provider):

    def fetch_reports(self, entity_name, entity_code, start_date=None,
                      end_date=None):
        """Fetches all DART reports for a single financial entity.

        :param entity_name: Financial entity name (e.g., 삼성전자)
        :param entity_code: Financial entity code (e.g., 00254045)
        """
        page = 1
        while True:
            reports, page_count, record_count = \
                self.fetch_reports_by_page(
                    entity_name, entity_code, page, start_date=start_date,
                    end_date=end_date)

            for report in reports:
                yield report

            page += 1
            if page > page_count:
                break

    def fetch_reports_by_page(self, entity_name, entity_code, page=1,
                              reports_per_page=15, start_date=None,
                              end_date=None):
        """Fetches DART reports for a single page."""
        if end_date is None:
            end_date = datetime.now()

        if start_date is None:
            start_date = end_date - timedelta(days=365)

        date_format = '%Y%m%d'

        url = 'http://{}/md3002/search.st'.format(DART_HOST)
        params = {
            'currentPage': page,
            'maxResultCnt': reports_per_page,
            'corporationType': None,
            'textCrpNm': quote_plus(entity_name),
            'textCrpCik': entity_code,
            'startDate': start_date.strftime(date_format),
            'endDate': end_date.strftime(date_format),
            'publicType': None,
            'publicOrgType': None,
            'reportName': None,
            'textPresenterNm': None,
            # and more...
        }
        resp = requests.get(url, params=params)
        report_listings = json.loads(resp.text)

        page_count = report_listings['totalPage']
        record_count = report_listings['totCount']

        if not report_listings['rlist'] or record_count == 0:
            # NOTE: Should we raise an exception or show a warning?
            raise ValueError('No report was found for {}'.format(entity_name))

        return self.process_data(report_listings), page_count, record_count

    def fetch_report(self, id):
        """Fetches a full report."""

        url = 'http://{}/viewer/main.st'.format(DART_HOST)
        params = {'rcpNo': id}
        resp = requests.get(url, params=params)
        parsed = json.loads(resp.text)
        return parsed

    def process_data(self, json_data):
        for listing in json_data['rlist']:
            report = self.fetch_report(listing['rcp_no'])
            report['self_'] = report.pop('self')
            merged = {**listing, **report}  # noqa, new syntax in Python 3.5
            yield Report(**merged)


class Report(object):

    id = Integer()
    registered_at = DateTime(date_format='%Y.%m.%d')
    title = String()
    entity_id = Integer()  # 전자공시 CRP code
    entity = String()
    reporter = String()
    content = String()

    def __init__(self, **kwargs):
        self.id = kwargs['rcp_no']
        self.registered_at = kwargs['rcp_dm']
        self.title = kwargs['rptNm']
        self.entity_id = kwargs['dsm_crp_cik']
        self.entity = kwargs['ifm_nm']
        self.reporter = kwargs['ifm_nm2']
        self.content = kwargs['reportBody']

    def __repr__(self):
        return '{} ({}, {}, {})'.format(
            self.title, self.id,
            self.registered_at.strftime('%Y-%m-%d'), self.entity)

    def __iter__(self):
        attrs = ['id', 'registered_at', 'title', 'entity_id', 'entity',
                 'reporter', 'content']
        for attr in attrs:
            yield attr, getattr(self, attr)
