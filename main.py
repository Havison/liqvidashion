import asyncio
import json
import ssl
import logging
import websockets
from pybit.unified_trading import HTTP
from config_data.config import Config, load_config
from user import message_bybit_binance, message_binance
import httpx

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

binance_symbol = []  # Список всех фьючерсных пар Binance с USDT
TOP_50_BYBIT = []  # Топ-50 пар Bybit по объему


# Функция для получения всех фьючерсных пар Binance с USDT
async def fetch_binance_futures_symbols():
    try:
        logger.info("Запрос всех фьючерсных пар Binance с USDT...")
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()
            global binance_symbol
            binance_symbol = [
                symbol["symbol"] for symbol in data["symbols"] if symbol["quoteAsset"] == "USDT"
            ]
            logger.info(f"Обновлен список фьючерсных пар Binance: {binance_symbol}")
    except Exception as e:
        logger.error(f"Ошибка при обновлении списка фьючерсных пар Binance: {e}")


# Функция для получения топ-50 торговых пар Bybit
async def fetch_top_50_bybit():
    try:
        logger.info("Запрос топ-50 торговых пар с Bybit...")
        data_bybit = session.get_tickers(category="linear")
        usdt_pairs = [
            {
                "symbol": ticker["symbol"],
                "volume_24h": float(ticker["turnover24h"])  # Оборот за 24 часа
            }
            for ticker in data_bybit["result"]["list"]
            if "USDT" in ticker["symbol"]
        ]
        sorted_pairs = sorted(usdt_pairs, key=lambda x: x["volume_24h"], reverse=True)
        global TOP_50_BYBIT
        TOP_50_BYBIT = [pair["symbol"] for pair in sorted_pairs[:50]]
        logger.info(f"Обновлен топ-50 Bybit: {TOP_50_BYBIT}")
    except Exception as e:
        logger.error(f"Ошибка при обновлении топ-50 Bybit: {e}")


# Фоновая задача для обновления топ-50 Bybit и списка пар Binance каждые 24 часа
async def update_symbols():
    while True:
        await fetch_top_50_bybit()
        await fetch_binance_futures_symbols()
        await asyncio.sleep(24 * 60 * 60)  # Обновление каждые 24 часа


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

            if notional >= 15000 and symbol not in TOP_50_BYBIT:
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
        await fetch_top_50_bybit()  # Запросить топ-50 перед подпиской
        params = {
            "op": "subscribe",
            "args": [f"liquidation.{symbol}" for symbol in TOP_50_BYBIT]
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
        # Запуск фонового обновления символов
        asyncio.create_task(update_symbols())

        # Подключение к WebSocket
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