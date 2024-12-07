from aiogram import Bot
import logging
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config_data.config import Config, load_config
import telebot


config: Config = load_config('.env')
bot = telebot.TeleBot(
    token=config.tg_bot.token)


logger3 = logging.getLogger(__name__)
handler3 = logging.FileHandler(f"{__name__}.log")
formatter3 = logging.Formatter("%(filename)s:%(lineno)d #%(levelname)-8s "
                               "[%(asctime)s] - %(name)s - %(message)s")
handler3.setFormatter(formatter3)
logger3.addHandler(handler3)
logger3.info(f"Testing the custom logger for module {__name__}")


def message_bybit_binance(tg_id, symbol, liquidation_type, price):
    sml = {'Short': '🟢', 'Long': '🔴'}
    coinglass = f'https://www.coinglass.com/tv/ru/Bybit_{symbol}'
    bybit = f'https://www.bybit.com/trade/usdt/{symbol}'
    binance = f'https://www.binance.com/ru/futures/{symbol}'
    bot.send_message(chat_id=tg_id, text=f'{sml[liquidation_type]}<b>{symbol[0:-4]}</b>, сумма ликвидации: {price} USDT\n'
                                         f'<a href=\"{bybit}\">ByBit</a> | <a href=\"{coinglass}\">CoinGlass</a> | <a href=\"{binance}\">Binance</a>',
                     parse_mode='HTML', disable_web_page_preview=True)