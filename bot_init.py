from aiogram import Dispatcher
from aiogram.filters import Command
from handlers import *


def register_handlers(dp: Dispatcher):
    # Основные команды
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_admin, Command("admin"))
    dp.message.register(add_money_command, Command("add_money"))

    # Основные кнопки
    dp.message.register(btn_daily, F.text == "💰 Получить Абаюнду")
    dp.message.register(btn_balance, F.text == "🪙 Мой баланс")
    dp.message.register(show_shop, F.text == "🎁 Магазин")
    dp.message.register(start_transfer, F.text == "📤 Перевести")
    dp.message.register(show_help, F.text == "ℹ️ Помощь")
    dp.message.register(add_money_start, F.text == "💵 Начислить валюту")

    # Админ-функции
    dp.message.register(add_prize_start, F.text == "➕ Добавить приз")
    dp.message.register(add_prize_process, F.text.regexp(r'^[^|]+\|\d+\|[^|]+\|\-?\d+$'))
    dp.message.register(show_stats, F.text == "📊 Статистика")

    # Обработчики callback-кнопок
    dp.callback_query.register(shop_buy_handler, F.data == "shop_buy")
    dp.callback_query.register(shop_admin_handler, F.data == "shop_admin")