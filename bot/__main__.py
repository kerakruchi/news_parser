"""
Точка входа: вебхук-сервер для Render.
Запуск: gunicorn -k uvicorn.workers.UvicornWorker bot.__main__:app
"""
import logging
import sys
from aiohttp import web

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.config import settings
from bot.handlers import setup_routers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Root router
router = Router()


# ========== Базовые хэндлеры ==========
@router.message(commands=["start"])
async def cmd_start(message):
    await message.answer(
        "🗳️ *Бот анализа предвыборной программы*\n\n"
        "📌 Отправьте текст программы — я проверю:\n"
        "• Полноту разделов (проблемы, решения, сроки)\n"
        "• Конкретику (адреса, цифры, ответственные)\n"
        "• Предложу улучшения по шаблону\n\n"
        "🔹 Также можно отправить ссылку на публичную страницу — "
        "я попробую извлечь текст для анализа.",
        parse_mode=ParseMode.MARKDOWN
    )


@router.message(commands=["help"])
async def cmd_help(message):
    await message.answer(
        "📚 *Команды:*\n"
        "/start — начать работу\n"
        "/help — эта справка",
        parse_mode=ParseMode.MARKDOWN
    )


@router.message()
async def handle_input(message):
    """Обрабатывает текст или ссылку"""
    text = message.text or ""
    
    # Если ссылка — пробуем спарсить
    if text.startswith("http"):
        await message.answer("🔄 Извлекаю текст со страницы...")
        from bot.services.fetcher import fetch_page_text
        page_text = await fetch_page_text(text)
        
        if page_text:
            await message.answer(f"📄 Найдено ~{len(page_text)} символов. Анализирую...")
            result = analyze_text(page_text)
        else:
            await message.answer("❌ Не удалось извлечь текст. Попробуйте отправить программу напрямую.")
            return
    else:
        # Прямой анализ текста
        await message.answer("🔄 Анализирую программу...")
        result = analyze_text(text)
    
    # Формируем ответ
    response = format_analysis_result(result)
    await message.answer(response, parse_mode=ParseMode.MARKDOWN)


# ========== Анализ (правиловый) ==========
def analyze_text(text: str) -> dict:
    """Простой анализ текста на основе правил"""
    from bot.services.analyzer import RuleBasedAnalyzer
    return RuleBasedAnalyzer.analyze(text)


def format_analysis_result(result: dict) -> str:
    """Форматирует результат анализа в читаемый ответ"""
    sections = []
    
    if result["strengths"]:
        sections.append("✅ *Сильные стороны:*")
        for s in result["strengths"]:
            sections.append(f"• {s}")
    
    if result["improvements"]:
        sections.append("\n💡 *Предложения по улучшению:*")
        for i, imp in enumerate(result["improvements"], 1):
            sections.append(f"{i}. {imp}")
    
    if result["missing"]:
        sections.append("\n⚠️ *Чего не хватает:*")
        for m in result["missing"]:
            sections.append(f"• {m}")
    
    sections.append("\n_Анализ выполнен по правилам. Для более глубокого анализа подключите AI-модель._")
    
    return "\n".join(sections)


# ========== Webhook setup ==========
async def on_startup(bot: Bot):
    if settings.webhook_url:
        await bot.set_webhook(
            url=settings.webhook_url,
            secret_token=settings.WEBHOOK_SECRET.get_secret_value() if settings.WEBHOOK_SECRET else None,
            drop_pending_updates=True
        )
        logger.info(f"✓ Webhook: {settings.webhook_url}")
    else:
        logger.warning("⚠ WEBHOOK_BASE_URL не задан — бот не будет получать сообщения на Render")


async def on_shutdown(bot: Bot):
    if settings.webhook_url:
        await bot.delete_webhook()
        logger.info("✓ Webhook удалён")


def create_app() -> web.Application:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    setup_routers(dp)
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    app = web.Application()
    
    # Webhook handler
    if settings.WEBHOOK_SECRET:
        secret = settings.WEBHOOK_SECRET.get_secret_value()
    else:
        secret = None
    
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=secret,
        handle_in_background=True
    )
    webhook_handler.register(app, path=settings.WEBHOOK_PATH)
    
    # Health check для Render
    async def health_handler(request):
        return web.json_response({"status": "ok", "version": "0.1.0"})
    app.router.add_get("/health", health_handler)
    
    setup_application(app, dp, bot=bot)
    
    return app


# Точка входа для gunicorn
app = create_app()
