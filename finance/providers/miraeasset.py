from finance.providers.provider import Provider
from finance.providers.record import DateTime, Float, Integer, String


DATE_FORMAT = '%Y/%m/%d'


class Miraeasset(Provider):

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

            fields = [cols[i] for i in [0, 1, 3, 4, 5, 7, 6, 9, 16]]
            # Insert an empty string for code
            fields.insert(4, '')
            record = Record(*fields)
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
                *[cols[i] for i in [0, 1, 3, 5, 7, 8, 10, 9, 13, 14]])
            yield record

    def is_local_transaction(self, category):
        return category in ['주식매수', '주식매도', '은행이체입금',
                            '은행이체출금', '배당금입금']

    def is_foreign_transaction(self, category):
        return category in ['해외주매수', '해외주매도', '외화인지세',
                            '예이용료', '해외주배당금', '환전매수', '환전매도']


class Record(object):
    """Represents a single transaction record."""

    registered_at = DateTime(date_format='%Y/%m/%d')
    seq = Integer()
    category = String()
    amount = Float()  # FIXME: Use decimal type
    #!: ISIN (International Securities Identification Numbers)
    code = String()
    name = String()
    unit_price = Float()  # FIXME: Use decimal type
    quantity = Integer()
    fees = Float()  # FIXME: Use decimal type
    tax = Float()  # FIXME: Use decimal type

    def __init__(self, registered_at, seq, category, amount, code, name,
            unit_price, quantity, fees, tax):
        self.registered_at = registered_at
        self.seq = seq
        self.category = category
        self.amount = amount
        self.code = code
        self.name = name
        self.unit_price = unit_price
        self.quantity = quantity
        self.fees = fees
        self.tax = tax

    def __repr__(self):
        return 'miraeasset.Record({}, {}, {}, {} ({}), {}, {})'.format(
            self.registered_at.strftime('%Y-%m-%d'), self.category,
            self.amount, self.name, self.code, self.unit_price, self.quantity)
