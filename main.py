
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import openai
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OWNER_ID = int(os.getenv("OWNER_ID"))

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
openai.api_key = OPENAI_API_KEY

tasks = []

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("Привет! Я твой личный ассистент. Напиши /newtask чтобы создать задачу.")

@dp.message(Command("newtask"))
async def newtask_handler(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("Отправь задачу в формате: `2025-07-07 14:00 Встреча с клиентом`")

@dp.message(Command("today"))
async def today_handler(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    today = datetime.now().date()
    text = "Задачи на сегодня:\n"
    for t in tasks:
        if t['time'].date() == today:
            text += f"🕒 {t['time'].strftime('%H:%M')} — {t['text']}\n"
    await message.answer(text)

@dp.message(Command("chat"))
async def chat_handler(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    prompt = message.text.replace("/chat", "").strip()
    if not prompt:
        await message.answer("Напиши вопрос после команды /chat")
        return
    reply = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    await message.answer(reply.choices[0].message.content)

@dp.message()
async def task_input_handler(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        parts = message.text.split(" ", 2)
        dt = datetime.strptime(f"{parts[0]} {parts[1]}", "%Y-%m-%d %H:%M")
        text = parts[2]
        tasks.append({"time": dt, "text": text})
        scheduler.add_job(send_reminder, "date", run_date=dt, args=[text])
        await message.answer(f"✅ Задача добавлена: {dt} — {text}")
    except:
        await message.answer("❌ Неверный формат. Пример: 2025-07-07 14:00 Встреча")

async def send_reminder(text):
    await bot.send_message(chat_id=OWNER_ID, text=f"🔔 Напоминание: {text}")

async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
