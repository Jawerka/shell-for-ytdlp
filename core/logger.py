# -*- coding: utf-8 -*-
"""
Модуль логгера приложения.

Содержит:
- LogLevel: уровни логирования
- GUILogger: логгер для GUI
"""

from datetime import datetime
from enum import Enum
from typing import Callable, Optional, List, Tuple


class LogLevel(Enum):
    """Уровни логирования."""
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'
    DEBUG = 'debug'


class GUILogger:
    """
    Логгер для GUI приложения.
    
    Сохраняет историю логов и предоставляет callback для отображения.
    """
    
    COLORS = {
        LogLevel.INFO: '#9AA0A6',
        LogLevel.SUCCESS: '#4CAF50',
        LogLevel.WARNING: '#FFC107',
        LogLevel.ERROR: '#F44336',
        LogLevel.DEBUG: '#607D8B',
    }
    
    def __init__(self, callback: Optional[Callable[[str, LogLevel], None]] = None):
        """
        Инициализация логгера.
        
        Args:
            callback: Функция обратного вызова для отображения логов
        """
        self.callback = callback
        self._logs: List[Tuple[str, LogLevel]] = []
    
    def _log(self, message: str, level: LogLevel) -> None:
        """
        Внутренний метод логирования.
        
        Args:
            message: Сообщение
            level: Уровень логирования
        """
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted = f"[{timestamp}] {message}"
        self._logs.append((formatted, level))
        if self.callback:
            self.callback(formatted, level)
    
    def info(self, message: str) -> None:
        """Логирование информационного сообщения."""
        self._log(message, LogLevel.INFO)
    
    def success(self, message: str) -> None:
        """Логирование успешного действия."""
        self._log(message, LogLevel.SUCCESS)
    
    def warning(self, message: str) -> None:
        """Логирование предупреждения."""
        self._log(message, LogLevel.WARNING)
    
    def error(self, message: str) -> None:
        """Логирование ошибки."""
        self._log(message, LogLevel.ERROR)
    
    def debug(self, message: str) -> None:
        """Логирование отладочной информации."""
        self._log(message, LogLevel.DEBUG)
    
    def get_logs(self) -> List[Tuple[str, LogLevel]]:
        """
        Получить копию истории логов.
        
        Returns:
            Список кортежей (сообщение, уровень)
        """
        return self._logs.copy()
    
    def clear(self) -> None:
        """Очистить историю логов."""
        self._logs.clear()
