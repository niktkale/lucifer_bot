import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from config import Config
from database import Database
from handlers import (
    cmd_start,
    cmd_admin,
    add_money_command,
    btn_daily,
    btn_balance,
    show_shop,
    show_my_items,
    start_transfer,
    show_help,
    add_money_start,
    add_prize_start,
    add_prize_process,
    show_stats,
    shop_buy_handler,
    shop_admin_handler,
    return_to_main_callback,
    return_to_main_menu,
    process_buy
)
from handlers import show_nft_ranking
db = Database()

async def main():
    bot = Bot(token=Config.TOKEN)
    dp = Dispatcher()

    # Основные команды
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_admin, Command("admin"))
    dp.message.register(add_money_command, Command("add_money"))

    # Основные кнопки
    dp.message.register(btn_daily, F.text == "💰 Получить Абаюнду")
    dp.message.register(btn_balance, F.text == "🪙 Мой баланс")
    dp.message.register(show_shop, F.text == "🎁 Магазин")
    dp.message.register(show_my_items, F.text == "🎒 Мои предметы")
    dp.message.register(start_transfer, F.text == "📄 Перевести")
    dp.message.register(show_help, F.text == "ℹ️ Помощь")
    dp.message.register(show_nft_ranking, F.text == "📈 Рейтинг NFT")

    # Админ-функции
    dp.message.register(add_money_start, F.text == "💵 Начислить валюту")
    dp.message.register(add_prize_start, F.text == "➕ Добавить приз")
    dp.message.register(add_prize_process, F.text.regexp(r'^[^|]+\|\d+\|[^|]+\|\-?\d+$'))
    dp.message.register(show_stats, F.text == "📊 Статистика")

    # Обработчики callback-кнопок
    dp.callback_query.register(shop_buy_handler, F.data == "shop_buy")
    dp.callback_query.register(shop_admin_handler, F.data == "shop_admin")
    dp.callback_query.register(process_buy, F.data.startswith("buy_"))
    dp.callback_query.register(return_to_main_callback, F.data == "return_to_main")

    # Кнопка "назад" в основном меню
    dp.message.register(return_to_main_menu, F.text == "🔙 Возвращаемся в главное меню")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
