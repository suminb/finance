from datetime import timedelta

from bidict import bidict

from finance.providers.provider import Provider
from finance.providers.record import DateTime, Decimal, Integer, List, String

DATE_INPUT_FORMAT = '%Y/%m/%d'
DATE_OUTPUT_FORMAT = '%Y-%m-%d'


# NOTE: This doesn't seem like a good idea...
name_code_mappings = {
    '애플': 'AAPL',
    'AMD': 'AMD',
    'Advanced Micro Devices  Inc.': 'AMD',
    '아마존닷컴': 'AMZN',
    '보잉': 'BA',
    'Empire State Realty Trust  Inc.': 'ESRT',
    'EMPIRE ST RLTY TR INC': 'ESRT',
    'SPDR S&P 500': 'SPY',
    '엔비디아': 'NVDA',
    'VANGUARD TAX-EXEMPT BOND ETF': 'VTEB',
    'ISHARES 20+Y TREASURY BOND ETF': 'TLT',
    'ISHARES IBOXX $ INVESTMENT GRADE': 'LQD',
    'VANGUARD EMERGING MARKETS GOVERN': 'VWOB',
    'VANGUARD SHORT-TERM INFLATION-PR': 'VTIP',
    '넥슨 일본': '3659.T',
}


class Miraeasset(Provider):

    # TODO: Ideally, we would like to unify the following two functions
    # (local/foreign transactions)

    def find_header_column_indices(self, headers):
        return {
            'created_at': headers.index('거래일자'),
            'seq': headers.index('거래번호'),
            'category': headers.index('거래종류'),
            'amount': headers.index('거래금액'),
            'currency': headers.index('통화코드'),
            #'code': headers.index(''),
            'name': headers.index('종목명'),
            'unit_price': headers.index('단가'),
            'quantity': headers.index('수량'),
            'fees': headers.index('수수료'),
            'tax': headers.index('제세금합'),
        }

    # FIXME: This doesn't have to be a method
    def coalesce(self, value, fallback):
        return value if value else fallback

    def parse_transactions(self, fin):
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

    def parse_local_transactions(self, fin):
        """Parses local transactions (거래내역조회, 0650)."""
        headers = next(fin)
        col_count = len(headers.split(','))
        assert col_count == 22, 'Invalid column count'

        for line in fin:
            cols = [x.strip() for x in line.strip().split(',')]
            assert len(cols) == col_count, \
                'Invalid column count ({})'.format(len(cols))

            category = cols[3]
            if not self.is_local_transaction(category):
                continue

            record = Record(
                cols[0], cols[1], cols[3], cols[4], 'KRW', '', cols[5],
                cols[7], cols[6], cols[9], cols[16], cols)
            yield record

    def parse_foreign_transactions(self, fin):
        """Parses foreign transactions (해외거래내역, 9465)."""
        headers = next(fin)
        col_count = len(headers.split(','))
        assert col_count == 22, 'Invalid column count ({})'.format(col_count)

        for line in fin:
            cols = [x.strip() for x in line.strip().split(',')]
            assert len(cols) == col_count, \
                'Invalid column count ({})'.format(len(cols))

            category = cols[3]
            if not self.is_foreign_transaction(category):
                continue

            record = Record(
                *[cols[i] for i in [0, 1, 3, 5, 4, 7, 8, 10, 9, 13, 14]], cols)
            yield record

    def is_local_transaction(self, category):
        return category in ['주식매수', '주식매도', '은행이체입금', '예이용료',
                            '은행이체출금', '배당금입금']

    def is_foreign_transaction(self, category):
        return category in ['해외주매수', '해외주매도', '외화인지세',
                            '해외주배당금', '환전매수', '환전매도']


class Record(object):
    """Represents a single transaction record."""

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
        attrs = ['created_at', 'seq', 'category', 'amount', 'currency',
                 'code', 'name', 'unit_price', 'quantity', 'fees', 'tax',
                 'raw_columns']
        for attr in attrs:
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
