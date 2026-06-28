# -*- coding: utf-8 -*-
"""
Модуль мониторинга буфера обмена.

Polling выполняется в главном потоке Tk через root.after() для надёжного
чтения буфера на Windows.
"""

import logging
import time
from typing import Callable, Optional, Any

import pyperclip

from core.utils import extract_video_url

logger = logging.getLogger('UI-for-ytdlp.clipboard_monitor')

_CLIPBOARD_READ_RETRIES = 3
_CLIPBOARD_READ_RETRY_DELAY = 0.05


class ClipboardMonitor:
    """
    Монитор буфера обмена для автоматического обнаружения ссылок на видео.

    Периодически проверяет буфер обмена на появление новых URL
    из списка поддерживаемых видеосервисов (YouTube, X, VK и др.).
    """

    def __init__(
        self,
        check_interval: float = 2.0,
        on_url_detected: Optional[Callable[[str], None]] = None,
        root_window: Any = None,
    ):
        self.check_interval = check_interval
        self.on_url_detected = on_url_detected
        self.root_window = root_window

        self._is_running = False
        self._is_paused = False
        self._last_clipboard_content: Optional[str] = None
        self._poll_after_id: Optional[str] = None

    def start(self) -> None:
        """Запустить мониторинг буфера обмена через root.after()."""
        if self._is_running:
            logger.debug("ClipboardMonitor уже запущен")
            return

        if not self.root_window:
            logger.error("ClipboardMonitor: root_window обязателен для start()")
            return

        self._is_running = True
        self._is_paused = False
        self._last_clipboard_content = None
        self._schedule_poll(0)
        logger.info(f"ClipboardMonitor запущен (интервал: {self.check_interval}s)")

    def stop(self) -> None:
        """Остановить мониторинг и отменить запланированный poll."""
        if not self._is_running:
            logger.debug("ClipboardMonitor уже остановлен")
            return

        self._is_running = False
        self._is_paused = False
        self._cancel_poll()
        self._last_clipboard_content = None
        logger.info("ClipboardMonitor остановлен")

    def pause(self) -> None:
        """Приостановить проверку URL (poll продолжается)."""
        self._is_paused = True
        logger.debug("ClipboardMonitor приостановлен")

    def resume(self) -> None:
        """Возобновить проверку и немедленно прочитать буфер."""
        self._is_paused = False
        logger.debug("ClipboardMonitor возобновлен")
        if self._is_running:
            self._check_clipboard()

    def is_running(self) -> bool:
        return self._is_running

    def is_paused(self) -> bool:
        return self._is_paused

    def _cancel_poll(self) -> None:
        if self._poll_after_id is not None and self.root_window:
            try:
                self.root_window.after_cancel(self._poll_after_id)
            except Exception:
                pass
            self._poll_after_id = None

    def _schedule_poll(self, delay_ms: int) -> None:
        if not self._is_running or not self.root_window:
            return
        self._poll_after_id = self.root_window.after(
            delay_ms,
            self._poll_and_reschedule,
        )

    def _poll_and_reschedule(self) -> None:
        self._poll_after_id = None
        if not self._is_running:
            return

        try:
            if not self._is_paused:
                self._check_clipboard()
        except Exception as e:
            logger.error(f"ClipboardMonitor: ошибка проверки буфера: {e}", exc_info=True)

        if self._is_running:
            self._schedule_poll(int(self.check_interval * 1000))

    def _read_clipboard(self) -> Optional[str]:
        last_error = None
        for attempt in range(_CLIPBOARD_READ_RETRIES):
            try:
                return pyperclip.paste()
            except Exception as e:
                last_error = e
                if attempt + 1 < _CLIPBOARD_READ_RETRIES:
                    time.sleep(_CLIPBOARD_READ_RETRY_DELAY)
        if last_error:
            logger.warning(f"ClipboardMonitor: не удалось прочитать буфер: {last_error}")
        return None

    def _check_clipboard(self) -> None:
        current_content = self._read_clipboard()
        if current_content is None:
            return

        if current_content == self._last_clipboard_content:
            return

        self._last_clipboard_content = current_content

        if not current_content or not isinstance(current_content, str):
            return

        try:
            url = extract_video_url(current_content)
            if url:
                logger.info(f"ClipboardMonitor: обнаружен URL: {url[:100]}")
                if self.on_url_detected:
                    try:
                        self.on_url_detected(url)
                    except Exception as e:
                        logger.error(f"ClipboardMonitor: ошибка callback: {e}", exc_info=True)
            else:
                logger.debug(
                    "ClipboardMonitor: содержимое не содержит поддерживаемый URL: "
                    f"{current_content[:50]}..."
                )
        except Exception as e:
            logger.error(f"ClipboardMonitor: ошибка проверки URL: {e}", exc_info=True)
