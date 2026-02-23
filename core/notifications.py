# -*- coding: utf-8 -*-
"""
Модуль системных уведомлений.

Содержит:
- NotificationManager: менеджер системных уведомлений
"""

import logging
from typing import Optional

from core.config import ConfigManager

# Логгер для отладки
logger = logging.getLogger('UI-for-ytdlp.notifications')


class NotificationManager:
    """Менеджер системных уведомлений."""

    def __init__(self):
        """Инициализация менеджера уведомлений."""
        logger.debug("NotificationManager: Инициализация")
        self.config_manager = ConfigManager()
        self._notification = None

    def _get_notification(self):
        """
        Получить экземпляр уведомления.

        Returns:
            Экземпляр уведомления или None
        """
        if self._notification is None:
            try:
                from plyer import notification
                self._notification = notification
                logger.debug("NotificationManager: plyer успешно импортирован")
            except ImportError:
                logger.warning("NotificationManager: plyer не установлен, уведомления отключены")
                return None
        return self._notification

    def send(
        self,
        title: str,
        message: str,
        app_name: str = "UI-for-ytdlp"
    ) -> bool:
        """
        Отправить системное уведомление.

        Args:
            title: Заголовок уведомления
            message: Текст уведомления
            app_name: Имя приложения

        Returns:
            True если уведомление отправлено
        """
        # Проверка включения уведомлений в конфигурации
        if not self.config_manager.get('ENABLE_NOTIFICATIONS', True):
            logger.debug("NotificationManager: Уведомления отключены в конфигурации")
            return False

        notification = self._get_notification()
        if notification is None:
            return False

        try:
            notification.notify(
                title=title,
                message=message,
                app_name=app_name,
                timeout=10  # Секунды отображения
            )
            logger.debug(f"NotificationManager: Отправлено уведомление: {title}")
            return True
        except Exception as e:
            logger.error(f"NotificationManager: Ошибка отправки уведомления: {e}")
            return False

    def send_download_complete(
        self,
        title: str = "Загрузка завершена",
        message: str = "Видео успешно загружено"
    ) -> bool:
        """
        Отправить уведомление о завершении загрузки.

        Args:
            title: Заголовок
            message: Текст

        Returns:
            True если уведомление отправлено
        """
        return self.send(title, message)

    def send_download_error(
        self,
        title: str = "Ошибка загрузки",
        message: str = "Произошла ошибка при загрузке видео"
    ) -> bool:
        """
        Отправить уведомление об ошибке загрузки.

        Args:
            title: Заголовок
            message: Текст

        Returns:
            True если уведомление отправлено
        """
        return self.send(title, message)

    def send_update_complete(
        self,
        title: str = "Утилиты обновлены",
        message: str = "yt-dlp и ffmpeg обновлены до последних версий"
    ) -> bool:
        """
        Отправить уведомление о завершении обновления утилит.

        Args:
            title: Заголовок
            message: Текст

        Returns:
            True если уведомление отправлено
        """
        return self.send(title, message)


# Глобальный экземпляр
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """
    Получить глобальный экземпляр менеджера уведомлений.

    Returns:
        NotificationManager
    """
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def send_notification(title: str, message: str) -> bool:
    """
    Отправить системное уведомление.

    Args:
        title: Заголовок
        message: Текст

    Returns:
        True если уведомление отправлено
    """
    return get_notification_manager().send(title, message)


def send_download_complete(title: str, message: str) -> bool:
    """Отправить уведомление о завершении загрузки."""
    return get_notification_manager().send_download_complete(title, message)


def send_download_error(title: str, message: str) -> bool:
    """Отправить уведомление об ошибке загрузки."""
    return get_notification_manager().send_download_error(title, message)
