# -*- coding: utf-8 -*-
"""
Модуль утилит приложения.

Содержит функции для:
- Валидации URL
- Работы с буфером обмена
- Поиска cookies.txt
"""

import os
import socket
from typing import Optional, Tuple
from urllib.request import urlopen
from urllib.error import HTTPError, URLError, ContentTooShortError
import pyperclip

# Константа таймаута для сетевых запросов (секунды)
DEFAULT_TIMEOUT = 10


def is_valid_url(text: str) -> bool:
    """
    Проверить, является ли текст валидным URL.

    Args:
        text: Текст для проверки

    Returns:
        True если URL валиден
    """
    if not text or not isinstance(text, str):
        return False
    text = text.strip()
    if not (text.startswith('http://') or text.startswith('https://')):
        return False
    try:
        response = urlopen(text, timeout=DEFAULT_TIMEOUT)
        response.close()
        return True
    except HTTPError as err:
        return err.code < 500
    except socket.timeout:
        return False
    except (URLError, ValueError, OSError):
        return False


def get_clipboard_url() -> Optional[str]:
    """
    Получить URL из буфера обмена.
    
    Returns:
        URL если найден, иначе None
    """
    try:
        text = pyperclip.paste().strip()
        if is_valid_url(text):
            return text
    except Exception:
        pass
    return None


def validate_url_for_ui(text: str) -> Tuple[bool, str]:
    """
    Проверить URL для отображения в UI.

    Args:
        text: Текст для проверки

    Returns:
        Кортеж (валиден, сообщение)
    """
    if not text:
        return False, "Введите URL"
    text = text.strip()
    if not text.startswith(('http://', 'https://')):
        return False, "URL должен начинаться с http:// или https://"
    try:
        response = urlopen(text, timeout=DEFAULT_TIMEOUT)
        response.close()
        return True, "Ссылка доступна"
    except HTTPError as err:
        return True, f"Сервер ответил: {err.code} (yt-dlp попробует скачать)"
    except socket.timeout:
        return False, "Превышено время ожидания (таймаут)"
    except URLError as err:
        return False, f"Ошибка сети: {err.reason}"
    except ValueError:
        return False, "Неверный формат URL"


def find_cookies_txt(start_dir: str) -> Optional[str]:
    """
    Найти последний изменённый cookies.txt.
    
    Args:
        start_dir: Директория для поиска
        
    Returns:
        Путь к cookies.txt или None
    """
    cookies = [
        os.path.join(root, name)
        for root, _, files in os.walk(start_dir)
        for name in files if name.endswith("cookies.txt")
    ]
    return max(cookies, key=os.path.getmtime) if cookies else None
