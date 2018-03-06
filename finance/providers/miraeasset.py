from finance.providers.provider import Provider
from finance.providers.record import DateTime, Float, Integer, String


DATE_INPUT_FORMAT = '%Y/%m/%d'
DATE_OUTPUT_FORMAT = '%Y-%m-%d'


class Miraeasset(Provider):

    # TODO: Ideally, we would like to unify the following two functions
    # (local/foreign transactions)

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
                cols[7], cols[6], cols[9], cols[16])
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
                *[cols[i] for i in [0, 1, 3, 5, 4, 7, 8, 10, 9, 13, 14]])
            yield record

    def is_local_transaction(self, category):
        return category in ['주식매수', '주식매도', '은행이체입금',
                            '은행이체출금', '배당금입금']

    def is_foreign_transaction(self, category):
        return category in ['해외주매수', '해외주매도', '외화인지세',
                            '예이용료', '해외주배당금', '환전매수', '환전매도']


class Record(object):
    """Represents a single transaction record."""

    created_at = DateTime(date_format=DATE_INPUT_FORMAT)
    seq = Integer()
    category = String()
    amount = Float()  # FIXME: Use decimal type
    currency = String()
    #: ISIN (International Securities Identification Numbers)
    code = String()
    name = String()
    unit_price = Float()  # FIXME: Use decimal type
    quantity = Integer()
    fees = Float()  # FIXME: Use decimal type
    tax = Float()  # FIXME: Use decimal type

    def __init__(self, created_at, seq, category, amount, currency, code,
                 name, unit_price, quantity, fees, tax):
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

    def __repr__(self):
        return 'miraeasset.Record({}, {}, {}, {} ({}), {}, {})'.format(
            self.created_at.strftime(DATE_OUTPUT_FORMAT), self.category,
            self.amount, self.name, self.code, self.unit_price, self.quantity)

    def __iter__(self):
        """Allows an Record object to become a dictionary as:

            dict(record)
        """
        attrs = ['created_at', 'seq', 'category', 'amount', 'currency',
                 'code', 'name', 'unit_price', 'quantity', 'fees', 'tax']
        for attr in attrs:
            yield attr, getattr(self, attr)

    def values(self):
        """Exports values only (in string)."""
        for k, v in self:
            if k == 'created_at':
                yield v.strftime(DATE_OUTPUT_FORMAT)
            else:
                yield str(v)
