# -*- coding: utf-8 -*-
"""Тесты оркестрации загрузки в MainWindow."""

import os
import sys
from unittest.mock import Mock, patch, MagicMock

import pytest

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestMainWindowDownloadOrchestration:
    def _make_window_stub(self):
        from ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        window.is_downloading = False
        window.config_manager = Mock()
        window.config_manager.get.return_value = ''
        window.config_manager.save = Mock()
        window.config_manager.set = Mock()
        window.url_input = Mock()
        window.log_viewer = Mock()
        window.log_viewer.warning = Mock()
        window.log_viewer.error = Mock()
        window.log_viewer.success = Mock()
        window.log_viewer.info = Mock()
        window.download_button = Mock()
        window.download_button.configure = Mock()
        window.progress_bar = Mock()
        window.progress_bar.reset = Mock()
        window.progress_bar.update_progress = Mock()
        window.clipboard_monitor = Mock()
        window.clipboard_monitor.is_running.return_value = True
        window.clipboard_monitor.pause = Mock()
        window.clipboard_monitor.resume = Mock()
        window.sound_manager = Mock()
        window.sound_manager.play_start_download = Mock()
        window.sound_manager.play_end_download = Mock()
        window.icon_download = '⭳'
        window.after = Mock()
        window.downloader = None
        return window

    @patch('ui.main_window.validate_url_for_download')
    def test_start_download_rejects_invalid_url(self, mock_validate):
        mock_validate.return_value = (False, 'Введите URL', '')
        window = self._make_window_stub()
        window.url_input.get_url.return_value = ''

        window._start_download()

        window.log_viewer.error.assert_called_once()
        assert window.is_downloading is False

    @patch('ui.main_window.validate_url_for_download')
    def test_start_download_skips_duplicate_url(self, mock_validate):
        mock_validate.return_value = (True, 'https://youtube.com/watch?v=abc', '')
        window = self._make_window_stub()
        window.url_input.get_url.return_value = 'https://youtube.com/watch?v=abc'
        window.config_manager.get.return_value = 'https://youtube.com/watch?v=abc'

        window._start_download()

        window.log_viewer.warning.assert_called()
        assert window.is_downloading is False

    @patch('ui.main_window.threading.Thread')
    @patch('ui.main_window.validate_url_for_download')
    @patch('ui.main_window.ctk.CTkFont')
    def test_start_download_starts_thread(self, mock_font, mock_validate, mock_thread):
        mock_validate.return_value = (True, 'https://youtube.com/watch?v=abc', '')
        window = self._make_window_stub()
        window.url_input.get_url.return_value = 'https://youtube.com/watch?v=abc'
        window.config_manager.get.return_value = ''

        window._start_download()

        assert window.is_downloading is True
        window.clipboard_monitor.pause.assert_called_once()
        mock_thread.assert_called_once()

    @patch('ui.main_window.send_download_complete')
    @patch('ui.main_window.check_ytdlp_ready')
    def test_update_and_download_success(self, mock_ready, mock_notify):
        mock_ready.return_value = (True, '')
        window = self._make_window_stub()
        window.is_downloading = True
        window._update_utilities = Mock()
        window._download_thread = Mock(return_value=True)

        window._update_and_download('https://youtube.com/watch?v=abc')

        window._download_thread.assert_called_once()
        window.after.assert_called()
        window.config_manager.set.assert_called_with('LAST_DOWNLOADED_URL', 'https://youtube.com/watch?v=abc')

    @patch('ui.main_window.check_ytdlp_ready')
    def test_update_and_download_resets_ui_on_exception(self, mock_ready):
        mock_ready.side_effect = RuntimeError('boom')
        window = self._make_window_stub()
        window.is_downloading = True
        window._update_utilities = Mock()
        window._on_download_complete = Mock()

        window._update_and_download('https://youtube.com/watch?v=abc')

        window.after.assert_any_call(0, window._on_download_complete)
        error_scheduled = any(
            len(call[0]) >= 2 and callable(call[0][1])
            for call in window.after.call_args_list
        )
        assert error_scheduled

    @patch('core.updater.update_utilities')
    @patch('ui.main_window.get_ytdlp_download_url')
    @patch('ui.main_window.check_ytdlp_ready')
    def test_retry_ytdlp_download(self, mock_ready, mock_get_url, mock_update):
        mock_get_url.return_value = 'https://example.com/yt-dlp.exe'
        window = self._make_window_stub()
        window.config_manager.get.return_value = '/utilities'
        mock_update.return_value = True
        mock_ready.return_value = (True, '')

        ready, message = window._retry_ytdlp_download('yt-dlp не найден')

        assert ready is True
        mock_update.assert_called_once()
