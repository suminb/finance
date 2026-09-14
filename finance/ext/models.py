from datetime import datetime, timedelta, timezone

import pytz
import pandas as pd
import yaml

from finance.utils import date_to_datetime, make_dates
from finance.ext.exceptions import MissingPriceException

from typing import List

# Cash is held in the inventory under an underscore-prefixed pseudo-ticker
# (e.g. "_USD", "_KRW"). This is the same convention `nav/model.py` defines
# independently as CASH_PREFIX -- that duplication is deliberate, since
# `finance.ext.models` depends on pandas and `nav.model` is meant to stay
# dependency-light.
CASH_PREFIX = "_"

# Quantities accumulate through repeated float addition (see
# `apply_transaction`), so a fully-closed position can land on something
# like 1e-13 instead of exact zero. Treat anything within this tolerance of
# zero as closed, so valuation doesn't demand a price for it.
QUANTITY_EPSILON = 1e-9


def is_cash(ticker: str) -> bool:
    """Cash is held in the inventory under an underscore-prefixed ticker."""
    return ticker.startswith(CASH_PREFIX)


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
            return [
                cls(
                    date_to_datetime(d["date"]).replace(tzinfo=pytz.utc),
                    d["ticker"],
                    d["quantity"],
                )
                for d in yaml_data
            ]

    # TODO: Get rid of dependencies on DataFrame
    def __init__(
        self,
        current_prices: dict,
        target_weights: dict,
        transactions: List[Transaction],
        base_currency: str = "USD",
    ):
        self.inventory: dict[str, float] = {}  # ticker: quantity
        self.current_prices = current_prices  # ticker: price
        self.target_weights = self.normalize_weights(target_weights)  # ticker: weight
        self.transactions = transactions
        self.base_currency = base_currency
        self.cash_ticker = CASH_PREFIX + base_currency

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

    @staticmethod
    def _accumulate(inventory: dict, record: Transaction) -> None:
        """Adds one transaction's quantity into `inventory`, in place.

        The single copy of this arithmetic. `_replay_transactions` used to
        inline it while `apply_transaction` kept its own copy, leaving two
        implementations of the same rule free to drift apart.
        """
        inventory.setdefault(record.ticker, 0)
        inventory[record.ticker] += record.quantity

    def _replay_transactions(self, evaluated_at: datetime) -> dict:
        """Replays transactions up to and including `evaluated_at` and
        returns the resulting inventory, without touching `self.inventory`.

        This is the pure query half of `eval_inventory`; use it (rather than
        `eval_inventory`) wherever a caller needs a historical inventory
        without also resetting the instance's current inventory as a side
        effect -- e.g. `eval_nav`, which is routinely asked to value past
        dates on a live `Portfolio` instance.
        """
        inventory: dict = {}
        for record in self.transactions:
            if record.date <= evaluated_at:
                self._accumulate(inventory, record)
        return inventory

    def eval_inventory(self, evaluated_at=None) -> dict:
        if evaluated_at is None:
            evaluated_at = datetime.now(timezone.utc)
        self.inventory = self._replay_transactions(evaluated_at)
        return self.inventory

    def apply_transaction(self, record: Transaction):
        """Reflects the given transaction record to the inventory.

        Nothing inside `Portfolio` calls this any more -- replay goes through
        `_replay_transactions`, which must not mutate `self.inventory` -- but
        it stays public for any external caller, sharing `_accumulate` with
        the replay path so the two cannot diverge.
        """
        self._accumulate(self.inventory, record)

    def eval_daily_inventories(self, from_date: datetime, to_date: datetime):
        """
        :param from_date: A timezone aware datetime markig the lower bound (inclusive)
        :param to_date: A timezone aware datetime marking the upper bound (exclusive)
        """
        for date in make_dates(from_date, to_date):
            yield date, self.eval_inventory(date)
            date += timedelta(days=1)

    def eval_daily_nav(
        self, from_date: datetime, to_date: datetime, historical: pd.DataFrame
    ):
        """Evaluate daily NAVs to make a DataFrame that looks like the following:

                ticker1 | quantity  | ticker2 | quantity  | ...
        date1 | price1  | quantity1 | price2  | quantity2 | ...
        date2 | price1  | quantity1 | price2  | quantity2 | ...

        :param from_date: A timezone aware datetime markig the lower bound (inclusive)
        :param to_date: A timezone aware datetime marking the upper bound (exclusive)
        """
        historical = historical[
            (historical.date >= from_date) & (historical.date < to_date)
        ]
        # dates: pd.Series = historical.groupby("date").head(1).date
        daily_inventories = {
            date.strftime("%Y%m%d"): inventory
            for date, inventory in self.eval_daily_inventories(from_date, to_date)
        }

        all_tickers = set()
        for inventory in daily_inventories.values():
            all_tickers.update(inventory.keys())

        daily_prices = {}
        for ticker in all_tickers:
            df = historical[historical.symbol == ticker][["date", "close"]].copy()

            # Skip tickers with no historical data in the date range
            if df.empty:
                continue

            df[f"{ticker}_quantity"] = df.apply(
                lambda x: daily_inventories[x.date.strftime("%Y%m%d")].get(ticker, 0),
                axis=1,
            )
            daily_prices[ticker] = df.set_index("date").rename(
                columns={"close": f"{ticker}_close"}
            )

        return daily_prices

    def eval_nav(self, evaluated_at: datetime, prices: dict) -> float:
        """Net asset value at a point in time.

        `prices` must already be expressed in one currency; this method
        performs no conversion. Holdings within `QUANTITY_EPSILON` of zero
        are skipped (by magnitude, not sign, so a short position is still
        valued) so that a delisted or fully-closed position with no price
        does not block valuation.

        This queries a historical inventory via `_replay_transactions`
        rather than `eval_inventory`, so evaluating a past date does not
        clobber `self.inventory` as a side effect.
        """
        inventory = self._replay_transactions(evaluated_at)
        total = 0.0
        for ticker, quantity in inventory.items():
            if abs(quantity) < QUANTITY_EPSILON:
                continue
            try:
                price = prices[ticker]
            except KeyError:
                raise MissingPriceException(
                    "No price for {} at {}".format(ticker, evaluated_at)
                ) from None
            total += price * quantity
        return total

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

        return {t: plan(t, diff) for t in diff if not is_cash(t)}

    # TODO: Tax on dividends?
    # TODO: Transaction fees?
    def apply_plan(
        self, plan: dict, start_dt: datetime, end_dt: datetime, dividend_records: dict
    ):
        def apply(t, q):
            self.inventory.setdefault(t, 0)
            while self.inventory[self.cash_ticker] - self.current_prices[t] * q < 0:
                if q > 0:
                    q -= 1
                else:
                    q += 1
            self.inventory[self.cash_ticker] -= self.current_prices[t] * q
            if self.inventory[self.cash_ticker] < 0:
                raise ValueError(
                    f"{self.cash_ticker} balance cannot be negative: {t}, {q}"
                )
            return self.inventory[t] + q

        # 'close' is actually 'adj close', which already includes
        # dividends/stock split/capital gains
        # self.inventory[self.cash_ticker] += self.calc_dividends_sum(start_dt, end_dt, dividend_records) * 0.85
        self.inventory = {t: apply(t, q) for t, q in plan.items()} | {
            self.cash_ticker: self.inventory[self.cash_ticker]
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
