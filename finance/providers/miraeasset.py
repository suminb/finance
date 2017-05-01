from finance.providers.provider import Provider
from finance.providers.record import DateTime, Float, Integer, String
from finance.utils import parse_date


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

            date = parse_date(cols[0], DATE_FORMAT)
            seq = int(cols[1])
            category = cols[3]

            if not self.is_local_transaction(category):
                continue

    def parse_foreign_transactions(self, fin):
        """Parses foreign transactions (해외거래내역, 9465)."""
        headers = next(fin)
        col_count = len(headers.split(','))
        assert col_count == 22, 'Invalid column count ({})'.format(col_count)

        for line in fin:
            cols = [x.strip() for x in line.strip().split(',')]
            assert len(cols) == col_count, \
                'Invalid column count ({})'.format(len(cols))

            date = parse_date(cols[0], DATE_FORMAT)
            seq = int(cols[1])
            category = cols[3]

            if not self.is_foreign_transaction(category):
                continue

            record = Record(*[cols[i] for i in [0, 1, 3, 5, 7, 8, 10, 9, 13, 14]])
            yield record

    def is_local_transaction(self, category):
        return category in ['주식매수', '주식매도', '은행이체입금',
                            '은행이체출금', '배당금입금']

    def is_foreign_transaction(self, category):
        return category in ['해외주매수', '해외주매도', '외화인지세',
                            '예이용료', '해외주배당금', '환전매수', '환전매도']

    def parse_data(self, fin):
        """Parses raw data.

        :param fin: A file input stream
        """
        headers = next(fin)
        col_count = len(headers.split())

        for line in fin:
            cols = [x.strip() for x in line.strip().split(',')]
            date = parse_date(cols[0], DATE_FORMAT)
            seq = int(cols[1])
            category, currency = cols[3:5]
            fcur_amount, lcur_amount = \
                self.parse_transaction_amount(category, cols[5], cols[6])
            code = cols[7]
            name = cols[8]
            quantity = int(cols[9])
            unit_price = self.parse_unit_price(category, currency, cols[10])
            fees = self.parse_fees(category, lcur_amount, unit_price, quantity,
                                   cols[13])
            tax = int(cols[14])
            yield date, seq, category, fcur_amount, lcur_amount, code, name, \
                unit_price, quantity, fees, tax

    def parse_unit_price(self, category, currency, value):
        if category not in ['주식매수', '주식매도', '해외주매수', '해외주매도']:
            return None

        if currency == 'USD':
            return float(value)
        elif currency == 'KRW':
            return int(value[:value.index('.')])
        else:
            raise ValueError('Invalid currency: {}'.format(currency))

    def parse_transaction_amount(self, category, fcur_amount, lcur_amount):
        """
        :param category: 거래구분
        :param fcur_amount: Amount in foreign currency
        :param lcur_amount: Amount in local currency (KRW)
        """
        if category in ['은행이체입금', '배당금입금', '주식매수', '주식매도']:
            return 0.0, int(lcur_amount)
        elif category in ['환전매수', '환전매도', '해외주매수', '해외주매도']:
            return float(fcur_amount), 0
        else:
            return None, None

    def parse_fees(self, category, lcur_amount, unit_price, quantity,
                   fcur_fees):
        if category in ['주식매수', '주식매도']:
            return lcur_amount - (unit_price * quantity)
        elif category in ['해외주매수', '해외주매도']:
            return float(fcur_fees)
        else:
            return 0


class Record(object):
        # yield date, seq, category, fcur_amount, lcur_amount, code, name, \
        #         unit_price, quantity, fees, tax
    registered_at = DateTime(date_format='%Y/%m/%d')
    seq = Integer()
    category = String()
    amount = Float()  # FIXME: Use decimal type
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
        return 'miraeasset.Record({}, {}, {}, {}, {}, {})'.format(
            self.registered_at.strftime('%Y-%m-%d'), self.category,
            self.amount, self.name, self.unit_price, self.quantity)
