"""Утилиты для работы с текстом."""
import re


def clean_text(text: str, max_length: int = None) -> str:
    """Базовая очистка текста"""
    # Убираем control-символы
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    # Нормализуем пробелы
    text = re.sub(r"\s+", " ", text)
    # Обрезаем если нужно
    if max_length and len(text) > max_length:
        text = text[:max_length].rsplit(" ", 1)[0] + "..."
    return text.strip()


def extract_urls(text: str) -> list[str]:
    """Находит все URL в тексте"""
    pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(pattern, text)
