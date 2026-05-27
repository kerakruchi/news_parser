"""
Простой парсер публичных веб-страниц без авторизации.
Работает с requests + BeautifulSoup.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


# Селекторы для известных источников (можно расширять)
SELECTORS = {
    "altgazeta.ru": {
        "container": "article, .article-content, .post-content",
        "exclude": "script, style, nav, footer, header, .comments, .sidebar"
    },
    "listmax.ru": {
        "container": ".channel-post, .post, article",
        "exclude": "script, style, .nav, .footer"
    },
    "vk.com": {
        "container": "#wall_posts, .wall_post_text",  # Работает не всегда, т.к. ВК динамический
        "exclude": "script, style"
    },
    # Дефолтный селектор
    "default": {
        "container": "article, main, .content, .post, [role='main']",
        "exclude": "script, style, nav, footer, header, aside, .sidebar, .comments"
    }
}


async def fetch_page_text(url: str, max_length: int = 4000) -> str | None:
    """
    Скачивает и извлекает основной текст со страницы.
    Возвращает очищенный текст или None при ошибке.
    """
    try:
        # Определяем домен для выбора селекторов
        domain = urlparse(url).netloc
        selectors = SELECTORS.get(domain, SELECTORS["default"])
        
        headers = {
            "User-Agent": "Mozilla/5.0 ElectionBot/1.0 (+https://example.com)"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "lxml")
        
        # Удаляем ненужные элементы
        for tag in soup.select(selectors["exclude"]):
            tag.decompose()
        
        # Ищем основной контент
        containers = soup.select(selectors["container"])
        if not containers:
            # fallback: берём body
            containers = [soup.body] if soup.body else [soup]
        
        # Извлекаем текст
        texts = []
        for container in containers:
            text = container.get_text(separator="\n", strip=True)
            if text:
                texts.append(text)
        
        full_text = "\n\n".join(texts)
        
        # Очистка: убираем лишние пробелы, символы
        full_text = " ".join(full_text.split())
        
        return full_text[:max_length] if len(full_text) > max_length else full_text
        
    except requests.RequestException as e:
        logger.error(f"Fetch error {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Parse error {url}: {e}")
        return None
