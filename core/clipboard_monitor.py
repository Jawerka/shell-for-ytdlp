# -*- coding: utf-8 -*-
"""
Модуль мониторинга буфера обмена.

Содержит класс ClipboardMonitor для периодической проверки
буфера обмена на появление ссылок на поддерживаемые видеосервисы.
"""

import threading
import time
import logging
from typing import Callable, Optional

import pyperclip

from core.utils import is_supported_video_url

logger = logging.getLogger('UI-for-ytdlp.clipboard_monitor')


class ClipboardMonitor:
    """
    Монитор буфера обмена для автоматического обнаружения ссылок на видео.

    Периодически проверяет буфер обмена на появление новых URL
    из списка поддерживаемых видеосервисов (YouTube, X, VK и др.).

    Attributes:
        check_interval: Интервал проверки буфера обмена в секундах
        on_url_detected: Callback функция, вызываемая при обнаружении URL
    """

    def __init__(
        self,
        check_interval: float = 2.0,
        on_url_detected: Optional[Callable[[str], None]] = None
    ):
        """
        Инициализировать монитор буфера обмена.

        Args:
            check_interval: Интервал проверки в секундах (по умолчанию 2.0)
            on_url_detected: Callback для обработки обнаруженного URL
        """
        self.check_interval = check_interval
        self.on_url_detected = on_url_detected

        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._last_clipboard_content: Optional[str] = None
        self._stop_event = threading.Event()
        self._is_paused = False

    def start(self) -> None:
        """
        Запустить мониторинг буфера обмена.

        Запускает фоновый поток для периодической проверки буфера.
        Если мониторинг уже запущен, метод ничего не делает.
        """
        if self._is_running:
            logger.debug("ClipboardMonitor уже запущен")
            return

        self._is_running = True
        self._is_paused = False
        self._stop_event.clear()
        self._last_clipboard_content = None

        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ClipboardMonitor"
        )
        self._thread.start()

        logger.info(f"ClipboardMonitor запущен (интервал: {self.check_interval}s)")

    def stop(self) -> None:
        """
        Остановить мониторинг буфера обмена.

        Сигнализирует фоновому потоку о остановке и ожидает его завершения.
        """
        if not self._is_running:
            logger.debug("ClipboardMonitor уже остановлен")
            return

        self._is_running = False
        self._is_paused = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        self._thread = None
        self._last_clipboard_content = None

        logger.info("ClipboardMonitor остановлен")

    def pause(self) -> None:
        """
        Приостановить мониторинг буфера обмена.

        Мониторинг не останавливается полностью, но проверка URL прекращается.
        """
        self._is_paused = True
        logger.debug("ClipboardMonitor приостановлен")

    def resume(self) -> None:
        """
        Возобновить мониторинг буфера обмена.

        Снимает паузу с мониторинга.
        """
        self._is_paused = False
        logger.debug("ClipboardMonitor возобновлен")

    def is_running(self) -> bool:
        """
        Проверить, запущен ли мониторинг.

        Returns:
            True если мониторинг активен
        """
        return self._is_running

    def is_paused(self) -> bool:
        """
        Проверить, находится ли мониторинг на паузе.

        Returns:
            True если мониторинг на паузе
        """
        return self._is_paused

    def _monitor_loop(self) -> None:
        """
        Основной цикл мониторинга буфера обмена.

        Выполняется в фоновом потоке до получения сигнала остановки.
        """
        logger.debug("ClipboardMonitor: начало цикла мониторинга")

        while self._is_running and not self._stop_event.is_set():
            try:
                if not self._is_paused:
                    self._check_clipboard()
            except Exception as e:
                logger.error(f"ClipboardMonitor: ошибка проверки буфера: {e}", exc_info=True)

            # Ждём следующий интервал или сигнал остановки
            self._stop_event.wait(self.check_interval)

        logger.debug("ClipboardMonitor: цикл мониторинга завершён")

    def _check_clipboard(self) -> None:
        """
        Проверить буфер обмена на наличие нового URL.

        Сравнивает текущее содержимое буфера с предыдущим.
        Если найден новый URL поддерживаемого сервиса - вызывает callback.
        """
        try:
            current_content = pyperclip.paste()
        except Exception as e:
            logger.warning(f"ClipboardMonitor: не удалось прочитать буфер: {e}")
            return

        # Пропускаем если содержимое не изменилось
        if current_content == self._last_clipboard_content:
            return

        self._last_clipboard_content = current_content

        # Пропускаем пустое содержимое
        if not current_content or not isinstance(current_content, str):
            return

        text = current_content.strip()

        # Проверяем является ли текст поддерживаемым URL
        if is_supported_video_url(text):
            logger.info(f"ClipboardMonitor: обнаружен URL: {text[:100]}")

            if self.on_url_detected:
                try:
                    self.on_url_detected(text)
                except Exception as e:
                    logger.error(f"ClipboardMonitor: ошибка callback: {e}", exc_info=True)
        else:
            # Логируем только для отладки, чтобы не спамить
            logger.debug(f"ClipboardMonitor: содержимое не является поддерживаемым URL: {text[:50]}...")
