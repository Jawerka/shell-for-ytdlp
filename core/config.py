# -*- coding: utf-8 -*-
"""
Модуль конфигурации приложения.

Содержит:
- DEFAULT_CONFIG: настройки по умолчанию
- ConfigManager: менеджер конфигурации
"""

import os
import json
import shutil
import logging
from typing import Any

# Логгер для отладки
logger = logging.getLogger('UI-for-ytdlp.config')


# ============================================================================
# ПУТИ И РЕСУРСЫ
# ============================================================================
def get_app_base_path() -> str:
    """Получить базовый путь приложения (корень проекта)."""
    import sys
    if hasattr(sys, '_MEIPASS'):
        path = os.path.dirname(sys.executable)
        logger.debug(f"get_app_base_path: PyInstaller mode -> {path}")
        return path
    # Возвращаем директорию выше core/ (т.е. корень проекта)
    core_dir = os.path.abspath(os.path.dirname(__file__))
    path = os.path.dirname(core_dir)
    logger.debug(f"get_app_base_path: Development mode -> {path}")
    return path


def get_resource_path(relative_path: str) -> str:
    """Получить полный путь к ресурсу."""
    import sys
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(get_app_base_path(), relative_path)


def get_utilities_path() -> str:
    """Получить путь к директории утилит."""
    base = get_app_base_path()
    utilities = os.path.join(base, 'utilities')
    os.makedirs(utilities, exist_ok=True)
    return utilities


def get_config_path() -> str:
    """Получить путь к файлу конфигурации."""
    return os.path.join(get_utilities_path(), 'config.json')


def get_config_backup_path() -> str:
    """Получить путь к резервной копии конфигурации."""
    return os.path.join(get_utilities_path(), 'config.bkp')


# ============================================================================
# КОНФИГУРАЦИЯ ПО УМОЛЧАНИЮ
# ============================================================================
DEFAULT_CONFIG = {
    'URL_UTILITIES_UPDATE': [
        'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe',
        'https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip'
    ],
    'DAFAULT_PATH': '',
    'UTILITIES_PATH': '',
    'DOWNLOAD_PATH': os.path.join(os.getenv('USERPROFILE', ''), 'Downloads'),
    'SPONSORBLOCK_REMOVE_LIST': ['sponsor', 'selfpromo'],
    'YTDLP_PATH': '',
    'QUESTION_BYPASS': False,
    # Настройки уведомлений
    'ENABLE_NOTIFICATIONS': True,
    # Настройки cookies
    'COOKIES_PATH': '',
    # Настройки мониторинга буфера обмена
    'CLIPBOARD_MONITORING': False,
    # Настройки звуковых уведомлений
    'ENABLE_SOUND_NOTIFICATIONS': True,
    # Настройки положения окна
    'WINDOW_POS_X': None,
    'WINDOW_POS_Y': None,
    'WINDOW_WIDTH': 740,
    'WINDOW_HEIGHT': 520,
    # Последний загруженный URL (для предотвращения повторной загрузки)
    'LAST_DOWNLOADED_URL': '',
}


# ============================================================================
# МЕНЕДЖЕР КОНФИГУРАЦИИ
# ============================================================================
class ConfigManager:
    """Менеджер конфигурации приложения."""

    def __init__(self):
        """Инициализация менеджера конфигурации."""
        logger.debug("ConfigManager: Инициализация")
        
        self.config_path = get_config_path()
        self.bkp_path = get_config_backup_path()
        
        logger.debug(f"ConfigManager: config_path = {self.config_path}")
        logger.debug(f"ConfigManager: bkp_path = {self.bkp_path}")
        
        base_path = get_app_base_path()

        # Установка путей по умолчанию
        DEFAULT_CONFIG['DAFAULT_PATH'] = base_path
        DEFAULT_CONFIG['UTILITIES_PATH'] = os.path.join(base_path, 'utilities')
        DEFAULT_CONFIG['YTDLP_PATH'] = os.path.join(DEFAULT_CONFIG['UTILITIES_PATH'], 'yt-dlp.exe')

        if not os.path.exists(DEFAULT_CONFIG['DOWNLOAD_PATH']):
            DEFAULT_CONFIG['DOWNLOAD_PATH'] = base_path

        self.config = self._load_or_create()
        logger.debug(f"ConfigManager: DOWNLOAD_PATH = {self.config.get('DOWNLOAD_PATH')}")
        logger.debug(f"ConfigManager: YTDLP_PATH = {self.config.get('YTDLP_PATH')}")
    
    def _load_or_create(self) -> dict:
        """Загрузить конфигурацию или создать новую."""
        logger.debug("_load_or_create: Попытка загрузки конфигурации")
        
        # Попытка загрузки основного файла
        if os.path.exists(self.config_path) and os.path.getsize(self.config_path) > 100:
            logger.debug(f"_load_or_create: Файл {self.config_path} найден")
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.debug(f"_load_or_create: Загружено {len(config)} ключей")
                self._backup_config(self.config_path)
                return self._merge_with_defaults(config)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"_load_or_create: Ошибка чтения config.json: {e}")
                pass

        # Попытка загрузки резервной копии
        if os.path.exists(self.bkp_path) and os.path.getsize(self.bkp_path) > 100:
            logger.debug(f"_load_or_create: Файл {self.bkp_path} найден, восстановление")
            try:
                shutil.copyfile(self.bkp_path, self.config_path)
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return self._merge_with_defaults(config)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"_load_or_create: Ошибка восстановления из backup: {e}")
                pass

        # Создание новой конфигурации
        logger.debug("_load_or_create: Создание новой конфигурации по умолчанию")
        return DEFAULT_CONFIG.copy()
    
    def _merge_with_defaults(self, config: dict) -> dict:
        """Объединить пользовательскую конфигурацию с настройками по умолчанию."""
        result = DEFAULT_CONFIG.copy()
        result.update(config)

        # Обновление путей
        base_path = get_app_base_path()
        result['DAFAULT_PATH'] = base_path
        result['UTILITIES_PATH'] = os.path.join(base_path, 'utilities')
        result['YTDLP_PATH'] = os.path.join(result['UTILITIES_PATH'], 'yt-dlp.exe')

        # Добавление новых полей если их нет
        if 'QUESTION_BYPASS' not in result:
            result['QUESTION_BYPASS'] = False
        if 'ENABLE_NOTIFICATIONS' not in result:
            result['ENABLE_NOTIFICATIONS'] = True
        if 'ENABLE_SOUND_NOTIFICATIONS' not in result:
            result['ENABLE_SOUND_NOTIFICATIONS'] = True

        return result
    
    def _backup_config(self, source_path: str) -> None:
        """Создать резервную копию конфигурации."""
        try:
            shutil.copyfile(source_path, self.bkp_path)
        except IOError:
            pass
    
    def save(self) -> None:
        """Сохранить конфигурацию."""
        if os.path.exists(self.config_path):
            self._backup_config(self.config_path)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение по ключу."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Установить значение по ключу."""
        self.config[key] = value
    
    def get_all(self) -> dict:
        """Получить копию всей конфигурации."""
        return self.config.copy()
