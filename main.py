
import logging
import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import openai
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID"))

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
openai.api_key = OPENAI_API_KEY

DB_PATH = "database.db"

# Кнопки
main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="/newtask"), KeyboardButton(text="/tasks")],
    [KeyboardButton(text="/today"), KeyboardButton(text="/chat Привет")]
], resize_keyboard=True)

# Создание таблицы
def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT,
            text TEXT
        )
        """)
        db.commit()

def get_all_tasks():
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        return db.execute("SELECT * FROM tasks ORDER BY time").fetchall()

def add_task_to_db(time, text):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("INSERT INTO tasks (time, text) VALUES (?, ?)", (time, text))
        db.commit()

def delete_task_from_db(task_id):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        db.commit()

@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("🤖 Привет! Я ассистент с кнопками и памятью.\nВыбери команду:", reply_markup=main_kb)

@dp.message(Command("newtask"))
async def newtask(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("✍️ Введи задачу в формате:\n2025-07-10 14:00 Встреча с клиентом")

@dp.message(F.text.regexp(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} "))
async def quick_task(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        parts = message.text.split(" ", 2)
        dt_str = f"{parts[0]} {parts[1]}"
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        text = parts[2]
        add_task_to_db(dt_str, text)
        scheduler.add_job(send_reminder, "date", run_date=dt, args=[text])
        await message.answer(f"✅ Задача добавлена:\n🕒 {dt_str} — {text}")
    except:
        await message.answer("❌ Ошибка. Формат: 2025-07-10 14:00 Текст")

@dp.message(Command("tasks"))
async def show_tasks(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    rows = get_all_tasks()
    if not rows:
        await message.answer("📭 Нет задач")
        return
    for task in rows:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Удалить", callback_data=f"del_{task['id']}")]
        ])
        await message.answer(f"🕒 {task['time']} — {task['text']}", reply_markup=kb)

@dp.callback_query(F.data.startswith("del_"))
async def delete_task(query: types.CallbackQuery):
    if query.from_user.id != OWNER_ID:
        return
    task_id = int(query.data.replace("del_", ""))
    delete_task_from_db(task_id)
    await query.message.edit_text("✅ Задача удалена")

@dp.message(Command("today"))
async def today_tasks(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    today = datetime.now().date().isoformat()
    rows = get_all_tasks()
    today_rows = [r for r in rows if r["time"].startswith(today)]
    if not today_rows:
        await message.answer("📭 На сегодня задач нет")
        return
    for task in today_rows:
        await message.answer(f"🕒 {task['time']} — {task['text']}")

@dp.message(Command("chat"))
async def chatgpt(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    prompt = message.text.replace("/chat", "").strip()
    if not prompt:
        await message.answer("❗ Напиши вопрос после /chat")
        return
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    await message.answer(response.choices[0].message.content)

async def send_reminder(text):
    await bot.send_message(chat_id=OWNER_ID, text=f"🔔 Напоминание: {text}")

async def main():
    init_db()
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
