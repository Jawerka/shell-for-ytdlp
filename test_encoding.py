# -*- coding: utf-8 -*-
"""
Тест кодировок для логгера.
"""

import sys
import os

# Добавляем корень проекта
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.logger import GUILogger

# Тестовый текст на русском
test_texts = [
    "Привет мир! Это тестовое сообщение.",
    "Загрузка файла: тест_видео.mp4",
    "Путь: D:\\Documents\\Projects\\python\\UI-for-ytdlp",
    "Ошибка: Файл не найден",
]

def print_colored(text, color_code=0):
    """Вывод текста с цветом."""
    print(f"\033[{color_code}m{text}\033[0m")

def test_logger():
    """Тестирование логгера с разными кодировками."""
    print("=" * 60)
    print("ТЕСТ ЛОГГЕРА С РАЗНЫМИ КОДИРОВКАМИ")
    print("=" * 60)
    
    # Создаём логгер
    logger = GUILogger()
    
    print("\n1. Тестовые сообщения (оригинальный UTF-8):")
    print("-" * 60)
    for text in test_texts:
        print(f"  {text}")
        logger.info(text)
    
    print("\n2. Сообщения из логов (как они хранятся):")
    print("-" * 60)
    for formatted, level in logger.get_logs():
        print(f"  [{level.value}] {formatted}")
    
    print("\n3. Тест с явной кодировкой cp866 (консоль Windows):")
    print("-" * 60)
    for text in test_texts:
        try:
            # Конвертация в cp866 и обратно
            cp866_text = text.encode('cp866', errors='replace').decode('cp866')
            print(f"  cp866: {cp866_text}")
        except Exception as e:
            print(f"  Ошибка cp866: {e}")
    
    print("\n4. Тест с кодировкой utf-8 (как в downloader.py):")
    print("-" * 60)
    for text in test_texts:
        try:
            # Двойная конвертация (как сейчас в коде)
            utf8_text = text.encode('utf-8', errors='replace').decode('utf-8')
            print(f"  utf-8: {utf8_text}")
        except Exception as e:
            print(f"  Ошибка utf-8: {e}")
    
    print("\n5. Тест с кодировкой OEM (консоль Windows):")
    print("-" * 60)
    import locale
    oem_encoding = locale.getpreferredencoding()
    print(f"  OEM кодировка системы: {oem_encoding}")
    for text in test_texts:
        try:
            oem_text = text.encode(oem_encoding, errors='replace').decode(oem_encoding)
            print(f"  {oem_encoding}: {oem_text}")
        except Exception as e:
            print(f"  Ошибка {oem_encoding}: {e}")
    
    print("\n6. Проверка кодировки stdout:")
    print("-" * 60)
    print(f"  sys.stdout.encoding: {sys.stdout.encoding}")
    print(f"  sys.stdin.encoding: {sys.stdin.encoding}")
    print(f"  sys.getdefaultencoding(): {sys.getdefaultencoding()}")
    
    print("\n" + "=" * 60)
    print("ТЕСТ ЗАВЕРШЁН")
    print("=" * 60)

if __name__ == '__main__':
    test_logger()
