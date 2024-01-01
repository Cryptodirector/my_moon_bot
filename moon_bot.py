import asyncio
import os
import datetime
import time

from binance.um_futures import UMFutures
from dotenv import load_dotenv, find_dotenv
from headers import headers
from requests.exceptions import ConnectionError

from main import Trades

import aiohttp

load_dotenv(find_dotenv())

KEY = os.environ.get("KEY")
SECRET = os.environ.get("SECRET")

um_futures_client = UMFutures(
    key=KEY,
    secret=SECRET
)


class Trade:
    symbols = []

    @classmethod
    async def get_all_futures_symbols(cls):
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get('https://www.binance.com/fapi/v1/exchangeInfo?showall=false') as response:
                result = await response.json()

                for results in result['symbols']:
                    cls.symbols.append(results['symbol'])

        return cls.symbols

    @classmethod
    async def get_price(cls, symbol: str):
        price = um_futures_client.ticker_price(symbol)
        return price['price']

    @classmethod
    async def into_order(cls, symbol: str, quantity: int):
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quantity': int(quantity),
            'recvWindow': 6000
        }
        um_futures_client.new_order(**params)

    @classmethod
    async def stop_loss(cls, symbol):
        get_price = await Trade.get_price(symbol=symbol)
        price = -(float(get_price) * 0.2 / 100) + float(get_price)
        params = {
            'symbol': symbol,
            'side': 'SELL',
            'type': 'STOP_MARKET',
            'stopPrice': float(round(price, 4)),
            'closePosition': 'True'
        }
        um_futures_client.new_order(**params)

    @classmethod
    async def take_profit(cls, symbol):
        get_price = await Trade.get_price(symbol=symbol)
        price = (float(get_price) * 0.7 / 100) + float(get_price)

        params = {
            'symbol': symbol,
            'side': 'SELL',
            'type': 'TAKE_PROFIT_MARKET',
            'stopPrice': float(round(price, 4)),
            'closePosition': 'True'
        }
        um_futures_client.new_order(**params)

    @classmethod
    async def get_kline_1m(cls):
        try:
            keep_running = True

            while keep_running is True:
                now = datetime.datetime.now()
                second = now.second
                if int(second) == 1:

                    data = await Trade.get_all_futures_symbols()

                    for symbol in data[0:145]:
                        if 'USDT' in symbol:

                            try:
                                kline = um_futures_client.klines(
                                    symbol=f'{symbol}',
                                    interval='1m',
                                    limit=1,
                                    recvWindow=6000
                                )

                                for klines in kline:
                                    my_deposit = 20 / float(klines[4])

                                    if float(klines[4]) > float(my_deposit):
                                        continue
                                    if klines[1] < klines[4]:
                                        time.sleep(2)
                                        num = ((float(klines[4]) - float(klines[1])) / float(klines[1])) * 100
                                        if float(num) >= 2.2:
                                            print(symbol)
                                            await Trade.into_order(symbol=symbol, quantity=int(my_deposit))
                                            await Trade.stop_loss(symbol=symbol)
                                            await Trade.take_profit(symbol=symbol)
                                            await Trades.msg()
                                            keep_running = False
                                            break
                            except KeyError:
                                continue

                        if keep_running is False:
                            time.sleep(600)
                            await Trade.get_kline_1m()
                        # break
        except ConnectionError:
            await Trade.get_kline_1m()


if __name__ == '__main__':
    asyncio.run(Trade.get_kline_1m())