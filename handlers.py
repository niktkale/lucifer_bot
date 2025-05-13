from aiogram import types
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
import random
import logging
from config import Config
from database import db
from keyboards import main_menu, admin_menu, cancel, shop
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    if not db.get_user(user_id):
        db.register_user(user_id, username)
    await message.answer("👋 Добро пожаловать в Адский Банк!", reply_markup=main_menu())


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

async def is_admin(user_id: int) -> bool:
    user = db.get_user(user_id)
    return (user and user['is_admin']) or (user_id in Config.ADMIN_IDS)


async def register_user(user_id: int, username: str = None):
    db.execute(
        """INSERT OR IGNORE INTO users (user_id, username, is_admin) 
        VALUES (?, ?, ?)""",
        (user_id, username, user_id in Config.ADMIN_IDS)
    )
    db.commit()


async def can_get_daily(user_id: int) -> Tuple[bool, Optional[str]]:
    user = db.get_user(user_id)
    if not user or not user['last_daily']:
        return True, None

    last_time = datetime.fromisoformat(user['last_daily'])
    if datetime.now() - last_time < timedelta(hours=Config.DAILY_COOLDOWN):
        next_time = (last_time + timedelta(hours=Config.DAILY_COOLDOWN)).strftime("%H:%M")
        return False, next_time
    return True, None


# ================== ОСНОВНЫЕ КОМАНДЫ ==================
async def cmd_admin(message: types.Message):
    if await is_admin(message.from_user.id):
        await message.answer("⚙️ Панель администратора", reply_markup=admin_menu())
    else:
        await message.answer("🚫 Доступ запрещен!")


# ================== ОБРАБОТЧИКИ КНОПОК ==================

async def return_to_main_callback(callback: CallbackQuery):
    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "🔙 Возвращаемся в главное меню",
        reply_markup=main_menu()
    )
    await callback.answer()


async def return_to_main_menu(message: types.Message):
    try:
        await message.answer(
            "🔙 Возвращаемся в главное меню",
            reply_markup=main_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка в return_to_main_menu: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при возврате в меню",
            reply_markup=main_menu()
        )


async def btn_daily(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await register_user(user_id, message.from_user.username)
        user = db.get_user(user_id)

    can_daily, next_time = await can_get_daily(user_id)

    if not can_daily:
        await message.answer(
            f"⏳ Приходи через {Config.DAILY_COOLDOWN} часов!\n"
            f"⏰ Следующее начисление: {next_time}",
            reply_markup=main_menu()
        )
        return

    amount = random.randint(1, Config.MAX_DAILY)
    db.update_balance(user_id, amount)
    db.execute(
        "UPDATE users SET last_daily = ? WHERE user_id = ?",
        (datetime.now().isoformat(), user_id)
    )
    db.commit()

    await message.answer(
        f"🎉 Вы получили {amount} Абаюнд!\n"
        f"💵 Текущий баланс: {user['balance'] + amount}",
        reply_markup=main_menu()
    )


async def btn_balance(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await register_user(user_id, message.from_user.username)
        user = db.get_user(user_id)

    await message.answer(
        f"💎 Ваш баланс: {user['balance']} Абаюнд",
        reply_markup=main_menu()
    )


async def show_my_items(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await register_user(user_id, message.from_user.username)
    items = db.get_user_items(user_id)

    if not items:
        await message.answer("👜 У вас пока нет предметов.", reply_markup=main_menu())
        return

    text = "🎒 <b>Ваши предметы:</b>\n\n"
    for item in items:
        text += f"• <b>{item['name']}</b> - {item['cost']} Абаюнд\n📝 {item['description']}\n\n"

    await message.answer(text, parse_mode="HTML", reply_markup=main_menu())


async def show_shop(message: Message):
    prizes = db.get_prizes()
    user_id = message.from_user.id
    is_adm = db.get_user(user_id)["is_admin"] if db.get_user(user_id) else False

    if not prizes:
        text = "🛒 Магазин пуст!"
        if is_adm:
            text += "\n\nВы можете добавить призы через админ-панель"
        await message.answer(text, reply_markup=shop(is_adm))
        return

    text = "🎁 <b>Доступные призы:</b>\n\n"
    keyboard = []

    owned_items = db.execute(
        "SELECT prize_id FROM user_items WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    owned_ids = {row["prize_id"] for row in owned_items}

    for prize in prizes:
        stock = "∞" if prize["stock"] == -1 else prize["stock"]
        owned = prize["prize_id"] in owned_ids
        status = "🟢 Куплено" if owned else f"Купить {prize['name']}"
        callback = "noop" if owned else f"buy_{prize['prize_id']}"

        text += (
            f"• <b>{prize['name']}</b> - {prize['cost']} Абаюнд\n"
            f"📍 {prize['description']}\n"
            f"📦 Осталось: {stock}\n\n"
        )

        keyboard.append([
            InlineKeyboardButton(
                text=status,
                callback_data=callback
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="return_to_main")
    ])

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


# ================== АДМИН: Начисление валюты ==================

async def add_money_command(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    try:
        parts = message.text.split()
        if len(parts) != 3:
            raise ValueError

        username = parts[1][1:]  # убираем '@'
        amount = int(parts[2])

        user = db.execute(
            "SELECT user_id, username FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if not user:
            return await message.answer("❌ Пользователь не найден!", reply_markup=admin_menu())

        db.update_balance(user['user_id'], amount)
        db.add_transaction(0, user['user_id'], amount, "Админское начисление")
        await message.answer(
            f"✅ Начислено {amount} Абаюнд пользователю @{user['username']}",
            reply_markup=admin_menu()
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат! Используй: /add_money @username сумма",
            reply_markup=admin_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка начисления: {e}")
        await message.answer(
            "❌ Произошла ошибка при начислении",
            reply_markup=admin_menu()
        )

async def start_transfer(message: types.Message):
    await message.answer(
        "💸 Введите ник пользователя и сумму для перевода:\n"
        "Формат: <code>@username сумма</code>\n\n"
        "Пример: <code>@user123 100</code>",
        reply_markup=cancel(),
        parse_mode="HTML"
    )


async def process_transfer(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError

        username = parts[0][1:]  # Убираем @
        amount = int(parts[1])

        if amount < Config.MIN_TRANSFER:
            return await message.answer(
                f"❌ Минимальная сумма перевода: {Config.MIN_TRANSFER}",
                reply_markup=main_menu()
            )

        sender_id = message.from_user.id
        recipient = db.execute(
            "SELECT user_id, username FROM users WHERE username = ? AND user_id != ?",
            (username, sender_id)
        ).fetchone()

        if not recipient:
            return await message.answer(
                "❌ Пользователь не найден или нельзя переводить себе!",
                reply_markup=main_menu()
            )
        if amount <= 0:
            return await message.answer(
                "❌ Сумма перевода должна быть положительной!",
                reply_markup=main_menu()
            )

        sender = db.get_user(sender_id)
        if not sender or sender['balance'] < amount:
            return await message.answer(
                "❌ Недостаточно средств на балансе!",
                reply_markup=main_menu()
            )

        db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, sender_id))
        db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, recipient['user_id']))
        db.add_transaction(sender_id, recipient['user_id'], amount, "Перевод")
        db.commit()

        await message.answer(
            f"✅ Успешно переведено {amount} Абаюнд пользователю @{recipient['username']}",
            reply_markup=main_menu()
        )

        try:
            await message.bot.send_message(
                recipient['user_id'],
                f"💸 Вам перевели {amount} Абаюнд от @{message.from_user.username}"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить получателя: {e}")

    except ValueError:
        await message.answer(
            "❌ Неверный формат! Используйте: @username сумма",
            reply_markup=main_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка перевода: {e}")
        await message.answer(
            "❌ Произошла ошибка при переводе",
            reply_markup=main_menu()
        )


async def process_buy(callback: CallbackQuery):
    if not callback.data.startswith("buy_"):
        return

    prize_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    # Проверка: уже ли куплен этот приз
    existing = db.execute(
        "SELECT 1 FROM user_items WHERE user_id = ? AND prize_id = ?",
        (user_id, prize_id)
    ).fetchone()

    if existing:
        await callback.message.answer("❌ Вы уже приобрели этот предмет.", reply_markup=main_menu())
        await callback.answer()
        return

    # Попытка покупки
    success, message = db.buy_prize(user_id, prize_id)
    await callback.message.answer(message, reply_markup=main_menu())
    await callback.answer()

# ================== КОМАНДА ПОКАЗА ПОМОЩИ ==================

async def show_help(message: types.Message):
    help_text = (
        "ℹ️ <b>Помощь по боту</b>\n\n"
        "💰 <b>Получить Абаюнду</b> — ежедневный бонус\n"
        "🪙 <b>Мой баланс</b> — проверить баланс\n"
        "📤 <b>Перевести</b> — отправить деньги другому пользователю\n"
        "🎁 <b>Магазин</b> — просмотр доступных призов\n"
        "🎒 <b>Мои предметы</b> — список купленных предметов\n\n"
        "Для поддержки писать @nikita_lee"
    )
    await message.answer(help_text, reply_markup=main_menu(), parse_mode="HTML")


# ================== АДМИН-КОМАНДА ДЛЯ ЗАПУСКА НАЧИСЛЕНИЯ ==================

async def add_money_start(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    await message.answer(
        "💵 Введите команду для начисления валюты:\n"
        "<code>/add_money @username сумма</code>\n\n"
        "Пример:\n"
        "<code>/add_money @user123 500</code>",
        reply_markup=cancel(),
        parse_mode="HTML"
    )
# ================== АДМИН: ДОБАВЛЕНИЕ ПРИЗА ==================

async def add_prize_start(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    await message.answer(
        "📝 Введите данные приза в формате:\n"
        "<code>Название|Цена|Описание|Количество</code>\n\n"
        "Пример:\n"
        "<code>Золотая карта|500|Дает бонус +10%|10</code>",
        reply_markup=cancel(),
        parse_mode="HTML"
    )


async def add_prize_process(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    try:
        name, cost, desc, stock = message.text.split("|")
        name = name.strip()
        cost = int(cost.strip())
        desc = desc.strip()
        stock = int(stock.strip())

        existing = db.execute(
            "SELECT 1 FROM prizes WHERE name = ?",
            (name,)
        ).fetchone()

        if existing:
            return await message.answer(
                "❌ Приз с таким названием уже существует!",
                reply_markup=admin_menu()
            )

        db.execute(
            "INSERT INTO prizes (name, cost, description, stock) VALUES (?, ?, ?, ?)",
            (name, cost, desc, stock)
        )
        db.commit()
        await message.answer(
            f"✅ Приз успешно добавлен!\n\n"
            f"🎁 <b>Название:</b> {name}\n"
            f"💵 <b>Цена:</b> {cost} Абаюнд\n"
            f"📝 <b>Описание:</b> {desc}\n"
            f"📦 <b>Количество:</b> {'∞' if stock == -1 else stock}",
            reply_markup=admin_menu(),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer(
            "❌ Неверный формат данных! Используйте:\nНазвание|Цена|Описание|Количество",
            reply_markup=admin_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка добавления приза: {e}")
        await message.answer(
            "❌ Произошла ошибка при добавлении приза",
            reply_markup=admin_menu()
        )
    if cost <= 0:
        return await message.answer(
            "❌ Цена должна быть положительной!",
            reply_markup=admin_menu()
        )
    if stock < -1:
        return await message.answer(
            "❌ Количество должно быть -1 (бесконечно) или положительным!",
            reply_markup=admin_menu()
        )


# ================== АДМИН: СТАТИСТИКА ==================

async def show_stats(message: types.Message):
    if not await is_admin(message.from_user.id):
        return

    stats = db.execute("""
        SELECT 
            COUNT(*) as total_users,
            SUM(balance) as total_balance,
            (SELECT COUNT(*) FROM transactions) as total_transactions
        FROM users
    """).fetchone()

    await message.answer(
        f"📊 <b>Статистика:</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"💰 Общий баланс: {stats['total_balance'] or 0} Абаюнд\n"
        f"🔄 Транзакций: {stats['total_transactions']}",
        reply_markup=admin_menu(),
        parse_mode="HTML"
    )


# ================== КНОПКИ МАГАЗИНА ==================

async def shop_buy_handler(callback: CallbackQuery):
    try:
        await callback.answer("🛒 Выберите приз из списка выше", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка в shop_buy_handler: {e}")
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


async def shop_admin_handler(callback: CallbackQuery):
    try:
        if await is_admin(callback.from_user.id):
            await callback.message.answer(
                "⚙️ Панель администратора",
                reply_markup=admin_menu()
            )
        else:
            await callback.answer("❌ У вас нет прав администратора!", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка в shop_admin_handler: {e}")
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)


# ================== ОБРАБОТКА ПОКУПКИ ПРЕДМЕТОВ ==================

async def process_buy(callback: CallbackQuery):
    if not callback.data.startswith("buy_"):
        return
    prize_id = int(callback.data.split("_")[1])
    success, message = db.buy_prize(callback.from_user.id, prize_id)
    await callback.message.answer(message, reply_markup=main_menu())
    await callback.answer()



# ================== NFT РЕЙТИНГ ==================

async def show_nft_ranking(message: Message):
    rows = db.execute("""
        SELECT 
            u.username,
            COUNT(ui.prize_id) AS count,
            GROUP_CONCAT(p.name, ', ') AS items,
            SUM(p.cost) AS total_cost
        FROM user_items ui
        JOIN users u ON u.user_id = ui.user_id
        JOIN prizes p ON p.prize_id = ui.prize_id
        WHERE p.is_nft = 1
        GROUP BY ui.user_id
        ORDER BY total_cost DESC
        LIMIT 10;
    """).fetchall()

    if not rows:
        await message.answer("ℹ️ Пока никто не приобрел NFT-предметы.")
        return

    text = "🏆 <b>NFT Рейтинг:</b>\n\n"
    for i, row in enumerate(rows, 1):
        username = row['username'] or 'Без ника'
        count = row['count']
        cost = row['total_cost']
        items = row['items']
        text += f"{i}. @{username} — {count} предмет(ов) на {cost} Абаюнд\n🎁 {items}\n\n"

    await message.answer(text, parse_mode="HTML", reply_markup=main_menu())
