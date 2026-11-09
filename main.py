import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Читаем секреты из переменных окружения (GitHub Secrets подставит их при запуске)
BOT_TOKEN = os.environ["BOT_TOKEN"]
MY_USER_ID = int(os.environ["MY_USER_ID"])

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Простая база данных: создаём таблицу, если её нет
def init_db():
    conn = sqlite3.connect("budget.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            category TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

# Обработчик команды /start
@dp.message(Command("start"))
async def start(message: types.Message):
    # Проверяем, что пишет именно владелец
    if message.from_user.id != MY_USER_ID:
        await message.answer("Это личный бот. Доступ запрещён.")
        return
    await message.answer(
        "Привет! Я бот для учёта трат.\n\n"
        "Пока я умею только записывать траты:\n"
        "/spend 50 Маркетплейсы наушники\n\n"
        "Позже добавим бюджеты, возвраты и отчёты."
    )

# Обработчик команды /spend
@dp.message(Command("spend"))
async def spend(message: types.Message):
    if message.from_user.id != MY_USER_ID:
        return
    
    # Разбираем текст: /spend 50 Маркетплейсы наушники
    parts = message.text.split(maxsplit=3)
    if len(parts) < 3:
        await message.answer("Формат: /spend <сумма> <категория> <описание>")
        return
    
    try:
        amount = float(parts[1])
    except ValueError:
        await message.answer("Сумма должна быть числом. Например: /spend 50 Маркетплейсы наушники")
        return
    
    category = parts[2]
    description = parts[3] if len(parts) > 3 else ""
    
    # Записываем в базу
    conn = init_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (user_id, amount, category, description) VALUES (?, ?, ?, ?)",
        (message.from_user.id, amount, category, description)
    )
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ Записано: {amount} BYN, {category}, {description}")

# Обработчик команды /history
@dp.message(Command("history"))
async def history(message: types.Message):
    if message.from_user.id != MY_USER_ID:
        return
    
    conn = init_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT amount, category, description, created_at FROM transactions ORDER BY id DESC LIMIT 10"
    )
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        await message.answer("Пока нет записей.")
        return
    
    lines = ["📋 Последние 10 трат:\n"]
    for row in rows:
        amount, category, description, created_at = row
        lines.append(f"• {amount} BYN — {category} — {description} ({created_at})")
    
    await message.answer("\n".join(lines))

# Главная функция: запускаем бота на короткое время
async def main():
    # get_updates: забираем только новые сообщения, не обработанные ранее
    # Это важно, потому что GitHub Actions каждый раз запускает новый процесс
    await dp.start_polling(bot, handle_signals=False)

if __name__ == "__main__":
    asyncio.run(main())