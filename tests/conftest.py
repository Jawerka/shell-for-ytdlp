# -*- coding: utf-8 -*-
"""
Конфигурация pytest для тестов UI-for-ytdlp.

Использование:
    pytest tests/ -v                    # Запустить все тесты
    pytest tests/ -v --cov=core         # С покрытием core
    pytest tests/ -v --cov=ui           # С покрытием ui
    pytest tests/unit/test_downloader.py -v  # Конкретный файл
    pytest tests/ -k "test_download"    # По имени теста
"""

import os
import sys

# Добавляем корень проекта в sys.path для импортов
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Глобальные фикстуры можно добавлять здесь
# Например:
# @pytest.fixture
# def temp_config(tmp_path):
#     """Создаёт временную конфигурацию для тестов."""
#     config_path = tmp_path / "config.json"
#     config_path.write_text('{}')
#     return str(config_path)
