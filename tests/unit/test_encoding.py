# -*- coding: utf-8 -*-
"""
Тесты кодировок для downloader и utils.
"""

import os
import sys
import subprocess
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

    def test_ytdlp_encoding_utf8(self):
        """Тест кодировки UTF-8 с errors='replace'."""
        ytdlp_path = os.path.join(project_root, 'utilities', 'yt-dlp.exe')
        
        # Используем стабильное видео для теста
        cmd = [
            ytdlp_path,
            '--dump-json',
            '--no-download',
            '--socket-timeout', '5',
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
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
        
        # Проверяем что вывод не пустой (видео может быть недоступно, но JSON должен быть)
        if result.returncode != 0:
            # Если ошибка сети - пропускаем тест
            if 'ERROR' in result.stderr and 'unavailable' in result.stderr:
                pytest.skip(f"Видео недоступно: {result.stderr[:100]}")
        
        # Проверяем что это валидный JSON если успех
        if result.returncode == 0 and len(result.stdout) > 0:
            import json
            try:
                data = json.loads(result.stdout)
                assert 'title' in data, "JSON не содержит поле 'title'"
            except json.JSONDecodeError as e:
                pytest.fail(f"yt-dlp вернул невалидный JSON: {e}\nSTDOUT: {result.stdout[:500]}")

    def test_ytdlp_encoding_cyrillic(self):
        """Тест обработки кириллицы в названии видео."""
        ytdlp_path = os.path.join(project_root, 'utilities', 'yt-dlp.exe')
        
        # Видео с русской локализацией
        cmd = [
            ytdlp_path,
            '--simulate',
            '--print', 'title',
            '--hlslang', 'ru',
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
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
        
        # Если видео недоступно - пропускаем
        if 'unavailable' in result.stderr.lower():
            pytest.skip(f"Видео недоступно")
        
        # Проверяем что вывод содержит текст
        if len(result.stdout.strip()) > 0:
            title = result.stdout.strip()
            # Проверяем что title не содержит ошибок кодировки ( replacement character)
            assert '' not in title, f"Название содержит символы замены: {title}"


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
