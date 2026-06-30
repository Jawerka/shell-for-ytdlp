# -*- coding: utf-8 -*-
"""
Логика основного пайплайна загрузки (без UI).

Содержит проверки и классификацию ошибок для этапов:
validate URL → utilities → yt-dlp download.
"""

from __future__ import annotations

import os
import socket
from enum import Enum
from typing import Any, Optional, Tuple
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

from .utils import DEFAULT_TIMEOUT, is_supported_video_url

# Результат валидации URL: (ok, url_or_message, warning_message_or_empty)
ValidationResult = Tuple[bool, str, str]


class UtilitySeverity(str, Enum):
    """Критичность сбоя обновления утилиты."""

    CRITICAL = 'critical'
    NON_CRITICAL = 'non_critical'


def validate_url_for_download(url: str) -> ValidationResult:
    """
    Проверить URL перед загрузкой.

    Для известных видео-доменов сетевые ошибки и таймаут — soft fail (warning).
    Для неизвестных доменов — hard fail.

    Returns:
        (ok, url_or_error_message, warning_message)
    """
    if not url:
        return False, 'Введите URL', ''

    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        return False, 'URL должен начинаться с http:// или https://', ''

    try:
        response = urlopen(url, timeout=DEFAULT_TIMEOUT)
        response.close()
        return True, url, ''
    except HTTPError as err:
        return True, url, f'Сервер ответил кодом {err.code}'
    except socket.timeout:
        if is_supported_video_url(url):
            return True, url, 'Превышено время ожидания при проверке URL (yt-dlp попробует скачать)'
        return False, 'Превышено время ожидания (таймаут)', ''
    except URLError as err:
        if is_supported_video_url(url):
            return True, url, f'Ошибка сети при проверке URL: {err.reason} (yt-dlp попробует скачать)'
        return False, f'Ошибка сети: {err.reason}', ''
    except ValueError:
        return False, 'Неверный формат URL', ''


def ensure_download_directory(path: str) -> Tuple[bool, str]:
    """
    Убедиться, что папка загрузки существует.

    Returns:
        (ok, message)
    """
    if not path or not path.strip():
        return False, 'Путь сохранения не указан'

    path = path.strip()
    if os.path.isdir(path):
        return True, ''

    try:
        os.makedirs(path, exist_ok=True)
        return True, ''
    except PermissionError:
        return False, f'Нет доступа для создания папки: {path}'
    except OSError as e:
        return False, f'Не удалось создать папку загрузки: {e}'


def check_ytdlp_ready(config: Any) -> Tuple[bool, str]:
    """
    Проверить наличие yt-dlp.exe перед запуском загрузки.

    Args:
        config: ConfigManager или объект с методом get()

    Returns:
        (ready, message)
    """
    ytdlp_path = config.get('YTDLP_PATH', '')
    if not ytdlp_path:
        return False, 'yt-dlp не настроен. Запустите обновление утилит.'

    if os.path.exists(ytdlp_path):
        return True, ''

    return False, 'yt-dlp не найден. Проверьте подключение к интернету и повторите попытку.'


def classify_utility_update_result(
    utility_name: str,
    success: bool,
    *,
    force_critical: bool = False,
) -> UtilitySeverity:
    """
    Классифицировать результат обновления утилиты.

    yt-dlp — critical; deno, ffmpeg zip check — non_critical.
    """
    if success:
        return UtilitySeverity.NON_CRITICAL

    name = utility_name.lower()
    if force_critical or 'yt-dlp' in name:
        return UtilitySeverity.CRITICAL
    return UtilitySeverity.NON_CRITICAL


def get_ytdlp_download_url(config: Any) -> Optional[str]:
    """Получить URL для загрузки yt-dlp из конфигурации."""
    urls = config.get('URL_UTILITIES_UPDATE', [])
    for url in urls:
        if 'yt-dlp' in url.lower():
            return url
    return None
