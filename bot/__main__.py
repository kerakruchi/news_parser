import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from bot.config import Settings

settings = Settings()
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🗳️ Бот анализа предвыборной программы\n"
        "Отправьте текст программы или ссылку на источник — "
        "я предложу улучшения на основе анализа данных."
    )

@dp.message()
async def handle_text(message: Message):
    # Здесь будет логика анализа
    await message.answer("🔄 Анализирую... (в разработке)")

async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
