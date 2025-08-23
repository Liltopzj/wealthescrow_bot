# connect_bot.py
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv

# Load .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Initialize bot & dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("🤖 Bot is online! Send /ping to test.")

@dp.message(Command("ping"))
async def ping_cmd(message: types.Message):
    await message.answer("🏓 Pong! The bot is connected.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
