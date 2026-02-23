# -*- coding: utf-8 -*-
"""
UI компоненты приложения.

Модули:
- url_input: Поле ввода URL
- log_viewer: Просмотр логов
- progress_bar: Прогресс-бар
- sponsorblock_dialog: Диалог SponsorBlock
"""

from .url_input import UrlInput
from .log_viewer import LogViewer
from .progress_bar import ProgressBarWithText
from .sponsorblock_dialog import SponsorBlockDialog, SPONSORBLOCK_CATEGORIES

__all__ = [
    'UrlInput',
    'LogViewer',
    'ProgressBarWithText',
    'SponsorBlockDialog',
    'SPONSORBLOCK_CATEGORIES',
]
