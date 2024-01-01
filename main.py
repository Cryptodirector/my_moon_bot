import asyncio
import os

from aiogram import Bot, Dispatcher, F
from binance.error import ClientError
from binance.um_futures import UMFutures
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

TOKEN = os.environ.get("TOKEN")
KEY = os.environ.get("KEY")
SECRET = os.environ.get("SECRET")

um_futures_client = UMFutures(
    key=KEY,
    secret=SECRET
)

token = TOKEN

bot = Bot(token=token)
dp = Dispatcher()


class Trades:
    price = None
    order = None

    @classmethod
    async def get_price(cls):
        price = um_futures_client.ticker_price('IOTAUSDT')
        return price['price']

    @classmethod
    async def into_order(cls):
        cls.price = await Trades.get_price()
        current_price = -(float(cls.price) * 1.3 / 100) + float(cls.price)

        params = {
            'symbol': 'IOTAUSDT',
            'side': 'BUY',
            'type': 'LIMIT',
            'quantity': int(60),
            'timeInForce': 'GTC',
            'price': round(float(current_price), 4),
        }
        cls.order = um_futures_client.new_order(**params)

    @classmethod
    async def cancel_order(cls):
        um_futures_client.cancel_order(symbol='IOTAUSDT', orderId=cls.order['orderId'])

    @classmethod
    async def open_order(cls):
        order = um_futures_client.get_position_risk(symbol='IOTAUSDT')

        for orders in order:
            return orders['unRealizedProfit']

    @classmethod
    async def stop_loss(cls):
        get_price = await Trades.get_price()
        price = -(float(get_price) * 1 / 100) + float(get_price)
        params = {
            'symbol': 'IOTAUSDT',
            'side': 'SELL',
            'type': 'LIMIT',
            'timeInForce': 'GTC',
            'quantity': int(60),
            'price': float(round(price, 4)),
            'closePosition': 'True'
        }
        um_futures_client.new_order(**params)

    @classmethod
    async def take_profit(cls):
        price = (float(cls.price) * 0.6 / 100) + float(cls.price)

        params = {
            'symbol': 'IOTAUSDT',
            'side': 'SELL',
            'type': 'LIMIT',
            'timeInForce': 'GTC',
            'quantity': int(60),
            'price': float(round(price, 4)),
            'closePosition': 'True'
        }
        um_futures_client.new_order(**params)

    @classmethod
    @dp.message(F.text)
    async def msg(cls):

        await bot.send_message(chat_id='847449845', text='Зашла в сделку')

    @classmethod
    async def run(cls):

        opn_ord = await Trades.open_order()

        while float(opn_ord) == 0:
            opn_ord = await Trades.open_order()

            await Trades.into_order()
            await asyncio.sleep(1.6)
            try:
                await Trades.cancel_order()
            except ClientError:
                continue

        if float(opn_ord) > float(0):
            await Trades.msg()
            try:
                await Trades.stop_loss()
                await Trades.take_profit()

            except ClientError:
                await Trades.stop_loss()
                await Trades.take_profit()


async def main():
    await Trades.run()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
