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
import re
import socket
from typing import Optional, Tuple
from urllib.request import urlopen
from urllib.error import HTTPError, URLError
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


# Список доменов популярных видеосервисов для проверки ссылок
# Основано на https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md
SUPPORTED_VIDEO_DOMAINS = [
    'youtube.com',
    'youtu.be',
    'www.youtube.com',
    'music.youtube.com',
    'gaming.youtube.com',
    'twitter.com',
    'x.com',
    'www.twitter.com',
    'www.x.com',
    'vk.com',
    'www.vk.com',
    'm.vk.com',
    'vkvideo.ru',
    'www.vkvideo.ru',
    'vimeo.com',
    'www.vimeo.com',
    'player.vimeo.com',
    'tiktok.com',
    'www.tiktok.com',
    'vm.tiktok.com',
    'vt.tiktok.com',
    'instagram.com',
    'www.instagram.com',
    'm.instagram.com',
    'facebook.com',
    'www.facebook.com',
    'm.facebook.com',
    'fb.watch',
    'twitch.tv',
    'www.twitch.tv',
    'clips.twitch.tv',
    'reddit.com',
    'www.reddit.com',
    'old.reddit.com',
    'new.reddit.com',
    't.me',
    'www.t.me',
    'telegram.org',
    'ok.ru',
    'www.ok.ru',
    'm.ok.ru',
    'dailymotion.com',
    'www.dailymotion.com',
    'bilibili.com',
    'www.bilibili.com',
    'b23.tv',
    'soundcloud.com',
    'www.soundcloud.com',
    'bandcamp.com',
    'www.bandcamp.com',
]


def is_supported_video_url(url: str) -> bool:
    """
    Проверить, является ли URL ссылкой на поддерживаемый видеосервис.

    Выполняет быструю проверку домена без сетевого запроса.
    """
    if not url or not isinstance(url, str):
        return False

    url = url.strip().lower()

    if not (url.startswith('http://') or url.startswith('https://')):
        return False

    try:
        if '://' in url:
            url_without_protocol = url.split('://')[1]
        else:
            return False

        domain = url_without_protocol.split('/')[0].lower()
        if not domain:
            return False

        for supported_domain in SUPPORTED_VIDEO_DOMAINS:
            if domain == supported_domain or domain.endswith('.' + supported_domain):
                return True

    except (IndexError, ValueError, AttributeError):
        return False

    return False


_URL_IN_TEXT_RE = re.compile(
    r'https?://[^\s<>"\'\]\)]+',
    re.IGNORECASE,
)

_TRAILING_PUNCT = '.,;:!?\'"»«)]}'

_SMART_QUOTES = str.maketrans({
    '\u201c': '"', '\u201d': '"',
    '\u2018': "'", '\u2019': "'",
    '\ufeff': '',
})


def _normalize_clipboard_text(text: str) -> str:
    text = text.translate(_SMART_QUOTES).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in '"\'':
        text = text[1:-1].strip()
    return text


def _strip_trailing_punctuation(url: str) -> str:
    while url and url[-1] in _TRAILING_PUNCT:
        url = url[:-1]
    return url


def _ensure_scheme(url: str) -> str:
    lower = url.lower()
    if lower.startswith(('http://', 'https://')):
        return url
    for domain in SUPPORTED_VIDEO_DOMAINS:
        if lower.startswith(domain) or lower.startswith('www.' + domain):
            return 'https://' + url
    return url


def extract_video_url(text: str) -> Optional[str]:
    """
    Извлечь URL поддерживаемого видеосервиса из текста буфера обмена.

    Без сетевых запросов — только нормализация и проверка домена.
    """
    if not text or not isinstance(text, str):
        return None

    normalized = _normalize_clipboard_text(text)
    if not normalized or len(normalized) < 10:
        return None

    candidates = []

    if '://' in normalized or normalized.lower().startswith('www.'):
        candidates.append(normalized.split()[0] if ' ' in normalized and '://' not in normalized.split()[0] else normalized)

    for line in normalized.splitlines():
        line = line.strip()
        if line:
            candidates.append(line)

    for match in _URL_IN_TEXT_RE.finditer(normalized):
        candidates.append(match.group(0))

    seen = set()
    for raw in candidates:
        candidate = _strip_trailing_punctuation(raw.strip())
        candidate = _ensure_scheme(candidate)
        if candidate in seen:
            continue
        seen.add(candidate)
        if is_supported_video_url(candidate):
            return candidate

    return None


def get_clipboard_url() -> Optional[str]:
    """
    Получить URL видеосервиса из буфера обмена.

    Returns:
        URL если найден, иначе None
    """
    try:
        return extract_video_url(pyperclip.paste())
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
