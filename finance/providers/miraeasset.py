import codecs
from datetime import timedelta

from finance.providers.provider import Provider
from finance.providers.record import DateTime, Decimal, Integer, List, String

DATE_INPUT_FORMAT = '%Y/%m/%d'
DATE_OUTPUT_FORMAT = '%Y-%m-%d'


# NOTE: This doesn't seem like a good idea...
name_code_mappings = {
    '애플': 'AAPL',
    'AMD': 'AMD',
    'Advanced Micro Devic': 'AMD',
    'Advanced Micro Devices  Inc.': 'AMD',
    '아마존닷컴': 'AMZN',
    '아마존 닷컴': 'AMZN',
    'ARK Web x.0 ETF': 'ARKW',
    'Berkshire Hathaway I': 'BRK-B', # FIXME: This is a dangerous assumption (could've been BRK-A)
    '버크셔해서웨이.B': 'BRK-B',
    '보잉': 'BA',
    'Credit Suisse High Y': 'DHY',
    'CREDIT SUISSE HIGH YIELD BOND FU': 'DHY',
    'Empire State Realty Trust  Inc.': 'ESRT',
    'Empire State Realty': 'ESRT',
    'EMPIRE ST RLTY TR INC': 'ESRT',
    'Direxion Daily Gold': 'NUGT',
    '엔비디아': 'NVDA',
    'OXFORD LANE CAPITAL': 'OXLC',
    '옥스포드 래인 캐피탈': 'OXLC',
    '스타벅스': 'SBUX',
    'SPDR S&P 500': 'SPY',
    '테슬라 모터스': 'TSLA',
    'VANGUARD TAX-EXEMPT BOND ETF': 'VTEB',
    'ISHARES 20+Y TREASURY BOND ETF': 'TLT',
    'ISHARES IBOXX $ INVESTMENT GRADE': 'LQD',
    'VANGUARD EMERGING MARKETS GOVERN': 'VWOB',
    'VANGUARD SHORT-TERM INFLATION-PR': 'VTIP',
    '넥슨 일본': '3659.T',
    '삼성전자보통주': '005930.KS',
}


class Miraeasset(Provider):

    DEFAULT_ENCODING = 'euc-kr'

    def read_records(self, filename):
        with codecs.open(filename, 'r', encoding=self.DEFAULT_ENCODING) as fin:
            for record in self.parse_records(fin):
                yield record

    def find_header_column_indices(self, headers):
        mappings = [
            ('created_at', '거래일자'),
            ('seq', '거래번호'),
            ('category', '거래종류'),
            ('amount', '거래금액'),
            ('currency', '통화코드'),
            ('name', '종목명'),
            ('unit_price', '단가'),
            ('quantity', '수량'),
            ('fees', '수수료'),
            ('tax', '제세금합'),
        ]
        return {k: headers.index(v) for k, v in mappings}

    # FIXME: This doesn't have to be a method
    def coalesce(self, value, fallback):
        return value if value else fallback

    def parse_records(self, fin):
        """거래내역조회 (0650)"""
        headers = next(fin).strip().split(',')

        col_count = len(headers)
        assert col_count == 25, 'Invalid column count ({})'.format(col_count)

        column_indices = self.find_header_column_indices(headers)

        for line in fin:
            columns = [x.strip() for x in line.strip().split(',')]
            assert len(columns) == col_count, \
                'Invalid column count ({})'.format(len(columns))

            column_names = [
                'created_at', 'seq', 'category', 'amount', 'currency',
                # 'code',
                'name', 'unit_price', 'quantity', 'fees', 'tax',
            ]
            kwargs = {k: columns[column_indices[k]] for k in column_names}

            # FIXME: Fix all this shit
            kwargs['amount'] = self.coalesce(kwargs['amount'], 0)
            kwargs['unit_price'] = self.coalesce(kwargs['unit_price'], 0)
            kwargs['quantity'] = self.coalesce(kwargs['quantity'], 0)
            kwargs['fees'] = self.coalesce(kwargs['fees'], 0)
            kwargs['tax'] = self.coalesce(kwargs['tax'], 0)
            try:
                kwargs['code'] = name_code_mappings[kwargs['name']]
            except KeyError:
                kwargs['code'] = '(unknown)'

            kwargs['raw_columns'] = columns

            yield Record(**kwargs)


class Record(object):
    """Represents a single transaction record."""

    attributes = ['created_at', 'seq', 'category', 'amount', 'currency',
                  'code', 'name', 'unit_price', 'quantity', 'fees', 'tax',
                  'raw_columns']

    created_at = DateTime(date_format=DATE_INPUT_FORMAT)
    seq = Integer()
    category = String()
    amount = Decimal()
    currency = String()
    #: ISIN (International Securities Identification Numbers)
    code = String()
    name = String()
    unit_price = Decimal()
    quantity = Integer()
    fees = Decimal()
    tax = Decimal()
    raw_columns = List()

    def __init__(self, created_at, seq, category, amount, currency, code,
                 name, unit_price, quantity, fees, tax, raw_columns):
        self.created_at = created_at
        self.seq = seq
        self.category = category
        self.amount = amount
        self.currency = currency
        self.code = code
        self.name = name
        self.unit_price = unit_price
        self.quantity = quantity
        self.fees = fees
        self.tax = tax
        self.raw_columns = raw_columns

    def __repr__(self):
        return 'miraeasset.Record({}, {}, {}, {} ({}), {}, {})'.format(
            self.created_at.strftime(DATE_OUTPUT_FORMAT), self.category,
            self.amount, self.name, self.code, self.unit_price, self.quantity)

    def __iter__(self):
        """Allows an Record object to become a dictionary as:

            dict(record)
        """
        for attr in self.attributes:
            yield attr, getattr(self, attr)

    def values(self):
        """Exports values only (in string)."""
        for k, v in self:
            if k == 'created_at':
                yield v.strftime(DATE_OUTPUT_FORMAT)
            else:
                yield str(v)

    @property
    def synthesized_created_at(self):
        return synthesize_datetime(self.created_at, self.seq)


def synthesize_datetime(datetime, seq):
    """The original CSV file does not include time information (it only
    includes date) and there is a high probability of having multiple records
    on a single day.  However, we have a unique constraint on (account_id,
    asset_id, created_at, quantity) fields on the Record model. In order to
    circumvent potential clashes, we are adding up some seconds (with the
    sequence value) on the original timestamp.
    """
    return datetime + timedelta(seconds=seq)
