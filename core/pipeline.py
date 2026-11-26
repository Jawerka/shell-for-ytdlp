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
import time
import re
from urllib.request import urlopen
from urllib.error import HTTPError
from enum import Enum
from typing import Any, Optional, Tuple

from .utils import validate_http_url

logger = logging.getLogger('UI-for-ytdlp.pipeline')

SPONSORBLOCK_FAILURE_POLICIES = {
    'ask': 'Спрашивать',
    'bypass': 'Скачивать без вырезания',
    'stop': 'Останавливать загрузку',
}


def is_sponsorblock_network_error(line: str, fetching: bool = False) -> bool:
    """Сбой API (сеть/неверный JSON), но не скачивания или вырезания ffmpeg."""
    text = line.lower()
    if fetching and text.startswith(('json.decoder.jsondecodeerror:', 'jsondecodeerror:')):
        return True
    if not (text.startswith(('error:', 'warning:'))
            or re.search(r'\]\s*(?:error|warning):', text)):
        return False
    source = 'sponsor.ajay.app' in text or 'sponsorblock api' in text
    if not source and ('ffmpeg' in text or 'video data' in text or '[youtube]' in text):
        return False
    network = any(token in text for token in (
        'timed out', 'timeout', 'connection', 'unable to communicate',
        'unable to download', 'http error 5', 'http error 429',
        'certificate_verify_failed', 'name resolution',
    ))
    return network and (source or (fetching and text.startswith('error:')
                                  and not re.search(r'https?://|host=', text)))


class SponsorBlockAvailability:
    """Состояние сервиса на время работы приложения; выбор хранится отдельно."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.unavailable = False
        self.failures = 0
        self.next_probe = 0.0

    def failed(self):
        self.unavailable = True
        self.failures += 1
        self.next_probe = self.clock() + (30, 120, 300)[min(self.failures - 1, 2)]

    def recovered(self):
        self.unavailable = False
        self.failures = 0
        self.next_probe = 0.0

    def probe(self, force=False):
        """None: ещё рано; bool: ответ API. Вызывать только в рабочем потоке."""
        if not force and self.clock() < self.next_probe:
            return None
        try:
            with urlopen('https://sponsor.ajay.app/api/skipSegments/0000', timeout=3) as response:
                import json
                healthy = isinstance(json.loads(response.read(1024 * 1024)), list)
        except HTTPError as exc:
            # API возвращает 404, если для префикса нет отметок.
            healthy = exc.code == 404
            exc.close()
        except Exception:
            healthy = False
        if healthy:
            self.recovered()
        else:
            self.failed()
        return healthy

# Папка для .part и прочих промежуточных файлов yt-dlp (рядом с DOWNLOAD_PATH).
DOWNLOAD_TEMP_DIR_NAME = '_UI-for-ytdlp-temp'

# Пресеты качества: верхняя граница высоты кадра для yt-dlp -f.
VIDEO_QUALITY_MAX = 'max'
VIDEO_QUALITY_DEFAULT = VIDEO_QUALITY_MAX
YTDLP_FORMAT_BEST = 'bestvideo+bestaudio/best'
_VIDEO_QUALITY_HEIGHTS = ('1080', '720', '480')
VIDEO_QUALITY_CHOICES = (
    ('480', '480p'),
    ('720', '720p'),
    ('1080', '1080p'),
    (VIDEO_QUALITY_MAX, 'Максимально доступный'),
)

OUTPUT_CONTAINER_DEFAULT = 'auto'
OUTPUT_CONTAINER_CHOICES = (
    ('auto', 'Авто'),
    ('mp4', 'MP4 — совместимость'),
    ('webm', 'WebM'),
    ('mkv', 'MKV — лучшее качество'),
)
OUTPUT_CONTAINER_DESCRIPTIONS = {
    'auto': 'Лучшие доступные дорожки. Контейнер выбирает yt-dlp.',
    'mp4': 'H.264 + AAC для широкой совместимости. Разрешение может быть ниже максимального.',
    'webm': 'VP9/AV1/VP8 + Opus/Vorbis. Эти дорожки доступны не на всех сайтах.',
    'mkv': 'Лучшие доступные дорожки, включая современные кодеки. Для просмотра подойдёт VLC.',
}


def normalize_output_container(value: Any) -> str:
    """Неизвестное или повреждённое значение настройки → авто."""
    value = value.strip().lower() if isinstance(value, str) else ''
    return value if value in OUTPUT_CONTAINER_DESCRIPTIONS else OUTPUT_CONTAINER_DEFAULT


def ytdlp_format_selector_for_container(
    quality: str, container: str, source_selector: Optional[str] = None,
) -> str:
    """Выбрать совместимые дорожки без перекодирования и скрытого отката кодеков.

    Идентификатор потока от обработчика сохраняется; для MP4/WebM он также
    проверяется по кодекам. Неизвестные кодеки не дают обещать совместимость.
    """
    container = normalize_output_container(container)
    if container not in ('mp4', 'webm'):
        return source_selector or ytdlp_format_selector_for_quality(quality)

    if container == 'mp4':
        video = "[vcodec~='^(avc|h264)']"
        audio = "[acodec~='^(mp4a|aac)']"
    else:
        video = "[vcodec~='^(vp8|vp9|vp08|vp09|av01|av1)']"
        audio = "[acodec~='^(opus|vorbis)']"
    if source_selector:
        return f'({source_selector}){video}{audio}'
    value = quality.strip().lower() if isinstance(quality, str) else ''
    height = f'[height<={value}]' if value in _VIDEO_QUALITY_HEIGHTS else ''
    return f'bestvideo{height}{video}+bestaudio{audio}/best{height}{video}{audio}'


def ytdlp_container_options(container: str) -> list[str]:
    """Контейнер и remux для отдельных дорожек и уже готового файла."""
    container = normalize_output_container(container)
    if container == 'auto':
        return []
    options = ['--merge-output-format', container, '--remux-video', container]
    if container == 'mp4':
        # Только MP4: не передавать movflags процессорам WebM/MKV.
        options += [
            '--postprocessor-args', 'Merger+ffmpeg_o:-movflags +faststart',
            '--postprocessor-args', 'VideoRemuxer+ffmpeg_o:-movflags +faststart',
        ]
    return options


def ytdlp_format_selector_for_quality(quality: str) -> str:
    """Вернуть строку -f для пресета VIDEO_QUALITY (неизвестный ключ → максимум)."""
    value = quality.strip().lower() if isinstance(quality, str) else ''
    if value in _VIDEO_QUALITY_HEIGHTS:
        return (
            f'bestvideo[height<={value}]+bestaudio/'
            f'best[height<={value}]'
        )
    return YTDLP_FORMAT_BEST

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
