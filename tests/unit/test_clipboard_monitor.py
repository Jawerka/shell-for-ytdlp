# -*- coding: utf-8 -*-
"""Тесты для модуля clipboard_monitor.py."""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.clipboard_monitor import ClipboardMonitor


@pytest.fixture
def mock_root():
    root = MagicMock()
    root.after = Mock(return_value='after-1')
    root.after_cancel = Mock()
    return root


@pytest.fixture
def monitor_with_callback(mock_root):
    callback = Mock()
    monitor = ClipboardMonitor(
        on_url_detected=callback,
        root_window=mock_root,
        check_interval=0.1,
    )
    return monitor, callback, mock_root


class TestClipboardMonitorInit:
    def test_init_default_values(self):
        monitor = ClipboardMonitor()
        assert monitor.check_interval == 2.0
        assert monitor.on_url_detected is None
        assert monitor._is_running is False
        assert monitor._is_paused is False
        assert monitor._last_clipboard_content is None


class TestStartStop:
    def test_start_schedules_poll(self, monitor_with_callback):
        monitor, _, root = monitor_with_callback
        monitor.start()
        assert monitor._is_running is True
        root.after.assert_called()
        monitor.stop()

    def test_start_requires_root_window(self):
        monitor = ClipboardMonitor()
        monitor.start()
        assert monitor._is_running is False

    def test_stop_cancels_poll(self, monitor_with_callback):
        monitor, _, root = monitor_with_callback
        monitor.start()
        monitor._poll_after_id = 'poll-id'
        monitor.stop()
        root.after_cancel.assert_called_once_with('poll-id')
        assert monitor._is_running is False


class TestPauseResume:
    def test_resume_triggers_immediate_check(self, monitor_with_callback):
        monitor, callback, _ = monitor_with_callback
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        monitor._is_running = True
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor.resume()
            callback.assert_called_once_with(test_url)


class TestUrlDetection:
    def test_supported_youtube_url(self, monitor_with_callback):
        monitor, callback, _ = monitor_with_callback
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor._check_clipboard()
            callback.assert_called_once_with(test_url)

    def test_url_in_quotes(self, monitor_with_callback):
        monitor, callback, _ = monitor_with_callback
        test_url = '"https://www.youtube.com/watch?v=dQw4w9WgXcQ"'
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor._check_clipboard()
            callback.assert_called_once()

    def test_url_with_trailing_period(self, monitor_with_callback):
        monitor, callback, _ = monitor_with_callback
        raw = "https://www.youtube.com/watch?v=dQw4w9WgXcQ."
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=raw):
            monitor._check_clipboard()
            callback.assert_called_once()
            assert callback.call_args[0][0].endswith('dQw4w9WgXcQ')

    def test_url_without_protocol(self, monitor_with_callback):
        monitor, callback, _ = monitor_with_callback
        test_url = "youtube.com/watch?v=dQw4w9WgXcQ"
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor._check_clipboard()
            callback.assert_called_once()
            assert callback.call_args[0][0].startswith('https://')

    def test_unsupported_url_not_detected(self, monitor_with_callback):
        monitor, callback, _ = monitor_with_callback
        with patch('core.clipboard_monitor.pyperclip.paste', return_value="https://example.com/page"):
            monitor._check_clipboard()
            callback.assert_not_called()

    def test_duplicate_content_not_processed(self, monitor_with_callback):
        monitor, callback, _ = monitor_with_callback
        test_url = "https://www.youtube.com/watch?v=test"
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor._check_clipboard()
        callback.assert_called_once()
        callback.reset_mock()
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor._check_clipboard()
        callback.assert_not_called()

    def test_multiline_with_url_on_second_line(self, monitor_with_callback):
        monitor, callback, _ = monitor_with_callback
        text = "Check this\nhttps://www.youtube.com/watch?v=abc1234567"
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=text):
            monitor._check_clipboard()
            callback.assert_called_once()


class TestErrorHandling:
    def test_clipboard_read_retry(self, monitor_with_callback):
        monitor, callback, _ = monitor_with_callback
        test_url = "https://www.youtube.com/watch?v=retrytest"
        with patch('core.clipboard_monitor.pyperclip.paste', side_effect=[Exception("busy"), test_url]):
            with patch('core.clipboard_monitor.time.sleep'):
                monitor._check_clipboard()
        callback.assert_called_once_with(test_url)

    def test_callback_error_handled(self, monitor_with_callback):
        monitor, callback, _ = monitor_with_callback
        callback.side_effect = Exception("Callback error")
        test_url = "https://www.youtube.com/watch?v=test"
        with patch('core.clipboard_monitor.pyperclip.paste', return_value=test_url):
            monitor._check_clipboard()

    def test_url_validation_error(self, monitor_with_callback):
        monitor, callback, _ = monitor_with_callback
        with patch('core.clipboard_monitor.extract_video_url', side_effect=Exception("Validation error")):
            with patch('core.clipboard_monitor.pyperclip.paste', return_value="https://test.com"):
                monitor._check_clipboard()
        callback.assert_not_called()
