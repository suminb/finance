"""Memory-based models. This is a temporary and may or may not be promoted as
permemant models.
"""
from finance.models import Granularity


class Account:
    # Memory-based model (as opposed to DB-based)
    # TODO: Move this elsewhere

    def __init__(self, records):
        self.records = list(records)

    def assets(self):
        """Returns all assets under this account."""
        return set([r.code for r in self.records])

    def balance(self, evaluated_at=None, include_zero_balance=False):
        balance = {}
        for r in self.records:
            if evaluated_at and r.created_at > evaluated_at:
                # Assuming the records may not be in order
                continue
            balance.setdefault(r.code, 0)
            if r.category in ['해외주식매수입고', '해외주식매수결제']:
                balance[r.code] += r.quantity
            elif r.category in ['해외주식매도출고', '해외주식매도결제']:
                balance[r.code] -= r.quantity
            elif r.category == '해외주식분할입고':
                balance[r.code] += r.quantity
            elif r.category == '해외주식분할출고':
                balance[r.code] -= r.quantity
        if not include_zero_balance:
            keys = [k for k in balance if balance[k] == 0]
            for k in keys:
                del balance[k]
        return balance

    def net_worth(self, evaluated_at=None, granularity=Granularity.day,
                  approximation=False, base_asset=None):
        """Calculates the net worth of the account on a particular datetime.
        If approximation=True and the asset value record is unavailable for the
        given date (evaluated_at), try to pull the most recent AssetValue.
        """
        raise NotImplementedError
