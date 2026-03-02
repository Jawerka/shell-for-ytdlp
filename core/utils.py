# -*- coding: utf-8 -*-
"""
Модуль утилит приложения.

Содержит функции для:
- Валидации URL
- Работы с буфером обмена
- Поиска cookies.txt
- Нормализации путей
"""

import os
import socket
from typing import Optional, Tuple
from urllib.request import urlopen
from urllib.error import HTTPError, URLError, ContentTooShortError
import pyperclip

# Константа таймаута для сетевых запросов (секунды)
DEFAULT_TIMEOUT = 10


def normalize_path_for_display(path: str) -> str:
    """
    Нормализовать путь для отображения в UI (стиль Windows).

    Преобразует все слеши к обратному виду (backslash),
    как принято в Windows.

    Args:
        path: Путь для нормализации

    Returns:
        Нормализованный путь
    """
    if not path:
        return path
    # Заменяем прямые слеши на обратные
    return path.replace('/', '\\')


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


def find_cookies_in_utilities() -> Optional[str]:
    """
    Найти cookies.txt в директории utilities.

    Returns:
        Путь к cookies.txt или None
    """
    from core.config import get_utilities_path
    utilities_dir = get_utilities_path()
    return find_cookies_txt(utilities_dir)


# Список доменов популярных видеосервисов для проверки ссылок
# Основано на https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md
SUPPORTED_VIDEO_DOMAINS = [
    # YouTube и связанные
    'youtube.com',
    'youtu.be',
    'www.youtube.com',
    'music.youtube.com',
    'gaming.youtube.com',
    # X (Twitter)
    'twitter.com',
    'x.com',
    'www.twitter.com',
    'www.x.com',
    # VK (ВКонтакте)
    'vk.com',
    'www.vk.com',
    'm.vk.com',
    'vkvideo.ru',
    'www.vkvideo.ru',
    # Vimeo
    'vimeo.com',
    'www.vimeo.com',
    'player.vimeo.com',
    # TikTok
    'tiktok.com',
    'www.tiktok.com',
    'vm.tiktok.com',
    'vt.tiktok.com',
    # Instagram
    'instagram.com',
    'www.instagram.com',
    'm.instagram.com',
    # Facebook
    'facebook.com',
    'www.facebook.com',
    'm.facebook.com',
    'fb.watch',
    # Twitch
    'twitch.tv',
    'www.twitch.tv',
    'clips.twitch.tv',
    # Reddit
    'reddit.com',
    'www.reddit.com',
    'old.reddit.com',
    'new.reddit.com',
    # Telegram
    't.me',
    'www.t.me',
    'telegram.org',
    # Одноклассники
    'ok.ru',
    'www.ok.ru',
    'm.ok.ru',
    # Dailymotion
    'dailymotion.com',
    'www.dailymotion.com',
    # Bilibili
    'bilibili.com',
    'www.bilibili.com',
    'b23.tv',
    # SoundCloud
    'soundcloud.com',
    'www.soundcloud.com',
    # Bandcamp
    'bandcamp.com',
    'www.bandcamp.com',
]


def is_supported_video_url(url: str) -> bool:
    """
    Проверить, является ли URL ссылкой на поддерживаемый видеосервис.

    Выполняет быструю проверку домена без сетевого запроса.
    Список основан на поддерживаемых сайтах yt-dlp.

    Args:
        url: URL для проверки

    Returns:
        True если домен входит в список популярных видеосервисов
    """
    if not url or not isinstance(url, str):
        return False

    url = url.strip().lower()

    # Быстрая отсечка: URL должен начинаться с http:// или https://
    if not (url.startswith('http://') or url.startswith('https://')):
        return False

    # Извлекаем домен из URL
    try:
        # Убираем протокол
        if '://' in url:
            url_without_protocol = url.split('://')[1]
        else:
            return False  # Нет протокола - не URL

        # Получаем домен (часть до первого /)
        domain = url_without_protocol.split('/')[0].lower()

        # Проверка: домен не должен быть пустым
        if not domain:
            return False

        # Проверяем наличие домена в списке поддерживаемых
        for supported_domain in SUPPORTED_VIDEO_DOMAINS:
            if domain == supported_domain or domain.endswith('.' + supported_domain):
                return True

    except (IndexError, ValueError, AttributeError):
        return False

    return False
