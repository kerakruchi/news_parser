"""
Простой анализ текста предвыборной программы на основе правил.
Не требует внешних API — работает локально.
"""
import re
from typing import Optional


class RuleBasedAnalyzer:
    """Анализатор на ключевых словах и шаблонах"""
    
    # Ключевые разделы хорошей программы
    GOOD_SECTIONS = [
        (r'проблем[аы]|вызов[ы]|задач[аи]', "Описание проблем округа"),
        (r'предлага[ю]|предложени[яе]|мера|инициатив', "Конкретные предложения"),
        (r'срок|этап|график|план|202[4-9]|203[0-5]', "Сроки реализации"),
        (r'бюджет|финанс|средств|источник', "Источники финансирования"),
        (r'адрес|улиц|дом|территори', "Привязка к адресам"),
        (r'ответственн|координатор|команда', "Ответственные исполнители"),
    ]
    
    # Признаки "воды" и общих фраз
    VAGUE_PHRASES = [
        r'улучшить.*жизнь',
        r'повысить.*уровень',
        r'создать.*услови',
        r'развивать.*сфер',
        r'обеспечить.*качеств',
    ]
    
    # Рекомендуемые улучшения (шаблоны)
    IMPROVEMENT_TEMPLATES = [
        ("нет сроков", "Добавьте конкретные сроки: 'до конца 2025 года', 'в два этапа'"),
        ("нет адресов", "Укажите адреса или территории: 'ул. Ленина, д. 1-15', 'микрорайон Северный'"),
        ("нет бюджета", "Добавьте оценку стоимости или источник: 'за счёт муниципального бюджета', 'грант'"),
        ("нет ответственных", "Укажите, кто реализует: 'совместно с УК', 'при участии жителей'"),
        ("общие фразы", "Замените общие формулировки на конкретные действия: не 'улучшить дороги', а 'отремонтировать 500 м асфальта по ул. Х'"),
    ]
    
    @classmethod
    def analyze(cls, text: str) -> dict:
        """Анализирует текст и возвращает структурированный результат"""
        text_lower = text.lower()
        result = {
            "strengths": [],
            "improvements": [],
            "missing": [],
            "score": 0
        }
        
        # 1. Проверяем наличие хороших разделов
        for pattern, label in cls.GOOD_SECTIONS:
            if re.search(pattern, text_lower, re.I):
                result["strengths"].append(label)
                result["score"] += 1
        
        # 2. Ищем "воду"
        vague_count = sum(1 for p in cls.VAGUE_PHRASES if re.search(p, text_lower))
        if vague_count >= 2:
            result["improvements"].append(
                "Замените общие фразы на конкретные действия с цифрами и адресами"
            )
        
        # 3. Проверяем, чего не хватает
        for pattern, label in cls.GOOD_SECTIONS[2:]:  # Сроки, бюджет, адреса, ответственные
            if not re.search(pattern, text_lower, re.I):
                key = label.lower().split()[0]
                for missing_key, suggestion in cls.IMPROVEMENT_TEMPLATES:
                    if missing_key in key or key in missing_key:
                        if suggestion not in result["improvements"]:
                            result["missing"].append(label)
                            result["improvements"].append(suggestion)
                        break
        
        # 4. Базовые проверки
        word_count = len(text.split())
        if word_count < 200:
            result["missing"].append("Достаточный объём текста")
            result["improvements"].insert(0, "Раскройте программу подробнее: добавьте детали по каждому пункту")
        
        if "дорог" in text_lower and "ремонт" not in text_lower and "асфальт" not in text_lower:
            result["improvements"].append(
                "По теме дорог: уточните тип работ (ямочный ремонт, асфальтирование, освещение)"
            )
        
        # Убираем дубли
        result["improvements"] = list(dict.fromkeys(result["improvements"]))
        result["missing"] = list(dict.fromkeys(result["missing"]))
        
        return result
