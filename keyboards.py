from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎒 Мои предметы")],
            [KeyboardButton(text="💰 Получить Абаюнду")],
            [KeyboardButton(text="🪙 Мой баланс"), KeyboardButton(text="🎁 Магазин")],
            [KeyboardButton(text="📄 Перевести"), KeyboardButton(text="ℹ️ Помощь")],
            [KeyboardButton(text="📈 Рейтинг NFT")],
            [KeyboardButton(text="🔙 Возвращаемся в главное меню")]
        ],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить приз"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="💵 Начислить валюту"), KeyboardButton(text="🔧 Управление")],
            [KeyboardButton(text="🔙 Возвращаемся в главное меню")]
        ],
        resize_keyboard=True
    )

def cancel():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")],
            [KeyboardButton(text="🔙 Возвращаемся в главное меню")]
        ],
        resize_keyboard=True
    )

def shop(is_admin: bool = False):
    buttons = [
        [InlineKeyboardButton(text="🛒 Купить приз", callback_data="shop_buy")],
        [InlineKeyboardButton(text="🔙 Возвращаемся в главное меню", callback_data="return_to_main")]
    ]
    if is_admin:
        buttons.insert(1, [InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="shop_admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
