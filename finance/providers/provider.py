from finance.models import Granularity


class Provider(object):
    pass


class AssetValueProvider(Provider):
    def __init__(self):
        raise NotImplementedError

    def asset_values(self, symbol, start_date, end_date,
                     granularity=Granularity.day):
        """Returns a list of asset value records (list of tuples).

        (datetime, open, high, low, close, volume)
        """
        raise NotImplementedError


class RecordProvider(Provider):
    def __init__(self):
        raise NotImplementedError

    def records(self):
        """Returns list of financial transactions (list of tuples).

        (TODO: Format to be determined)
        """
        raise NotImplementedError
