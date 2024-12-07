import tracemalloc

import websocket
import json
import ssl
from pybit.unified_trading import HTTP
from config_data.config import Config, load_config
from user import message_bybit_binance

tracemalloc.start()
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


def on_message(ws, message):
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
            message_bybit_binance(-1002304776308, symbol, liquidation_type, f'{notional:.2f}')
            # print(f"Монета: {symbol}, Тип ликвидации: {liquidation_type}, Сумма: {notional:.2f} USDT")


# Обработка ошибок
def on_error(ws, error):
    print(f"Ошибка: {error}")


# Закрытие соединения
def on_close(ws, close_status_code, close_msg):
    print(f"Соединение закрыто. Код: {close_status_code}, Сообщение: {close_msg}")


# Открытие соединения
def on_open(ws):
    # Группируем тикеры для подписки
    params = {
        "op": "subscribe",
        "args": [f"liquidation.{symbol}" for symbol in s]  # Создаём массив тикеров
    }
    ws.send(json.dumps(params))

# URL для подключения к публичному WebSocket
url = "wss://stream.bybit.com/v5/public/linear"  # Исправленный URL для деривативов

# Игнорирование проверки SSL-сертификатов
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Подключение к WebSocket
ws = websocket.WebSocketApp(
    url,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)
ws.on_open = on_open
ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})