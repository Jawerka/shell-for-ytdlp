# -*- coding: utf-8 -*-
"""
Логика основного пайплайна загрузки (без UI).

Содержит проверки и классификацию ошибок для этапов:
validate URL → utilities → yt-dlp download.
"""

from __future__ import annotations

import logging
import os
import shutil
from enum import Enum
from typing import Any, Optional, Tuple

from .utils import validate_http_url

logger = logging.getLogger('UI-for-ytdlp.pipeline')

# Папка для .part и прочих промежуточных файлов yt-dlp (рядом с DOWNLOAD_PATH).
DOWNLOAD_TEMP_DIR_NAME = '_UI-for-ytdlp-temp'

# Результат валидации URL: (ok, url_or_message, warning_message_or_empty)
ValidationResult = Tuple[bool, str, str]


class UtilitySeverity(str, Enum):
    """Критичность сбоя обновления утилиты."""

    CRITICAL = 'critical'
    NON_CRITICAL = 'non_critical'


def validate_url_for_download(url: str) -> ValidationResult:
    """
    Проверить URL перед загрузкой (без сетевого запроса).

    Доступность проверяет yt-dlp во время загрузки; синхронный urlopen
    блокировал бы поток Tk до 10 секунд.

    Returns:
        (ok, url_or_error_message, warning_message)
    """
    if not url:
        return False, 'Введите URL', ''

    url = url.strip()
    error = validate_http_url(url)
    if error:
        return False, error, ''

    return True, url, ''


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


def get_download_temp_dir(download_path: str) -> str:
    """Путь к папке временных файлов загрузки рядом с каталогом сохранения."""
    return os.path.join(os.path.abspath(download_path.strip()), DOWNLOAD_TEMP_DIR_NAME)


def ensure_download_temp_directory(download_path: str) -> Tuple[bool, str]:
    """Создать папку для .part и фрагментов HLS, если её ещё нет."""
    return ensure_download_directory(get_download_temp_dir(download_path))


def cleanup_download_temp_directory(download_path: str) -> None:
    """
    Удалить папку временных файлов после успешной сборки видео.

    При ошибке или отмене папку не трогаем — там остаются .part для --continue.
    """
    temp_dir = get_download_temp_dir(download_path)
    if not os.path.isdir(temp_dir):
        return
    try:
        shutil.rmtree(temp_dir)
        logger.debug("cleanup_download_temp_directory: удалена %s", temp_dir)
    except OSError as e:
        logger.warning("cleanup_download_temp_directory: не удалось удалить %s: %s", temp_dir, e)


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
