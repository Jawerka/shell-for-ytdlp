# -*- coding: utf-8 -*-
"""
Менеджер звуковых эффектов.

Отвечает за воспроизведение звуковых уведомлений при событиях приложения.
"""

import os
import sys
import threading
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger('UI-for-ytdlp.sound_manager')


class SoundManager:
    """
    Менеджер звуковых эффектов приложения.

    Воспроизводит звуковые уведомления для различных событий:
    - Начало загрузки
    - Завершение загрузки
    - Ошибка загрузки

    Использует pygame.mixer для воспроизведения WAV-файлов.
    """

    # Пути к звуковым файлам (относительно корня проекта)
    SOUND_START_DOWNLOAD = 'ui/sfx/start-dl.wav'
    SOUND_END_DOWNLOAD = 'ui/sfx/end-dl.wav'
    SOUND_ERROR_DOWNLOAD = 'ui/sfx/error-dl.wav'  # Зарезервировано на будущее

    def __init__(self, enabled: bool = True):
        """
        Инициализировать менеджер звуковых эффектов.

        Args:
            enabled: Включены ли звуковые эффекты (по умолчанию True)
        """
        self.enabled = enabled
        self._pygame_initialized = False
        self._lock = threading.Lock()

        # Получить путь к корню проекта
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller: файлы извлечены во временную папку
            self._project_root = sys._MEIPASS
        else:
            # Разработка: корень проекта
            self._project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        logger.debug(f"SoundManager инициализирован (enabled={enabled}, root={self._project_root})")

    def _get_sound_path(self, relative_path: str) -> Optional[str]:
        """
        Получить полный путь к звуковому файлу.

        Args:
            relative_path: Относительный путь к файлу

        Returns:
            Полный путь или None если файл не найден
        """
        full_path = os.path.join(self._project_root, relative_path)

        if os.path.exists(full_path):
            logger.debug(f"Звуковой файл найден: {full_path}")
            return full_path
        else:
            logger.warning(f"Звуковой файл не найден: {full_path}")
            return None

    def _init_pygame(self) -> bool:
        """
        Инициализировать pygame.mixer.

        Returns:
            True если инициализация успешна
        """
        if self._pygame_initialized:
            return True

        with self._lock:
            if self._pygame_initialized:
                return True

            try:
                import pygame
                pygame.mixer.init()
                self._pygame_initialized = True
                logger.debug("pygame.mixer инициализирован")
                return True
            except Exception as e:
                logger.error(f"Ошибка инициализации pygame.mixer: {e}", exc_info=True)
                return False

    def play(self, sound_key: str) -> None:
        """
        Воспроизвести звуковой эффект.

        Args:
            sound_key: Ключ звука (START_DOWNLOAD, END_DOWNLOAD, ERROR_DOWNLOAD)
        """
        if not self.enabled:
            logger.debug(f"Звук отключён: {sound_key}")
            return

        # Маппинг ключей к путям
        sound_paths = {
            'START_DOWNLOAD': self.SOUND_START_DOWNLOAD,
            'END_DOWNLOAD': self.SOUND_END_DOWNLOAD,
            'ERROR_DOWNLOAD': self.SOUND_ERROR_DOWNLOAD,
        }

        relative_path = sound_paths.get(sound_key)
        if not relative_path:
            logger.warning(f"Неизвестный ключ звука: {sound_key}")
            return

        # Запуск воспроизведения в отдельном потоке
        thread = threading.Thread(
            target=self._play_sound,
            args=(relative_path,),
            daemon=True,
            name=f"Sound-{sound_key}"
        )
        thread.start()

    def _play_sound(self, relative_path: str) -> None:
        """
        Воспроизвести звуковой файл (внутренний метод для потока).

        Args:
            relative_path: Относительный путь к WAV-файлу
        """
        full_path = self._get_sound_path(relative_path)
        if not full_path:
            return

        if not self._init_pygame():
            return

        try:
            import pygame

            # Загрузка и воспроизведение
            sound = pygame.mixer.Sound(full_path)
            sound.play()

            logger.debug(f"Воспроизводится звук: {os.path.basename(full_path)}")

            # Ждём завершения воспроизведения
            # Для коротких звуков это не блокирует надолго
            clock = pygame.time.Clock()
            while pygame.mixer.get_busy():
                clock.tick(10)  # Проверка каждые 100ms

        except Exception as e:
            logger.error(f"Ошибка воспроизведения звука: {e}", exc_info=True)

    def play_start_download(self) -> None:
        """Воспроизвести звук начала загрузки."""
        self.play('START_DOWNLOAD')

    def play_end_download(self) -> None:
        """Воспроизвести звук завершения загрузки."""
        self.play('END_DOWNLOAD')

    def play_error_download(self) -> None:
        """Воспроизвести звук ошибки загрузки (зарезервировано)."""
        self.play('ERROR_DOWNLOAD')

    def set_enabled(self, enabled: bool) -> None:
        """
        Включить или отключить звуковые эффекты.

        Args:
            enabled: True для включения, False для отключения
        """
        self.enabled = enabled
        logger.info(f"Звуковые эффекты {'включены' if enabled else 'отключены'}")

    def is_enabled(self) -> bool:
        """
        Проверить, включены ли звуковые эффекты.

        Returns:
            True если звуки включены
        """
        return self.enabled

    def shutdown(self) -> None:
        """Остановить воспроизведение и очистить ресурсы."""
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.quit()
                self._pygame_initialized = False
                logger.debug("pygame.mixer остановлен")
        except Exception as e:
            logger.warning(f"Ошибка при остановке звука: {e}")


# Глобальный экземпляр для удобного доступа
_sound_manager: Optional[SoundManager] = None


def get_sound_manager() -> SoundManager:
    """
    Получить глобальный экземпляр SoundManager.

    Returns:
        Экземпляр SoundManager
    """
    global _sound_manager
    if _sound_manager is None:
        _sound_manager = SoundManager()
    return _sound_manager


def play_start_sound() -> None:
    """Воспроизвести звук начала загрузки."""
    get_sound_manager().play_start_download()


def play_end_sound() -> None:
    """Воспроизвести звук завершения загрузки."""
    get_sound_manager().play_end_download()


def play_error_sound() -> None:
    """Воспроизвести звук ошибки загрузки."""
    get_sound_manager().play_error_download()
