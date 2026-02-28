# -*- coding: utf-8 -*-
"""
UI компоненты приложения.

Модули:
- url_input: Поле ввода URL
- log_viewer: Просмотр логов
- progress_bar: Прогресс-бар
- sponsorblock_dialog: Диалог SponsorBlock
- cookies_dialog: Диалог настройки cookies.txt
"""

from .url_input import UrlInput
from .log_viewer import LogViewer
from .progress_bar import ProgressBarWithText
from .sponsorblock_dialog import SponsorBlockDialog, SPONSORBLOCK_CATEGORIES
from .cookies_dialog import CookiesDialog

__all__ = [
    'UrlInput',
    'LogViewer',
    'ProgressBarWithText',
    'SponsorBlockDialog',
    'CookiesDialog',
    'SPONSORBLOCK_CATEGORIES',
]
