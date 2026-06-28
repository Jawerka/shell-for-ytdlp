# -*- coding: utf-8 -*-
"""
Конфигурация pytest для тестов UI-for-ytdlp.
"""

import os
import sys

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: tests requiring utilities/yt-dlp.exe on disk",
    )
