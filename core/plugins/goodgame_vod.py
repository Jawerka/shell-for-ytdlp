# -*- coding: utf-8 -*-
"""
Плагин загрузки VOD с GoodGame.ru.

yt-dlp не понимает URL вида /vods/{streamId}/{moddate} — резолвим через API
и передаём m3u8 в yt-dlp с особыми флагами.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode
from urllib.request import Request, urlopen

from ..download_handlers import DownloadHints, HandlerError
from ..utils import DEFAULT_TIMEOUT

logger = logging.getLogger('UI-for-ytdlp.plugins.goodgame_vod')

PLUGIN_ID = 'goodgame_vod'
CONFIG_KEY = 'ENABLE_GOODGAME_VOD_HANDLER'
DEFAULT_ENABLED = True

GOODGAME_REFERER = 'https://goodgame.ru/'
RECORDS_API = 'https://goodgame.ru/api/4/records/video'

_VOD_URL_RE = re.compile(
    r'(?:https?://)?(?:www\.)?goodgame\.ru/vods/([^/]+)/([^/?#]+)',
    re.IGNORECASE,
)

_FILENAME_UNSAFE_RE = re.compile(r'[\\/:*?"<>|]')


class GoodGameError(HandlerError):
    """Ошибка резолвинга GoodGame VOD."""


def is_goodgame_vod_url(url: str) -> bool:
    """Проверить, является ли URL записью GoodGame VOD."""
    return _VOD_URL_RE.search(url.strip()) is not None


def parse_goodgame_vod_url(url: str) -> Optional[Tuple[str, str]]:
    """
    Извлечь stream_id и moddate из URL VOD.

    Returns:
        (stream_id, moddate) или None
    """
    match = _VOD_URL_RE.search(url.strip())
    if not match:
        return None
    stream_id = unquote(match.group(1))
    moddate = unquote(match.group(2))
    return stream_id, moddate


def _sanitize_filename(title: str) -> str:
    return _FILENAME_UNSAFE_RE.sub('_', title).strip() or 'goodgame_vod'


def _fetch_vods(stream_id: str) -> list:
    """Запросить список записей канала через API v4."""
    query = urlencode({'streamId': stream_id})
    api_url = f'{RECORDS_API}?{query}'
    request = Request(api_url, headers={'Referer': GOODGAME_REFERER})

    try:
        with urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
            data = json.loads(response.read().decode('utf-8'))
    except HTTPError as e:
        raise GoodGameError(f'Ошибка API GoodGame: HTTP {e.code}') from e
    except URLError as e:
        raise GoodGameError(f'Ошибка сети при запросе GoodGame: {e.reason}') from e
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise GoodGameError('Некорректный ответ API GoodGame') from e
    except OSError as e:
        raise GoodGameError(f'Ошибка при запросе GoodGame: {e}') from e

    vods = data.get('vods')
    if not isinstance(vods, list):
        raise GoodGameError('Некорректный ответ API GoodGame: нет списка vods')

    return vods


def resolve_goodgame_vod(url: str) -> Tuple[str, str, str]:
    """
    Резолвить VOD URL в (media_url, title, moddate).

    Raises:
        GoodGameError
    """
    parsed = parse_goodgame_vod_url(url)
    if not parsed:
        raise GoodGameError('Неверный URL записи GoodGame')

    stream_id, moddate = parsed
    vods = _fetch_vods(stream_id)

    vod = next((v for v in vods if v.get('moddate') == moddate), None)
    if vod is None:
        raise GoodGameError('Запись GoodGame не найдена')

    title = vod.get('title') or 'goodgame_vod'
    media_url = vod.get('m3u8path') or ''
    if not media_url:
        media_url = vod.get('mp4path') or ''
        if media_url:
            logger.warning(
                'resolve_goodgame_vod: m3u8path отсутствует, используем mp4path'
            )
    if not media_url:
        raise GoodGameError('В записи GoodGame нет ссылки на видео')

    return media_url, title, moddate


class GoodGameVodHandler:
    """Обработчик VOD-записей GoodGame.ru."""

    def is_enabled(self, config: Any) -> bool:
        return bool(config.get(CONFIG_KEY, DEFAULT_ENABLED))

    def can_handle(self, url: str) -> bool:
        return is_goodgame_vod_url(url)

    def prepare(self, url: str) -> DownloadHints:
        media_url, title, moddate = resolve_goodgame_vod(url)
        safe_title = _sanitize_filename(title)

        return DownloadHints(
            url=media_url,
            format_selector='0',
            referer=GOODGAME_REFERER,
            merge_output_format='mp4',
            output_template=f'{safe_title}_{moddate}.%(ext)s',
            log_title=title,
        )

    def extra_domains(self) -> List[str]:
        return ['goodgame.ru', 'www.goodgame.ru']
