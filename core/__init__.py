# -*- coding: utf-8 -*-
"""
Ядро приложения UI-for-ytdlp.

Модули:
- config: Конфигурация приложения
- logger: Система логирования
- downloader: Загрузчик YouTube
- updater: Обновление утилит
- utils: Утилиты
- theme: Тема и дизайн-система
- icons: Менеджер иконок
"""

from .config import ConfigManager, DEFAULT_CONFIG, get_config_path, get_utilities_path
from .logger import GUILogger, LogLevel
from .downloader import YouTubeDownloader
from .updater import update_loop, update_utilities, unzipping_ffmpeg
from .utils import is_valid_url, get_clipboard_url, validate_url_for_ui, find_cookies_txt
from .theme import COLOR_THEME, Spacing, setup_theme, get_color, get_radius, get_spacing
from .icons import IconManager, ICONS, icon, icon_button_text

__all__ = [
    # Config
    'ConfigManager',
    'DEFAULT_CONFIG',
    'get_config_path',
    'get_utilities_path',
    
    # Logger
    'GUILogger',
    'LogLevel',
    
    # Downloader
    'YouTubeDownloader',
    
    # Updater
    'update_loop',
    'update_utilities',
    'unzipping_ffmpeg',
    
    # Utils
    'is_valid_url',
    'get_clipboard_url',
    'validate_url_for_ui',
    'find_cookies_txt',
    
    # Theme
    'COLOR_THEME',
    'Spacing',
    'setup_theme',
    'get_color',
    'get_radius',
    'get_spacing',
    
    # Icons
    'IconManager',
    'ICONS',
    'icon',
    'icon_button_text',
]
