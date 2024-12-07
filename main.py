import asyncio
import json
import ssl
import logging

import requests
import websockets
from pybit.unified_trading import HTTP
from config_data.config import Config, load_config
from user import message_bybit_binance, message_binance

# Настройка логирования
logger = logging.getLogger(__name__)
handler = logging.FileHandler("main.log")
formatter = logging.Formatter("%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

config: Config = load_config('.env')
session = HTTP(
    testnet=False,
    api_key=config.by_bit.api_key,
    api_secret=config.by_bit.api_secret,
)

data_bybit = session.get_tickers(category="linear")

TOP_50_COINS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT', 'XRPUSDT', 'DOTUSDT', 'SOLUSDT', 'LINKUSDT', 'LTCUSDT', 'BCHUSDT', 'UNIUSDT', 'XLMUSDT', 'FILUSDT', 'THETAUSDT', 'VETUSDT', 'TRXUSDT', 'EOSUSDT', 'AAVEUSDT', 'XMRUSDT', 'ATOMUSDT', 'ALGOUSDT', 'CROUSDT', 'MKRUSDT', 'ETCUSDT', 'NEOUSDT', 'CAKEUSDT', 'COMPUSDT', 'MIOTAUSDT', 'DASHUSDT', 'KSMUSDT', 'ZECUSDT', 'XEMUSDT', 'XTZUSDT', 'BSVUSDT', 'AXSUSDT', 'WAVESUSDT', 'SUSHIUSDT', 'EGLDUSDT', 'MANAUSDT', 'HNTUSDT', 'HEDGUSDT', 'SHIBUSDT', 'CELUSDT', 'HTUSDT', 'ENJUSDT', 'GRTUSDT', 'ZRXUSDT', 'RENUSDT', 'BATUSDT']
s = [dicts['symbol'] for dicts in data_bybit['result']['list']
     if 'USDT' in dicts['symbol'] and dicts['symbol'] not in TOP_50_COINS]

url = 'https://fapi.binance.com/fapi/v2/ticker/price'
response = requests.get(url)
data_binance = response.json()
binance_symbol = [data['symbol'] for data in data_binance if 'USDT' in data['symbol']]


async def on_message(ws, message):
    try:
        data = json.loads(message)
        if "data" in data and data["topic"].startswith("liquidation."):
            liquidation = data["data"]
            symbol = liquidation["symbol"]
            side = liquidation["side"]
            qty = float(liquidation["size"])
            price = float(liquidation["price"])
            notional = qty * price

            if notional >= 15000:
                liquidation_type = "Long" if side == "Buy" else "Short"
                if symbol in binance_symbol:
                    await message_bybit_binance(-1002304776308, symbol, liquidation_type, f'{notional:.2f}', price)
                else:
                    await message_binance(-1002304776308, symbol, liquidation_type, f'{notional:.2f}', price)
                logger.info(f"Обработано событие ликвидации: {symbol}, Тип: {liquidation_type}, Сумма: {notional:.2f} USDT")
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения WebSocket: {e}")


async def on_error(ws, error):
    logger.error(f"Ошибка WebSocket: {error}")


async def on_close(ws, close_status_code, close_msg):
    logger.warning(f"Соединение закрыто. Код: {close_status_code}, Сообщение: {close_msg}")


async def on_open(ws):
    try:
        params = {
            "op": "subscribe",
            "args": [f"liquidation.{symbol}" for symbol in s]
        }
        await ws.send(json.dumps(params))
        logger.info("Подписка на ликвидации отправлена.")
    except Exception as e:
        logger.error(f"Ошибка при подписке на ликвидации: {e}")


url = "wss://stream.bybit.com/v5/public/linear"
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


async def main():
    try:
        async with websockets.connect(url, ssl=ssl_context) as ws:
            logger.info("Соединение с WebSocket открыто.")
            await on_open(ws)

            while True:
                message = await ws.recv()
                await on_message(ws, message)
    except Exception as e:
        logger.critical(f"Критическая ошибка в основном цикле: {e}")


if __name__ == "__main__":
    asyncio.run(main())