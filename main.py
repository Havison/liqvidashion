import asyncio
import json
import ssl
import websockets
from pybit.unified_trading import HTTP
from config_data.config import Config, load_config
from user import message_bybit_binance

config: Config = load_config('.env')
session = HTTP(
    testnet=False,
    api_key=config.by_bit.api_key,
    api_secret=config.by_bit.api_secret,
)

data_bybit = session.get_tickers(category="linear")

TOP_50_COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT",
    "SOLUSDT", "MATICUSDT", "DOTUSDT", "LTCUSDT", "SHIBUSDT", "TRXUSDT",
    "AVAXUSDT", "UNIUSDT", "ATOMUSDT", "LINKUSDT", "XMRUSDT", "ETCUSDT",
    "FILUSDT", "APEUSDT", "APTUSDT", "NEARUSDT", "ALGOUSDT", "QNTUSDT",
    "VETUSDT", "ICPUSDT", "GRTUSDT", "EOSUSDT", "MANAUSDT", "SANDUSDT",
    "AAVEUSDT", "KLAYUSDT", "XTZUSDT", "THETAUSDT", "AXSUSDT", "FTMUSDT",
    "RUNEUSDT", "CHZUSDT", "CAKEUSDT", "LDOUSDT", "ZILUSDT", "ENJUSDT",
    "1INCHUSDT", "IMXUSDT", "GALAUSDT", "CRVUSDT", "DYDXUSDT", "SUSHIUSDT"
]
s = [dicts['symbol'] for dicts in data_bybit['result']['list']
     if 'USDT' in dicts['symbol'] and dicts['symbol'] not in TOP_50_COINS]


async def on_message(ws, message):
    data = json.loads(message)
    if "data" in data and data["topic"].startswith("liquidation."):
        liquidation = data["data"]
        symbol = liquidation["symbol"]
        side = liquidation["side"]  # Тип ликвидации: "Buy" или "Sell"
        qty = float(liquidation["size"])  # Количество монет
        price = float(liquidation["price"])  # Цена ликвидации
        notional = qty * price  # Сумма ликвидации в USDT
        if notional >= 15000:
            liquidation_type = "Short" if side == "Buy" else "Long"
            await message_bybit_binance(-1002304776308, symbol, liquidation_type, f'{notional:.2f}')


# Обработка ошибок
async def on_error(ws, error):
    print(f"Ошибка: {error}")


# Закрытие соединения
async def on_close(ws, close_status_code, close_msg):
    print(f"Соединение закрыто. Код: {close_status_code}, Сообщение: {close_msg}")


# Открытие соединения
async def on_open(ws):
    # Группируем тикеры для подписки
    params = {
        "op": "subscribe",
        "args": [f"liquidation.{symbol}" for symbol in s]  # Создаём массив тикеров
    }
    await ws.send(json.dumps(params))


# URL для подключения к публичному WebSocket
url = "wss://stream.bybit.com/v5/public/linear"  # Исправленный URL для деривативов

# Игнорирование проверки SSL-сертификатов
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


async def main():
    async with websockets.connect(url, ssl=ssl_context) as ws:
        await on_open(ws)

        while True:
            message = await ws.recv()
            await on_message(ws, message)


# Запуск асинхронной функции
if __name__ == "__main__":
    asyncio.run(main())