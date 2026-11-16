# -*- coding: utf-8 -*-
"""
Тесты кодировок для downloader и utils.
"""

import os
import sys
import subprocess
import json
import pytest

# Добавляем корень проекта
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

_YTDLP_PATH = os.path.join(project_root, 'utilities', 'yt-dlp.exe')
_HAS_YTDLP = os.path.isfile(_YTDLP_PATH)


@pytest.mark.integration
@pytest.mark.skipif(not _HAS_YTDLP, reason="utilities/yt-dlp.exe not installed")
class TestEncoding:
    """Тесты кодировки вывода yt-dlp."""

    def test_ytdlp_exists(self):
        """Проверка наличия yt-dlp."""
        ytdlp_path = os.path.join(project_root, 'utilities', 'yt-dlp.exe')
        assert os.path.exists(ytdlp_path), f"yt-dlp не найден: {ytdlp_path}"

    def test_ytdlp_version(self):
        """Проверка запуска yt-dlp с флагом --version."""
        ytdlp_path = os.path.join(project_root, 'utilities', 'yt-dlp.exe')
        
        cmd = [ytdlp_path, '--version']
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            timeout=10
        )
        
        assert result.returncode == 0, f"yt-dlp --version failed: {result.stderr}"
        assert len(result.stdout.strip()) > 0, "yt-dlp вернул пустую версию"

    @pytest.fixture
    def info_file(self, tmp_path):
        """Unicode fixture avoids testing encoding through an unreliable network."""
        path = tmp_path / 'video.info.json'
        path.write_text(json.dumps({
            'id': 'unicode', 'title': 'Проверка кириллицы — видео',
            'extractor': 'generic', 'url': 'https://example.invalid/video.mp4',
            'ext': 'mp4', 'vcodec': 'avc1.640028', 'acodec': 'mp4a.40.2',
        }, ensure_ascii=False), encoding='utf-8')
        return path

    def test_ytdlp_encoding_utf8(self, info_file):
        """Тест кодировки UTF-8 с errors='replace'."""
        ytdlp_path = os.path.join(project_root, 'utilities', 'yt-dlp.exe')
        
        cmd = [
            ytdlp_path,
            '--ignore-config', '--no-check-formats',
            '--encoding', 'utf-8',
            '--dump-json',
            '--no-download',
            '--load-info-json', str(info_file),
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            timeout=30
        )
        
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data['title'] == 'Проверка кириллицы — видео'

    def test_ytdlp_encoding_cyrillic(self, info_file):
        """Тест обработки кириллицы в названии видео."""
        ytdlp_path = os.path.join(project_root, 'utilities', 'yt-dlp.exe')
        
        cmd = [
            ytdlp_path,
            '--ignore-config', '--no-check-formats',
            '--encoding', 'utf-8',
            '--simulate',
            '--print', 'title',
            '--load-info-json', str(info_file),
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            timeout=30
        )
        
        assert result.returncode == 0, result.stderr
        title = result.stdout.strip()
        assert title == 'Проверка кириллицы — видео'
        assert '\ufffd' not in title


class TestLoggerEncoding:
    """Тесты кодировки логгера."""

    def test_logger_utf8_strings(self):
        """Тест UTF-8 строк в логгере."""
        from core.logger import GUILogger
        
        logger = GUILogger()
        
        test_texts = [
            "Привет мир! Это тестовое сообщение.",
            "Загрузка файла: тест_видео.mp4",
            "Путь: D:\\Documents\\Projects\\python\\UI-for-ytdlp",
            "Ошибка: Файл не найден",
        ]
        
        for text in test_texts:
            logger.info(text)
        
        logs = logger.get_logs()
        assert len(logs) == len(test_texts), f"Количество логов не совпадает: {len(logs)} != {len(test_texts)}"
        
        # Проверяем что все логи содержат UTF-8 текст
        for (formatted, level), expected in zip(logs, test_texts):
            assert expected in formatted, f"Лог не содержит ожидаемый текст: {expected}"

    def test_logger_long_cyrillic_text(self):
        """Тест длинного кириллического текста."""
        from core.logger import GUILogger
        
        logger = GUILogger()
        
        # Длинный текст на русском
        long_text = "А" * 1000 + "Привет" + "Б" * 1000
        
        logger.info(long_text)
        logs = logger.get_logs()
        
        assert len(logs) == 1, "Должно быть одно сообщение"
        assert long_text in logs[0][0], "Лог не содержит длинный текст"
