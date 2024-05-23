from datetime import datetime

import yaml

from finance.utils import date_to_datetime

from typing import List


class Portfolio:
    class Transaction:
        def __init__(self, date: datetime, ticker: str, quantity: float):
            self.date = date
            self.ticker = ticker
            self.quantity = quantity

        # NOTE: I'd like to mark the return type as List[Transaction], but it
        # complains that Transaction is not defined...
        @classmethod
        def load_transactions(cls, yaml_data: List[dict]):
            return [cls(d["date"], d["ticker"], d["quantity"]) for d in yaml_data]

    # TODO: Get rid of dependencies on DataFrame
    def __init__(
        self,
        current_prices: dict,
        target_weights: dict,
        transactions: List[Transaction],
    ):
        self.inventory: dict[str, float] = {}  # ticker: quantity
        self.current_prices = current_prices  # ticker: price
        self.target_weights = self.normalize_weights(target_weights)  # ticker: weight
        self.transactions = transactions

    @property
    def asset_values(self):
        return {t: self.current_prices[t] * q for t, q in self.inventory.items()}

    @property
    def net_asset_value(self):
        return sum(self.asset_values.values())

    @property
    def current_weights(self):
        """Calculate the weights of the current holdings based on the current
        price."""
        nav = self.net_asset_value
        return {t: v / nav for t, v in self.asset_values.items()}

    def evaluate_inventory(self, evaluated_at=datetime.utcnow()) -> dict:
        self.inventory = {}
        for record in self.transactions:
            if date_to_datetime(record.date) <= evaluated_at:
                self.apply_transaction(record)
        return self.inventory

    def apply_transaction(self, record: Transaction):
        """Reflects the given transaction record to the inventory."""
        self.inventory.setdefault(record.ticker, 0)
        self.inventory[record.ticker] += record.quantity

    @classmethod
    def load_from_file(cls, path: str, current_prices: dict):
        """Loads `inventory` and `target_weights` from a YAML file.

        :param current_prices: This must be injected from outside the class.
        """
        with open(path) as fin:
            content = yaml.safe_load(fin)
            portfolio = content["portfolio"]
            transactions = cls.Transaction.load_transactions(content["transactions"])
            return Portfolio(
                current_prices,
                portfolio["target_weights"],
                transactions,
            )

    def normalize_weights(self, weights: dict):
        net_weight = sum(weights.values())
        return {t: v / net_weight for t, v in weights.items()}

    def calc_diff(self):
        """Calculate the difference between the target weights and the current
        ones."""
        cw = self.current_weights
        tw = self.target_weights
        all_keys = set(list(cw.keys()) + list(tw.keys()))

        def diff(t, cw, tw):
            cw.setdefault(t, 0)
            tw.setdefault(t, 0)
            return cw[t] - tw[t]

        return {t: diff(t, cw, tw) for t in all_keys}

    # TODO: Incorporate tax and fees
    def make_rebalancing_plan(self):
        """
        Negative diff means we're short of that asset, so we need to buy more;
        whereas positive diff means we need to sell some.
        Positive values in rebalance plans means the quantity of the asset to
        be purchased.
        """
        nav = self.net_asset_value
        diff = self.calc_diff()

        def plan(t, diff):
            return round((nav * -diff[t]) / self.current_prices[t])

        return {t: plan(t, diff) for t in diff if t != "_USD"}

    # TODO: Tax on dividends?
    # TODO: Transaction fees?
    def apply_plan(
        self, plan: dict, start_dt: datetime, end_dt: datetime, dividend_records: dict
    ):
        def apply(t, q):
            self.inventory.setdefault(t, 0)
            while self.inventory["_USD"] - self.current_prices[t] * q < 0:
                if q > 0:
                    q -= 1
                else:
                    q += 1
            self.inventory["_USD"] -= self.current_prices[t] * q
            if self.inventory["_USD"] < 0:
                raise ValueError(f"USD balance cannot be negative: {t}, {q}")
            return self.inventory[t] + q

        # 'close' is actually 'adj close', which already includes
        # dividends/stock split/capital gains
        # self.inventory["_USD"] += self.calc_dividends_sum(start_dt, end_dt, dividend_records) * 0.85
        self.inventory = {t: apply(t, q) for t, q in plan.items()} | {
            "_USD": self.inventory["_USD"]
        }
        return self.inventory

    def calc_dividends_sum(
        self, start_dt: datetime, end_dt: datetime, dividend_records: dict
    ) -> float:
        div_sum = 0.0
        for t, q in self.inventory.items():
            if t in dividend_records:
                for div_dt, div_amount in dividend_records[t]:
                    if start_dt <= div_dt < end_dt:
                        if q < 0:
                            raise ValueError(f"Quantity cannot be negative: {t}, {q}")
                        div_sum += div_amount * q
        return div_sum
