# -*- coding: utf-8 -*-
"""
Подключаемые обработчики URL перед загрузкой через yt-dlp.

Каждый плагин реализует DownloadHandler и регистрируется в PLUGIN_REGISTRY.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, List, Optional, Protocol, Type

logger = logging.getLogger('UI-for-ytdlp.download_handlers')


class HandlerError(Exception):
    """Ошибка подготовки URL обработчиком."""


@dataclass
class DownloadHints:
    """Параметры загрузки, подготовленные обработчиком."""

    url: str
    format_selector: Optional[str] = None
    referer: Optional[str] = None
    merge_output_format: Optional[str] = None
    output_template: Optional[str] = None
    log_title: str = ''


class DownloadHandler(Protocol):
    """Протокол подключаемого обработчика URL."""

    def is_enabled(self, config: Any) -> bool:
        """Проверить, включён ли обработчик в конфигурации."""
        ...

    def can_handle(self, url: str) -> bool:
        """Проверить, может ли обработчик обработать URL."""
        ...

    def prepare(self, url: str) -> DownloadHints:
        """Подготовить параметры загрузки для URL."""
        ...

    def extra_domains(self) -> List[str]:
        """Дополнительные домены для is_supported_video_url."""
        ...


def _get_plugin_registry() -> List[Type[DownloadHandler]]:
    """Ленивая загрузка реестра плагинов (избегаем циклических импортов)."""
    from .plugins.goodgame_vod import GoodGameVodHandler

    return [
        GoodGameVodHandler,
    ]


def resolve_download_hints(url: str, config: Any) -> DownloadHints:
    """
    Найти подходящий обработчик и подготовить параметры загрузки.

    Raises:
        HandlerError: если обработчик не смог подготовить URL
    """
    for HandlerCls in _get_plugin_registry():
        handler = HandlerCls()
        if not handler.is_enabled(config):
            continue
        if handler.can_handle(url):
            try:
                hints = handler.prepare(url)
                logger.debug(
                    "resolve_download_hints: %s обработал URL -> %s",
                    HandlerCls.__name__,
                    hints.url[:80],
                )
                return hints
            except Exception as e:
                if isinstance(e, HandlerError):
                    raise
                raise HandlerError(str(e)) from e

    return DownloadHints(url=url)


def get_plugin_domains(config: Any) -> List[str]:
    """Собрать дополнительные домены от включённых плагинов."""
    domains: List[str] = []
    for HandlerCls in _get_plugin_registry():
        handler = HandlerCls()
        if handler.is_enabled(config):
            domains.extend(handler.extra_domains())
    return domains


def can_handle_by_plugins(url: str) -> bool:
    """Проверить, распознаёт ли какой-либо плагин URL (без учёта config)."""
    for HandlerCls in _get_plugin_registry():
        handler = HandlerCls()
        if handler.can_handle(url):
            return True
    return False
