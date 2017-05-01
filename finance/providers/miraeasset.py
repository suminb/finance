from finance.providers.provider import Provider
from finance.utils import parse_date


DATE_FORMAT = '%Y/%m/%d'


class Miraeasset(Provider):

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
