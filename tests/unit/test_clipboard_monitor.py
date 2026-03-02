# -*- coding: utf-8 -*-
"""
Тесты для модуля clipboard_monitor.py.

Проверяют:
- Запуск/остановку мониторинга
- Обнаружение URL в буфере
- Паузу/возобновление
- Обработку ошибок
"""

import os
import sys
import pytest
import time
from unittest.mock import Mock, patch, MagicMock

# Добавляем корень проекта в path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.clipboard_monitor import ClipboardMonitor


class TestClipboardMonitorInit:
    """Тесты инициализации ClipboardMonitor."""

    def test_init_default_values(self):
        """Тест значений по умолчанию."""
        monitor = ClipboardMonitor()
        
        assert monitor.check_interval == 2.0
        assert monitor.on_url_detected is None
        assert monitor._is_running is False
        assert monitor._is_paused is False
        assert monitor._thread is None
        assert monitor._last_clipboard_content is None

    def test_init_custom_interval(self):
        """Тест пользовательского интервала."""
        monitor = ClipboardMonitor(check_interval=5.0)
        
        assert monitor.check_interval == 5.0

    def test_init_with_callback(self):
        """Тест с callback функцией."""
        callback = Mock()
        monitor = ClipboardMonitor(on_url_detected=callback)
        
        assert monitor.on_url_detected == callback


class TestStartStop:
    """Тесты запуска и остановки."""

    def test_start_sets_flags(self):
        """Тест что start устанавливает флаги."""
        monitor = ClipboardMonitor()
        monitor.start()
        
        assert monitor._is_running is True
        assert monitor._is_paused is False
        assert monitor._thread is not None
        assert monitor._thread.is_alive()
        
        # Останавливаем для очистки
        monitor.stop()

    def test_start_already_running(self):
        """Тест что повторный start ничего не делает."""
        monitor = ClipboardMonitor()
        monitor.start()
        
        # Запоминаем поток
        first_thread = monitor._thread
        
        # Повторный запуск
        monitor.start()
        
        # Поток не должен измениться
        assert monitor._thread == first_thread
        
        monitor.stop()

    def test_stop_clears_flags(self):
        """Тест что stop очищает флаги."""
        monitor = ClipboardMonitor()
        monitor.start()
        monitor.stop()
        
        assert monitor._is_running is False
        assert monitor._is_paused is False
        assert monitor._thread is None
        assert monitor._last_clipboard_content is None

    def test_stop_not_running(self):
        """Тест что stop на остановленном мониторе ничего не делает."""
        monitor = ClipboardMonitor()
        
        # Не должно выбрасывать исключений
        monitor.stop()
        
        assert monitor._is_running is False

    def test_is_running(self):
        """Тест метода is_running."""
        monitor = ClipboardMonitor()
        
        assert monitor.is_running() is False
        
        monitor.start()
        assert monitor.is_running() is True
        
        monitor.stop()
        assert monitor.is_running() is False


class TestPauseResume:
    """Тесты паузы и возобновления."""

    def test_pause_sets_flag(self):
        """Тест что pause устанавливает флаг."""
        monitor = ClipboardMonitor()
        monitor.start()
        monitor.pause()
        
        assert monitor._is_paused is True
        
        monitor.stop()

    def test_resume_clears_flag(self):
        """Тест что resume сбрасывает флаг."""
        monitor = ClipboardMonitor()
        monitor.start()
        monitor.pause()
        monitor.resume()
        
        assert monitor._is_paused is False
        
        monitor.stop()

    def test_is_paused(self):
        """Тест метода is_paused."""
        monitor = ClipboardMonitor()
        
        assert monitor.is_paused() is False
        
        monitor.pause()
        assert monitor.is_paused() is True
        
        monitor.resume()
        assert monitor.is_paused() is False


class TestUrlDetection:
    """Тесты обнаружения URL."""

    @pytest.fixture
    def monitor_with_callback(self):
        """Фикстура с callback."""
        callback = Mock()
        monitor = ClipboardMonitor(on_url_detected=callback)
        return monitor, callback

    def test_supported_youtube_url(self, monitor_with_callback):
        """Тест обнаружения YouTube URL."""
        monitor, callback = monitor_with_callback
        
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor._check_clipboard()
            
            callback.assert_called_once_with(test_url)

    def test_supported_vk_url(self, monitor_with_callback):
        """Тест обнаружения VK URL."""
        monitor, callback = monitor_with_callback
        
        test_url = "https://vk.com/video123456789"
        
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor._check_clipboard()
            
            callback.assert_called_once_with(test_url)

    def test_supported_twitter_url(self, monitor_with_callback):
        """Тест обнаружения Twitter/X URL."""
        monitor, callback = monitor_with_callback
        
        test_url = "https://x.com/user/status/123456789"
        
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor._check_clipboard()
            
            callback.assert_called_once_with(test_url)

    def test_unsupported_url_not_detected(self, monitor_with_callback):
        """Тест что неподдерживаемые URL не обнаруживаются."""
        monitor, callback = monitor_with_callback
        
        test_url = "https://example.com/page"
        
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor._check_clipboard()
            
            callback.assert_not_called()

    def test_no_protocol_not_detected(self, monitor_with_callback):
        """Тест что URL без протокола не обнаруживаются."""
        monitor, callback = monitor_with_callback
        
        test_url = "youtube.com/watch?v=test"
        
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor._check_clipboard()
            
            callback.assert_not_called()

    def test_short_text_not_detected(self):
        """Тест что короткий текст не обрабатывается."""
        monitor = ClipboardMonitor()
        
        with patch('core.clipboard_monitor.pyperclip.paste', return_value="abc"):
            # Не должно выбрасывать исключений
            monitor._check_clipboard()

    def test_multiline_text_not_detected(self, monitor_with_callback):
        """Тест что многострочный текст не обнаруживается."""
        monitor, callback = monitor_with_callback
        
        test_text = "Line 1\nLine 2\nhttps://youtube.com/watch?v=test"
        
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_text):
            monitor._check_clipboard()
            
            callback.assert_not_called()

    def test_duplicate_content_not_processed(self, monitor_with_callback):
        """Тест что дублирующееся содержимое не обрабатывается."""
        monitor, callback = monitor_with_callback
        
        test_url = "https://www.youtube.com/watch?v=test"
        
        # Первый раз
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor._check_clipboard()
            
        callback.assert_called_once()
        callback.reset_mock()
        
        # Второй раз с тем же содержимым
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor._check_clipboard()
            
        # Не должно быть вызвано
        callback.assert_not_called()

    def test_empty_content_not_processed(self, monitor_with_callback):
        """Тест что пустое содержимое не обрабатывается."""
        monitor, callback = monitor_with_callback
        
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=""):
            monitor._check_clipboard()
            
            callback.assert_not_called()

    def test_none_content_not_processed(self, monitor_with_callback):
        """Тест что None содержимое не обрабатывается."""
        monitor, callback = monitor_with_callback
        
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=None):
            monitor._check_clipboard()
            
            callback.assert_not_called()


class TestErrorHandling:
    """Тесты обработки ошибок."""

    def test_clipboard_read_error(self):
        """Тест ошибки чтения буфера."""
        monitor = ClipboardMonitor()
        
        with patch('core.clipboard_monitor.pyperclip.paste', side_effect=Exception("Clipboard error")):
            # Не должно выбрасывать исключений
            monitor._check_clipboard()

    def test_callback_error_handled(self):
        """Тест что ошибка в callback обрабатывается."""
        callback = Mock(side_effect=Exception("Callback error"))
        monitor = ClipboardMonitor(on_url_detected=callback)
        
        test_url = "https://www.youtube.com/watch?v=test"
        
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            # Не должно выбрасывать исключений
            monitor._check_clipboard()

    def test_url_validation_error(self):
        """Тест ошибки валидации URL."""
        monitor = ClipboardMonitor()
        
        # URL который вызывает ошибку в is_supported_video_url
        with patch('core.clipboard_monitor.is_supported_video_url', side_effect=Exception("Validation error")):
            with patch('core.clipboard_monitor.pyperclip.paste', return_value="https://test.com"):
                # Не должно выбрасывать исключений
                monitor._check_clipboard()


class TestMonitorLoop:
    """Тесты цикла мониторинга."""

    def test_monitor_loop_respects_pause(self):
        """Тест что цикл уважает паузу."""
        monitor = ClipboardMonitor()
        monitor._is_running = True
        monitor._is_paused = True
        
        with patch('core.clipboard_monitor.pyperclip.paste') as mock_paste:
            # Запускаем цикл один раз
            monitor._monitor_loop()
            
            # paste не должен быть вызван на паузе
            mock_paste.assert_not_called()

    def test_monitor_loop_stops_on_flag(self):
        """Тест что цикл останавливается по флагу."""
        monitor = ClipboardMonitor()
        monitor._is_running = False
        
        with patch('core.clipboard_monitor.pyperclip.paste') as mock_paste:
            monitor._monitor_loop()
            
            # paste не должен быть вызван
            mock_paste.assert_not_called()

    def test_monitor_loop_handles_exception(self):
        """Тест что цикл обрабатывает исключения."""
        monitor = ClipboardMonitor()
        monitor._is_running = True
        
        with patch('core.clipboard_monitor.pyperclip.paste', side_effect=Exception("Test error")):
            with patch('core.clipboard_monitor.logger.error') as mock_error:
                monitor._monitor_loop()
                
                # Ошибка должна быть залогирована
                assert mock_error.called
