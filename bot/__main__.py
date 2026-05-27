"""
Точка входа: вебхук-сервер для Render.
Запуск: gunicorn -k aiohttp.GunicornWebWorker bot.__main__:app --bind 0.0.0.0:$PORT
"""
import logging
import sys
from aiohttp import web

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Root router
router = Router()


# ========== Хэндлеры (исправленный синтаксис aiogram 3.x) ==========
@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🗳️ *Бот анализа предвыборной программы*\n\n"
        "📌 Отправьте текст программы — я проверю:\n"
        "• Полноту разделов (проблемы, решения, сроки)\n"
        "• Конкретику (адреса, цифры, ответственные)\n"
        "• Предложу улучшения по шаблону",
        parse_mode=ParseMode.MARKDOWN
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📚 *Команды:*\n"
        "/start — начать работу\n"
        "/help — эта справка",
        parse_mode=ParseMode.MARKDOWN
    )


@router.message(F.text)
async def handle_input(message: Message):
    """Обрабатывает текст программы"""
    text = message.text or ""
    
    # Если ссылка — пробуем спарсить (опционально)
    if text.startswith("http"):
        await message.answer("🔄 Извлекаю текст со страницы...")
        from bot.services.fetcher import fetch_page_text
        page_text = await fetch_page_text(text)
        if page_text:
            text = page_text
        else:
            await message.answer("❌ Не удалось извлечь текст. Отправьте программу напрямую.")
            return
    
    # Анализ текста
    await message.answer("🔄 Анализирую программу...")
    result = analyze_text(text)
    response = format_analysis_result(result)
    await message.answer(response, parse_mode=ParseMode.MARKDOWN)


# ========== Логика анализа (правиловый анализатор) ==========
def analyze_text(text: str) -> dict:
    """Простой анализ на основе ключевых слов"""
    import re
    text_lower = text.lower()
    
    strengths = []
    improvements = []
    missing = []
    
    # Проверка разделов
    sections = [
        (r'проблем|вызов|задач', "Описание проблем"),
        (r'предлага|предложени|мера|инициатив', "Конкретные предложения"),
        (r'срок|этап|график|202[4-9]', "Сроки реализации"),
        (r'бюджет|финанс|средств', "Финансирование"),
        (r'адрес|улиц|территори', "Привязка к адресам"),
    ]
    
    for pattern, label in sections:
        if re.search(pattern, text_lower):
            strengths.append(label)
    
    # Проверка на отсутствие важного
    if not re.search(r'срок|этап|график|202[4-9]', text_lower):
        missing.append("Сроки реализации")
        improvements.append("Добавьте сроки: 'до конца 2025', 'в два этапа'")
    
    if not re.search(r'бюджет|финанс|средств|источник', text_lower):
        missing.append("Источники финансирования")
        improvements.append("Укажите источник: 'муниципальный бюджет', 'грант'")
    
    if not re.search(r'адрес|улиц|дом|микрорайон', text_lower):
        missing.append("Привязка к адресам")
        improvements.append("Добавьте адреса: 'ул. Ленина, д. 1-15'")
    
    # Проверка на "воду"
    vague = sum(1 for p in [r'улучшить.*жизнь', r'повысить.*уровень', r'создать.*услови'] 
                if re.search(p, text_lower))
    if vague >= 2:
        improvements.append("Замените общие фразы на конкретные действия с цифрами")
    
    # Объём текста
    if len(text.split()) < 200:
        improvements.insert(0, "Раскройте программу подробнее — добавьте детали")
    
    return {
        "strengths": strengths if strengths else ["Программа структурирована"],
        "improvements": improvements if improvements else ["Программа соответствует базовым требованиям"],
        "missing": missing
    }


def format_analysis_result(result: dict) -> str:
    """Форматирует ответ пользователю"""
    parts = []
    
    if result["strengths"]:
        parts.append("✅ *Сильные стороны:*")
        parts.extend(f"• {s}" for s in result["strengths"])
    
    parts.append("\n💡 *Предложения:*")
    parts.extend(f"{i}. {imp}" for i, imp in enumerate(result["improvements"], 1))
    
    if result["missing"]:
        parts.append("\n⚠️ *Не хватает:*")
        parts.extend(f"• {m}" for m in result["missing"])
    
    return "\n".join(parts)


# ========== Webhook setup для Render ==========
async def on_startup(bot: Bot):
    if settings.webhook_url:
        await bot.set_webhook(
            url=settings.webhook_url,
            secret_token=settings.WEBHOOK_SECRET.get_secret_value() if settings.WEBHOOK_SECRET else None,
            drop_pending_updates=True
        )
        logger.info(f"✓ Webhook set: {settings.webhook_url}")


async def on_shutdown(bot: Bot):
    if settings.webhook_url:
        await bot.delete_webhook()
        logger.info("✓ Webhook deleted")


def create_app() -> web.Application:
    """Создаёт aiohttp приложение"""
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    app = web.Application()
    
    # Webhook handler
    secret = settings.WEBHOOK_SECRET.get_secret_value() if settings.WEBHOOK_SECRET else None
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=secret,
        handle_in_background=True
    )
    webhook_handler.register(app, path=settings.WEBHOOK_PATH)
    
    # Health check
    async def health_handler(request):
        return web.json_response({"status": "ok"})
    app.router.add_get("/health", health_handler)
    
    setup_application(app, dp, bot=bot)
    return app


# Точка входа для gunicorn
app = create_app()
