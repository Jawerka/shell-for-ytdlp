# -*- coding: utf-8 -*-
"""
UI компоненты приложения.

Модули:
- url_input: Поле ввода URL
- log_viewer: Просмотр логов
- progress_bar: Прогресс-бар
- settings_dialog: Диалог настроек (cookies + SponsorBlock)
"""

from .url_input import UrlInput
from .log_viewer import LogViewer
from .progress_bar import ProgressBarWithText
from .settings_dialog import SettingsDialog, SPONSORBLOCK_CATEGORIES

__all__ = [
    'UrlInput',
    'LogViewer',
    'ProgressBarWithText',
    'SettingsDialog',
    'SPONSORBLOCK_CATEGORIES',
]
