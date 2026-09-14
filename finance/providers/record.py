import decimal

from finance.utils import parse_date


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
    def __init__(self, date_format="%Y-%m-%d"):
        self.date_format = date_format
        super(self.__class__, self).__init__()

    def __set__(self, instance, value):
        self._values[instance] = parse_date(value, self.date_format)


def _clean_number(value):
    """Normalizes a numeric string as it appears in brokerage exports.

    Thousands separators and surrounding whitespace are stripped, and an empty
    value is treated as zero -- exports leave numeric cells blank rather than
    writing a zero.
    """
    if isinstance(value, str):
        value = value.strip().replace(",", "")
        if not value:
            return "0"
    return value


class Decimal(AbstractField):
    def __set__(self, instance, value):
        self._values[instance] = decimal.Decimal(_clean_number(value))


class Float(AbstractField):
    def __set__(self, instance, value):
        self._values[instance] = float(value)


class Integer(AbstractField):
    def __set__(self, instance, value):
        self._values[instance] = int(decimal.Decimal(_clean_number(value)))


class String(AbstractField):
    def __set__(self, instance, value):
        self._values[instance] = value.strip()


class List(AbstractField):
    def __set__(self, instance, value):
        assert isinstance(value, list)
        self._values[instance] = value
