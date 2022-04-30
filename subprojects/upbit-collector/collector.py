from datetime import datetime
import json
import os

import aiohttp
import aiofiles
import asyncio
import websockets
import uuid64

from typing import Union


BASE_PATH = os.path.dirname(__file__)
LOG_PATH = os.path.join(BASE_PATH, "logs")


def parse_currency_pair(value: str):
    key_currency, currency = value.split("-")
    return currency, key_currency


class Model:
    def __iter__(self):
        for column in self.columns:
            value = getattr(self, column)
            if value is None:
                yield column, None
            elif isinstance(value, (int, float, bool)):
                yield column, value
            else:
                yield column, str(value)


class UpbitOrderbook(Model):

    # b'{"type":"orderbook","code":"KRW-ETH","timestamp":1641420543245,"total_ask_size":92.87027002,"total_bid_size":72.42660147,"orderbook_units":[{"ask_price":4407000.0,"bid_price":4403000.0,"ask_size":9.39739072,"bid_size":0.01135589},{"ask_price":4408000.0,"bid_price":4402000.0,"ask_size":10.7262,"bid_size":4.22910973},{"ask_price":4409000.0,"bid_price":4401000.0,"ask_size":12.93587276,"bid_size":0.01590547},{"ask_price":4410000.0,"bid_price":4400000.0,"ask_size":8.9517781,"bid_size":7.47463308},{"ask_price":4411000.0,"bid_price":4399000.0,"ask_size":1.509,"bid_size":2.20840275},{"ask_price":4412000.0,"bid_price":4398000.0,"ask_size":0.63090328,"bid_size":1.20843104},{"ask_price":4413000.0,"bid_price":4397000.0,"ask_size":0.04533091,"bid_size":10.74122291},{"ask_price":4415000.0,"bid_price":4396000.0,"ask_size":20.66047486,"bid_size":3.23},{"ask_price":4416000.0,"bid_price":4395000.0,"ask_size":0.29737862,"bid_size":9.53567619},{"ask_price":4417000.0,"bid_price":4394000.0,"ask_size":0.06779596,"bid_size":5.94741953},{"ask_price":4418000.0,"bid_price":4393000.0,"ask_size":15.6526326,"bid_size":3.12847003},{"ask_price":4419000.0,"bid_price":4392000.0,"ask_size":1.0,"bid_size":8.40977349},{"ask_price":4420000.0,"bid_price":4391000.0,"ask_size":10.6708258,"bid_size":4.54105641},{"ask_price":4422000.0,"bid_price":4390000.0,"ask_size":0.0455,"bid_size":8.01551888},{"ask_price":4423000.0,"bid_price":4389000.0,"ask_size":0.27918641,"bid_size":3.72962607}],"stream_type":"REALTIME"}'

    columns = ["currency", "key_currency", "timestamp", "ask_prices", "ask_volumes", "bid_prices", "bid_volumes", "ask_volume", "bid_volume"]

    def __init__(self, **kwargs):
        for col in self.columns:
            setattr(self, col, kwargs[col])

    @classmethod
    def from_json(cls, json_data: dict):
        currency, key_currency = parse_currency_pair(json_data["code"])
        records = json_data["orderbook_units"]
        asks = [(record["ask_price"], record["ask_size"]) for record in records]
        bids = [(record["bid_price"], record["bid_size"]) for record in records]

        orderbook = UpbitOrderbook(
            currency=currency,
            key_currency=key_currency,
            timestamp=datetime.utcfromtimestamp(json_data["timestamp"] / 1000.0),
            ask_prices=[p for p, _ in asks],
            ask_volumes=[v for _, v in asks],
            bid_prices=[p for p, _ in bids],
            bid_volumes=[v for _, v in bids],
            ask_volume=sum([v for _, v in asks]),
            bid_volume=sum([v for _, v in bids]),
        )
        return orderbook

    @property
    def ask(self):
        return self.ask_prices[0]

    @property
    def bid(self):
        return self.bid_prices[0]


class UpbitTrade(Model):

    # {"type":"trade","code":"KRW-BTC","timestamp":1650787278433,"trade_date":"2022-04-24","trade_time":"08:01:18","trade_timestamp":1650787278000,"trade_price":50000000.0000,"trade_volume":0.03090000,"ask_bid":"ASK","prev_closing_price":49742000.00000000,"change":"RISE","change_price":258000.00000000,"sequential_id":1650787278000000,"stream_type":"SNAPSHOT"}

    columns = ["currency", "key_currency", "timestamp", "trade_type", "stream_type", "price", "volume", "prev_closing_price"]

    def __init__(self, **kwargs):
        for col in self.columns:
            setattr(self, col, kwargs[col])

    @classmethod
    def from_json(cls, json_data: dict):
        currency, key_currency = parse_currency_pair(json_data["code"])

        trade = UpbitTrade(
            id=json_data["sequential_id"],
            currency=currency,
            key_currency=key_currency,
            timestamp=datetime.utcfromtimestamp(json_data["trade_timestamp"] / 1000.0),
            trade_type=json_data["ask_bid"].lower(),
            stream_type=json_data["stream_type"].lower(),
            price=json_data["trade_price"],
            volume=json_data["trade_volume"],
            prev_closing_price=json_data["prev_closing_price"],
        )
        return trade



session = aiohttp.ClientSession()
# TODO: We might want to store this in a database (e.g., Redis)
codes = [
    "KRW-ETH", "KRW-BTC", "KRW-XRP", "KRW-LINK", "KRW-ELF", "KRW-MTL",
    "KRW-POLY", "KRW-KNC", "KRW-KAVA", "KRW-STEEM", "KRW-IOST", "KRW-ZIL",
]


async def collect():
    async with websockets.connect("wss://api.upbit.com/websocket/v1") as websocket:
        req = [
            {"ticket":"test"},
            {"type":"orderbook", "codes":codes},
            {"type":"trade", "codes":codes},
        ]
        await websocket.send(json.dumps(req))

        while True:
            # TODO: Could we 'asynchronize' this operation as well?
            resp = await websocket.recv()
            json_data = json.loads(resp)
            resp_type = json_data["type"]
            if resp_type == "orderbook":
                asyncio.ensure_future(process_orderbook(json_data))
            elif resp_type == "trade":
                asyncio.ensure_future(process_trade(json_data))
            else:
                raise ValueError(f"Unsupported response type: {resp_type}")


async def process_orderbook(json_data: dict):
    orderbook = UpbitOrderbook.from_json(json_data)
    # NOTE: We might want to re-consider how we issue IDs
    orderbook.id = uuid64.issue()
    # if orderbook.id == prev_orderbook_id:
    #     orderbook.id += 1
    print(f"\r{orderbook.timestamp} {orderbook.currency}/{orderbook.key_currency} {orderbook.ask}, {orderbook.bid}\r", end="")
    await write_to_file(orderbook, "orderbook")
    # prev_orderbook_id = orderbook.id


async def process_trade(json_data: dict):
    trade = UpbitTrade.from_json(json_data)
    await write_to_file(trade, "trade")


async def write_to_file(record: Union[UpbitTrade, UpbitOrderbook], entity_name):
    dt_partition = record.timestamp.strftime("%Y%m%d-%H")
    filename = f"{LOG_PATH}/{entity_name}/{entity_name}-{dt_partition}.ndjson"
    async with aiofiles.open(filename, mode="a") as fout:
        await fout.write(json.dumps(dict(record), separators=(",", ":")) + "\n")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    while True:
        try:
            loop.run_until_complete(collect())
        except websockets.exceptions.ConnectionClosedError:
            print("Connection closed, reconnecting...")
            loop.run_until_complete(session.close())
            loop.run_until_complete(asyncio.sleep(0.25))
